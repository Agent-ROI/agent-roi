"""Collector for GitHub Copilot Chat in VS Code.

Copilot stores chat sessions under each VS Code workspace's
``workspaceStorage/<id>/chatSessions/*.json(l)``. Crucially, these logs record
the conversation text and the model id, but **not** real token usage (Copilot is
subscription-billed, so GitHub doesn't write token counts). We therefore
*estimate* token counts from the message text with a tokenizer and flag the
interactions as ``estimated`` so reports never present them as exact.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent_roi.collectors.base import Collector
from agent_roi.core.models import Interaction, Tool
from agent_roi.core.platform import vscode_user_dirs
from agent_roi.core.project import project_for
from agent_roi.core.tokens import estimate_tokens

# Copilot's log records the user's typed message but NOT the rest of what is
# actually sent to the model. To estimate input tokens realistically we add:
#   1. attached file context (the editor "working set" sent with the request),
#   2. the running conversation history (earlier turns are re-sent each request),
#   3. a fixed overhead for the agent system prompt + tool definitions.
# Without these the estimate counts only the user's sentence and badly
# undercounts real usage. All estimates stay flagged estimated=True.
_SYSTEM_PROMPT_OVERHEAD_TOKENS = 2400


class CopilotCollector(Collector):
    tool = Tool.COPILOT
    name = "copilot"

    def __init__(self, roots: list[Path] | None = None) -> None:
        # Each root is a VS Code "User" dir; chat sessions live under its
        # workspaceStorage subtree.
        self.roots = roots if roots is not None else vscode_user_dirs()

    def is_available(self) -> bool:
        return any((r / "workspaceStorage").is_dir() for r in self.roots)

    def search_paths(self) -> list[Path]:
        return list(self.roots)

    def count_files(self) -> int:
        total = 0
        for root in self.roots:
            ws = root / "workspaceStorage"
            if ws.is_dir():
                total += sum(1 for _ in ws.glob("*/chatSessions/*.json*"))
        return total

    def collect(self) -> Iterator[Interaction]:
        for root in self.roots:
            ws = root / "workspaceStorage"
            if not ws.is_dir():
                continue
            for ws_dir in ws.iterdir():
                if not ws_dir.is_dir():
                    continue
                cwd = _workspace_cwd(ws_dir)
                chat_dir = ws_dir / "chatSessions"
                if not chat_dir.is_dir():
                    continue
                for session_file in chat_dir.glob("*.json*"):
                    yield from self._parse_file(session_file, cwd)

    def _parse_file(self, path: Path, cwd: str) -> Iterator[Interaction]:
        session_id = path.stem
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            return
        # Collect all requests first so we can process them in conversation order
        # and accumulate history — earlier turns are re-sent on each request, so
        # input cost grows down the session.
        requests: list[dict[str, Any]] = []
        for obj in _load_objects(raw):
            _collect_requests(obj, requests)
        requests.sort(key=lambda r: _ts_value(r.get("timestamp")))

        history_text = ""  # running transcript of prior turns in this session
        for req in requests:
            itx = self._to_interaction(req, session_id, cwd, history_text)
            if itx is None:
                continue
            yield itx
            user_text = _message_text(req.get("message"))
            response_text = _response_text(req.get("response"))
            history_text += user_text + "\n" + response_text + "\n"

    def _to_interaction(
        self, req: dict[str, Any], session_id: str, cwd: str, history_text: str
    ) -> Interaction | None:
        request_id = req.get("requestId")
        if not request_id:
            return None

        user_text = _message_text(req.get("message"))
        response_text = _response_text(req.get("response"))
        context_text = _attached_context_text(req)

        model = str(req.get("modelId") or "unknown")
        summary = " ".join(p for p in (user_text, response_text) if p)[:600]

        # Real input = system prompt + tools + attached files + history + this turn.
        input_tokens = (
            _SYSTEM_PROMPT_OVERHEAD_TOKENS
            + estimate_tokens(context_text)
            + estimate_tokens(history_text)
            + estimate_tokens(user_text)
        )
        return Interaction(
            id=f"copilot:{request_id}",
            tool=self.tool,
            session_id=session_id,
            timestamp=_parse_ts(req.get("timestamp")),
            model=_normalize_model(model),
            input_tokens=input_tokens,
            output_tokens=estimate_tokens(response_text),
            cwd=cwd,
            project=project_for(cwd),
            summary=summary,
            estimated=True,
        )


def _workspace_cwd(ws_dir: Path) -> str:
    """Read the workspace folder from VS Code's ``workspace.json``.

    VS Code writes ``workspaceStorage/<hash>/workspace.json`` with a ``folder``
    key that is a URI such as:
    - ``file:///Users/yen/repo``  → local path (most common)
    - ``vscode-remote://ssh-remote%2B<host>/home/yen/repo``  → SSH remote

    We convert both to the plain path portion so ``project_for`` can derive a
    project name. For remote workspaces we keep a ``ssh:<host>:`` prefix so the
    project name stays meaningful (e.g. ``repo`` on host ``100.120.0.60``).
    """
    from urllib.parse import unquote

    wj = ws_dir / "workspace.json"
    try:
        data = json.loads(wj.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    folder = str(data.get("folder", ""))

    if folder.startswith("file:///"):
        # file:///Users/yen/repo -> /Users/yen/repo
        return unquote(folder[len("file://"):])

    if folder.startswith("vscode-remote://"):
        # vscode-remote://ssh-remote%2B<host>/path/to/repo
        rest = folder[len("vscode-remote://"):]
        slash = rest.find("/")
        if slash != -1:
            path = unquote(rest[slash:])
            return path  # project_for will pick up the last meaningful segment
        return unquote(rest)

    return folder


def _collect_requests(obj: Any, out: list[dict[str, Any]]) -> None:
    """Walk an arbitrary JSON structure, collecting every Copilot chat request."""
    if isinstance(obj, dict):
        if obj.get("requestId") and "modelId" in obj:
            out.append(obj)
        for value in obj.values():
            _collect_requests(value, out)
    elif isinstance(obj, list):
        for value in obj:
            _collect_requests(value, out)


def _ts_value(raw: Any) -> float:
    """Sortable numeric timestamp; preserves log order when timestamps are absent."""
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        try:
            return _parse_ts(raw).timestamp()
        except (ValueError, OverflowError):
            return 0.0
    return 0.0


def _attached_context_text(req: dict[str, Any]) -> str:
    """Text of files attached to the request (the editor working set + variables).

    Copilot sends the content of attached/open files to the model as context but
    does not log token counts, so we recover the raw text and estimate from it.
    """
    parts: list[str] = []

    result = req.get("result")
    if isinstance(result, dict):
        edits = result.get("metadata", {})
        edits = edits.get("edits", {}) if isinstance(edits, dict) else {}
        working_set = edits.get("workingSet", []) if isinstance(edits, dict) else []
        if isinstance(working_set, list):
            for entry in working_set:
                if isinstance(entry, dict) and isinstance(entry.get("text"), str):
                    parts.append(entry["text"])

    # variableData can also embed file snippets/selections under nested "value".
    _collect_variable_text(req.get("variableData"), parts)
    return "\n".join(parts)


def _collect_variable_text(obj: Any, out: list[str]) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in ("text", "value") and isinstance(value, str) and len(value) > 40:
                out.append(value)
            else:
                _collect_variable_text(value, out)
    elif isinstance(obj, list):
        for value in obj:
            _collect_variable_text(value, out)


def _load_objects(raw: str) -> list[Any]:
    """Parse a session file that may be a single JSON object or JSONL."""
    try:
        return [json.loads(raw)]
    except json.JSONDecodeError:
        objects: list[Any] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                objects.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return objects


def _message_text(message: Any) -> str:
    if isinstance(message, dict):
        return str(message.get("text", ""))
    if isinstance(message, str):
        return message
    return ""


def _response_text(response: Any) -> str:
    """Copilot responses are usually a list of parts with a ``value``/``text``."""
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        return str(response.get("value") or response.get("text") or "")
    if isinstance(response, list):
        parts = []
        for part in response:
            if isinstance(part, dict):
                parts.append(str(part.get("value") or part.get("text") or ""))
            elif isinstance(part, str):
                parts.append(part)
        return "".join(parts)
    return ""


def _normalize_model(model: str) -> str:
    # Copilot reports e.g. "copilot/claude-opus-4.6"; strip the vendor prefix and
    # map dots to dashes so it matches the pricing table where possible.
    name = model.split("/", 1)[-1]
    return name.replace(".", "-")


def _parse_ts(raw: Any) -> datetime:
    # Copilot timestamps are epoch milliseconds.
    if isinstance(raw, (int, float)):
        try:
            return datetime.fromtimestamp(raw / 1000, tz=timezone.utc)
        except (ValueError, OSError):
            pass
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(tz=timezone.utc)
