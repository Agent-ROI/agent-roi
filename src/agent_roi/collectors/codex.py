"""Collector for OpenAI Codex CLI.

Codex CLI stores rollout/session logs as JSONL under ``~/.codex/sessions``.
Token usage is reported in ``token_count`` / ``usage`` events. Formats have
shifted across Codex versions, so this parser is defensive and skips records it
does not recognize rather than failing the whole ingest.
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


class CodexCollector(Collector):
    tool = Tool.CODEX
    name = "codex"

    def __init__(self, roots: list[Path] | None = None) -> None:
        self.roots = roots if roots is not None else find_tool_dirs(".codex", "sessions")

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
        seq = 0
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            usage = _find_usage(record)
            if usage is None:
                continue
            seq += 1
            yield Interaction(
                id=f"{session_id}:{seq}",
                tool=self.tool,
                session_id=session_id,
                timestamp=_parse_ts(record.get("timestamp")),
                model=str(record.get("model") or usage.get("model") or "unknown"),
                input_tokens=int(usage.get("input_tokens", usage.get("prompt_tokens", 0))),
                output_tokens=int(usage.get("output_tokens", usage.get("completion_tokens", 0))),
                cache_read_tokens=int(usage.get("cached_input_tokens", 0)),
                summary=str(record.get("summary", ""))[:500],
            )


def _find_usage(record: dict[str, Any]) -> dict[str, Any] | None:
    """Locate a usage/token_count dict in the various shapes Codex emits."""
    for key in ("usage", "token_count", "token_usage"):
        value = record.get(key)
        if isinstance(value, dict):
            return value
    payload = record.get("payload")
    if isinstance(payload, dict):
        return _find_usage(payload)
    return None


def _parse_ts(raw: object) -> datetime:
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now()
