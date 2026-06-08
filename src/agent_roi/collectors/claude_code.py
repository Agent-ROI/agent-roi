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
from agent_roi.core.models import Activity, Interaction, Tool
from agent_roi.core.platform import find_tool_dirs
from agent_roi.core.project import project_for
from agent_roi.core.tokens import estimate_tokens

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

        records = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

        # A tool call's result lands in a *later* user message, keyed by
        # tool_use_id. Pre-scan so we can attribute each result's size back to the
        # activity (how many tokens that tool returned into the context).
        result_tokens = _result_tokens_by_id(records)

        last_user_text = ""
        for record in records:
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
                record, message, usage, session_id, last_user_text, text, result_tokens
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
        result_tokens: dict[str, int],
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
            activities=_activities_from_content(message.get("content"), result_tokens),
        )


def _combine_summary(user_text: str, assistant_text: str) -> str:
    """Build a topic-bearing summary, preferring the user's request first."""
    parts = [p for p in (user_text, assistant_text) if p]
    return " ".join(parts)[:_SUMMARY_MAX]


def _activities_from_content(
    content: object, result_tokens: dict[str, int] | None = None
) -> list[Activity]:
    """Pull the concrete tool calls out of an assistant message's content.

    Each ``tool_use`` block is one action: its ``name`` is the tool (``Bash``,
    ``Read`` …), MCP tools are named ``mcp__<server>__<tool>``, and file tools
    carry a ``file_path``/``path`` we record as the target. ``result_tokens`` maps
    a tool_use id to the estimated size of the result it later returned, so each
    activity also knows how many tokens it pushed into the context.
    """
    if not isinstance(content, list):
        return []
    result_tokens = result_tokens or {}
    activities: list[Activity] = []
    for block in content:
        if not isinstance(block, dict) or block.get("type") != "tool_use":
            continue
        name = block.get("name")
        if not name:
            continue
        name = str(name)
        mcp_server = name.split("__")[1] if name.startswith("mcp__") and "__" in name[5:] else None
        target = None
        inp = block.get("input")
        if isinstance(inp, dict):
            fp = inp.get("file_path") or inp.get("path")
            if isinstance(fp, str) and fp:
                target = fp
        activities.append(
            Activity(
                kind=name,
                mcp_server=mcp_server,
                target=target,
                result_tokens=result_tokens.get(str(block.get("id")), 0),
            )
        )
    return activities


def _result_tokens_by_id(records: list[dict[str, Any]]) -> dict[str, int]:
    """Map each tool_use id to the estimated token size of its tool_result.

    tool_result blocks live in user messages and reference the call they answer
    via ``tool_use_id``; their body is the content the tool pushed back into the
    model's context. We estimate that body's size so a tool's "return volume" can
    be attributed per tool / MCP server.
    """
    sizes: dict[str, int] = {}
    for record in records:
        message = record.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            tid = block.get("tool_use_id")
            if not tid:
                continue
            body = block.get("content")
            text = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)
            sizes[str(tid)] = estimate_tokens(text)
    return sizes


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
