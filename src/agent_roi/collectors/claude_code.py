"""Collector for Claude Code.

Claude Code stores one JSONL file per session under
``~/.claude/projects/<encoded-project-path>/<session-id>.jsonl``. Each line is a
JSON object; assistant turns carry a ``message.usage`` block with token counts.
We read these files read-only and never modify them.

We emit one :class:`Interaction` per assistant turn (those are the ones with
token usage), but we build each interaction's ``summary`` from both the user's
request and the assistant's reply. Many assistant turns are pure tool calls with
no prose, so using assistant text alone leaves most summaries empty — which makes
topic discovery impossible. Carrying the preceding user message keeps the topic
signal intact.
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
from agent_roi.core.project import project_for

_SUMMARY_MAX = 600


class ClaudeCodeCollector(Collector):
    tool = Tool.CLAUDE_CODE
    name = "claude_code"

    def __init__(self, roots: list[Path] | None = None) -> None:
        # Supports multiple roots so WSL can also read Windows-side logs.
        self.roots = roots if roots is not None else find_tool_dirs(".claude", "projects")

    def is_available(self) -> bool:
        return bool(self.roots)

    def search_paths(self) -> list[Path]:
        return list(self.roots)

    def count_files(self) -> int:
        return sum(1 for root in self.roots for _ in root.rglob("*.jsonl"))

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

        last_user_text = ""
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            message = record.get("message")
            if not isinstance(message, dict):
                continue

            role = message.get("role") or record.get("type")
            text = _text_from_content(message.get("content"))

            if role == "user":
                # Remember the latest user intent to attach to the next reply.
                if text:
                    last_user_text = text
                continue

            usage = message.get("usage")
            if not isinstance(usage, dict):
                continue

            interaction = self._to_interaction(
                record, message, usage, session_id, last_user_text, text
            )
            if interaction is not None:
                yield interaction

    def _to_interaction(
        self,
        record: dict[str, Any],
        message: dict[str, Any],
        usage: dict[str, Any],
        session_id: str,
        user_text: str,
        assistant_text: str,
    ) -> Interaction | None:
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

        cwd = str(record.get("cwd", ""))
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
            cwd=cwd,
            project=project_for(cwd),
            summary=_combine_summary(user_text, assistant_text),
        )


def _combine_summary(user_text: str, assistant_text: str) -> str:
    """Build a topic-bearing summary, preferring the user's request first."""
    parts = [p for p in (user_text, assistant_text) if p]
    return " ".join(parts)[:_SUMMARY_MAX]


def _text_from_content(content: object) -> str:
    """Extract human-readable text from a Claude message ``content`` field.

    Content may be a plain string or a list of typed blocks. We keep prose
    (``text``) and tool *names* (``tool_use``) as topic signal, but deliberately
    skip ``tool_result`` bodies: those carry command output (e.g. ``ls -l``
    listings, file dumps) that pollutes topic labels with noise like permission
    bits and paths rather than describing the task.
    """
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""

    pieces: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        btype = block.get("type")
        if btype == "text":
            pieces.append(str(block.get("text", "")))
        elif btype == "tool_use":
            name = block.get("name")
            if name:
                pieces.append(str(name))
    return " ".join(p for p in pieces if p).strip()
