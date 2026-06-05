"""Collector for Claude Code.

Claude Code stores one JSONL file per session under
``~/.claude/projects/<encoded-project-path>/<session-id>.jsonl``. Each line is a
JSON object; assistant turns carry a ``message.usage`` block with token counts.
We read these files read-only and never modify them.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

from agent_roi.collectors.base import Collector
from agent_roi.core.models import Interaction, Tool
from agent_roi.core.platform import find_tool_dirs


class ClaudeCodeCollector(Collector):
    tool = Tool.CLAUDE_CODE
    name = "claude_code"

    def __init__(self, roots: list[Path] | None = None) -> None:
        # Supports multiple roots so WSL can also read Windows-side logs.
        self.roots = roots if roots is not None else find_tool_dirs(".claude", "projects")

    def is_available(self) -> bool:
        return bool(self.roots)

    def collect(self) -> Iterator[Interaction]:
        for root in self.roots:
            for jsonl in root.rglob("*.jsonl"):
                yield from self._parse_file(jsonl)

    def _parse_file(self, path: Path) -> Iterator[Interaction]:
        session_id = path.stem
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            interaction = self._to_interaction(record, session_id)
            if interaction is not None:
                yield interaction

    def _to_interaction(self, record: dict[str, Any], session_id: str) -> Interaction | None:
        message = record.get("message")
        if not isinstance(message, dict):
            return None
        usage = message.get("usage")
        if not isinstance(usage, dict):
            return None

        msg_id = message.get("id") or record.get("uuid")
        if not msg_id:
            return None

        ts_raw = record.get("timestamp")
        try:
            timestamp = (
                datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                if isinstance(ts_raw, str)
                else datetime.now()
            )
        except ValueError:
            timestamp = datetime.now()

        return Interaction(
            id=str(msg_id),
            tool=self.tool,
            session_id=session_id,
            timestamp=timestamp,
            model=message.get("model", "unknown"),
            input_tokens=int(usage.get("input_tokens", 0)),
            output_tokens=int(usage.get("output_tokens", 0)),
            cache_read_tokens=int(usage.get("cache_read_input_tokens", 0)),
            cache_write_tokens=int(usage.get("cache_creation_input_tokens", 0)),
            summary=_first_text(message.get("content")),
        )


def _first_text(content: object) -> str:
    """Pull a short text snippet from a message's content blocks for classification."""
    if isinstance(content, str):
        return content[:500]
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                return str(block.get("text", ""))[:500]
    return ""
