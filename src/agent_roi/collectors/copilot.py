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
from agent_roi.core.tokens import estimate_tokens


class CopilotCollector(Collector):
    tool = Tool.COPILOT
    name = "copilot"

    def __init__(self, roots: list[Path] | None = None) -> None:
        # Each root is a VS Code "User" dir; chat sessions live under its
        # workspaceStorage subtree.
        self.roots = roots if roots is not None else vscode_user_dirs()

    def is_available(self) -> bool:
        return any((r / "workspaceStorage").is_dir() for r in self.roots)

    def collect(self) -> Iterator[Interaction]:
        for root in self.roots:
            ws = root / "workspaceStorage"
            if not ws.is_dir():
                continue
            for session in ws.glob("*/chatSessions/*.json*"):
                yield from self._parse_file(session)

    def _parse_file(self, path: Path) -> Iterator[Interaction]:
        session_id = path.stem
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            return
        for obj in _load_objects(raw):
            yield from self._requests_in(obj, session_id)

    def _requests_in(self, obj: Any, session_id: str) -> Iterator[Interaction]:
        """Walk an arbitrary JSON structure, yielding an Interaction per Copilot
        chat request found."""
        if isinstance(obj, dict):
            if obj.get("requestId") and "modelId" in obj:
                itx = self._to_interaction(obj, session_id)
                if itx is not None:
                    yield itx
            for value in obj.values():
                yield from self._requests_in(value, session_id)
        elif isinstance(obj, list):
            for value in obj:
                yield from self._requests_in(value, session_id)

    def _to_interaction(self, req: dict[str, Any], session_id: str) -> Interaction | None:
        request_id = req.get("requestId")
        if not request_id:
            return None

        user_text = _message_text(req.get("message"))
        response_text = _response_text(req.get("response"))

        model = str(req.get("modelId") or "unknown")
        return Interaction(
            id=f"copilot:{request_id}",
            tool=self.tool,
            session_id=session_id,
            timestamp=_parse_ts(req.get("timestamp")),
            model=_normalize_model(model),
            input_tokens=estimate_tokens(user_text),
            output_tokens=estimate_tokens(response_text),
            summary=user_text[:500],
            estimated=True,
        )


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
