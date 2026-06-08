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
import re
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from agent_roi.collectors.base import Collector
from agent_roi.core.models import Activity, Interaction, Tool
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
        requests = _extract_requests(raw)
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
            activities=_activities_from_response(req.get("response")),
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
    wj = ws_dir / "workspace.json"
    try:
        data = json.loads(wj.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    folder = str(data.get("folder", ""))

    if folder.startswith("file:///"):
        # file:///Users/yen/repo -> /Users/yen/repo
        return unquote(folder[len("file://") :])

    if folder.startswith("vscode-remote://"):
        rest = folder[len("vscode-remote://") :]
        authority, _, path = rest.partition("/")
        # dev-container authorities encode the real local path as a hex JSON blob
        # (e.g. dev-container%2B<hex>); recover the host path so the project name
        # is meaningful instead of the opaque "/workspaces/..." mount point.
        if authority.startswith("dev-container%2B"):
            host = _devcontainer_host_path(authority[len("dev-container%2B") :])
            if host:
                return host
        # ssh-remote://ssh-remote%2B<host>/path/to/repo -> /path/to/repo
        return unquote("/" + path) if path else unquote(rest)

    return folder


def _devcontainer_host_path(hex_blob: str) -> str:
    """Decode a dev-container authority's hex-encoded JSON to a real path.

    The blob decodes to JSON like ``{"hostPath": "/Users/yen/Desktop/app", ...}``
    (a bind-mounted folder) or ``{"volumeName": "x", "folder": "x"}`` (a named
    volume with no host path). Prefer the host path; fall back to the folder name.
    """
    try:
        data = json.loads(bytes.fromhex(hex_blob).decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return ""
    host = data.get("hostPath")
    if isinstance(host, str) and host:
        return host
    folder = data.get("folder")
    return folder if isinstance(folder, str) else ""


def _extract_requests(raw: str) -> list[dict[str, Any]]:
    """Recover every chat request from a session file, across both log formats.

    Newer VS Code writes a *patch stream*: a JSONL file whose first line
    (``kind:0``) is a full session snapshot and whose later lines are
    incremental edits to it — ``kind:1`` sets the value at a key path ``k``,
    ``kind:2`` appends to the array at ``k`` (this is how streamed response
    chunks accumulate). We replay the patches to rebuild the final session, then
    read ``requests`` from it.

    Older files are a single JSON object (or plain JSONL) that already contains
    the requests inline, so we fall back to walking the tree for them.
    """
    objects = _load_objects(raw)
    snapshot = _apply_patch_stream(objects)
    if snapshot is not None:
        reqs = snapshot.get("requests")
        if isinstance(reqs, list):
            return [r for r in reqs if isinstance(r, dict) and r.get("requestId")]

    out: list[dict[str, Any]] = []
    for obj in objects:
        _collect_requests(obj, out)
    return out


def _apply_patch_stream(objects: list[Any]) -> dict[str, Any] | None:
    """Replay a ``{kind, k, v}`` patch stream into the initial snapshot.

    Returns the rebuilt session dict, or ``None`` if these objects aren't a
    patch stream (so the caller can fall back to the inline-request format).
    """
    if not objects:
        return None
    first = objects[0]
    if not isinstance(first, dict) or first.get("kind") != 0:
        return None
    if not isinstance(first.get("v"), dict):
        return None
    snapshot: dict[str, Any] = first["v"]
    for patch in objects[1:]:
        if not isinstance(patch, dict):
            continue
        kind, key, value = patch.get("kind"), patch.get("k"), patch.get("v")
        if not isinstance(key, list) or not key:
            continue
        try:
            _apply_patch(snapshot, kind, key, value)
        except (KeyError, IndexError, TypeError):
            # A patch may reference a path that doesn't exist yet; skip it
            # rather than abandoning the whole session.
            continue
    return snapshot


def _apply_patch(root: Any, kind: Any, key: list[Any], value: Any) -> None:
    cur = root
    for step in key[:-1]:
        cur = cur[step]
    last = key[-1]
    if kind == 2:  # append to the array at this path (streamed chunks)
        target = cur[last]
        if isinstance(value, list):
            target.extend(value)
        else:
            target.append(value)
    else:  # kind == 1: set/overwrite the value at this path
        cur[last] = value


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


# Copilot prefixes built-in tool ids with "copilot_"; strip it so names read
# cleanly (copilot_readFile -> readFile) and align with other tools' style.
_FILE_URI_RE = re.compile(r"file://(/[^\s)\"]+)")


def _activities_from_response(response: Any) -> list[Activity]:
    """Pull tool calls out of a Copilot response stream.

    Each ``toolInvocationSerialized`` part is one action. ``toolId`` is the tool
    (``copilot_readFile`` -> ``readFile``); ``source`` of type ``mcp`` carries the
    MCP server's ``serverLabel``; and file tools embed the path either in
    ``invocationMessage`` (a ``file://`` URI) or, for terminal runs, we record the
    command's ``cwd``. This mirrors the Claude Code activity extraction so both
    tools feed the same Activity Analysis view.
    """
    if not isinstance(response, list):
        return []
    activities: list[Activity] = []
    for part in response:
        if not isinstance(part, dict) or part.get("kind") != "toolInvocationSerialized":
            continue
        tool_id = part.get("toolId")
        if not tool_id:
            continue
        kind = _normalize_tool_id(str(tool_id))

        source = part.get("source")
        mcp_server = None
        if isinstance(source, dict) and source.get("type") == "mcp":
            # ``label`` is a short server name (e.g. "GitKraken", "pencil");
            # ``serverLabel`` is sometimes a long description, so prefer label.
            mcp_server = source.get("label") or source.get("serverLabel")

        target = _tool_target(part)
        activities.append(Activity(kind=kind, mcp_server=mcp_server, target=target))
    return activities


def _normalize_tool_id(tool_id: str) -> str:
    if tool_id.startswith("copilot_"):
        return tool_id[len("copilot_") :]
    return tool_id


def _tool_target(part: dict[str, Any]) -> str | None:
    """Best-effort file path / working dir a Copilot tool acted on."""
    tsd = part.get("toolSpecificData")
    if isinstance(tsd, dict):
        # Terminal runs carry the working directory they ran in.
        cwd = tsd.get("cwd")
        if isinstance(cwd, str) and cwd:
            return cwd
    # File tools embed the path as a file:// URI inside the invocation message.
    msg = part.get("invocationMessage")
    text = msg.get("value") if isinstance(msg, dict) else msg
    if isinstance(text, str):
        m = _FILE_URI_RE.search(text)
        if m:
            return unquote(m.group(1))
    return None


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
