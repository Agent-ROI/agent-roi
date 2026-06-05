"""Collector for OpenAI Codex CLI.

Codex CLI stores one rollout log per session as JSONL under
``~/.codex/sessions/<YYYY>/<MM>/<DD>/rollout-*.jsonl``. Each line is a typed
record. The shapes we care about:

- ``session_meta``  — session id and start time.
- ``turn_context``  — carries the active ``model`` for subsequent turns.
- ``event_msg`` with ``payload.type == "token_count"`` — per-turn token usage in
  ``info.last_token_usage`` (input/cached/output/reasoning tokens).
- ``event_msg`` with ``payload.type in {"user_message","agent_message"}`` — text
  we keep a short snippet of for the classifier.

We emit one :class:`Interaction` per ``token_count`` event, using
``last_token_usage`` (the delta for that turn) so usage isn't double-counted from
the running ``total_token_usage``. The parser is defensive: unknown records are
skipped rather than failing the whole ingest.
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


class CodexCollector(Collector):
    tool = Tool.CODEX
    name = "codex"

    def __init__(self, roots: list[Path] | None = None) -> None:
        self.roots = roots if roots is not None else find_tool_dirs(".codex", "sessions")

    def is_available(self) -> bool:
        return bool(self.roots)

    def search_paths(self) -> list[Path]:
        return list(self.roots)

    def count_files(self) -> int:
        return sum(1 for root in self.roots for _ in root.rglob("rollout-*.jsonl"))

    def collect(self) -> Iterator[Interaction]:
        for root in self.roots:
            for jsonl in root.rglob("*.jsonl"):
                yield from self._parse_file(jsonl)

    def _parse_file(self, path: Path) -> Iterator[Interaction]:
        # Session id is the uuid at the end of the filename if present, else stem.
        session_id = path.stem.split("-")[-1] if "-" in path.stem else path.stem

        model = "unknown"
        cwd = ""
        last_user = ""
        last_agent = ""
        seq = 0

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

            rtype = record.get("type")
            payload = record.get("payload")
            payload = payload if isinstance(payload, dict) else {}

            if rtype == "turn_context":
                model = str(payload.get("model") or model)
                cwd = str(payload.get("cwd") or cwd)
                continue

            if rtype == "session_meta":
                cwd = str(payload.get("cwd") or cwd)
                continue

            if rtype != "event_msg":
                continue

            ptype = payload.get("type")
            if ptype == "user_message":
                text = _event_text(payload)
                if text:
                    last_user = text
            elif ptype == "agent_message":
                text = _event_text(payload)
                if text:
                    last_agent = text
            elif ptype == "token_count":
                usage = _last_usage(payload)
                if usage is None:
                    continue
                seq += 1
                yield Interaction(
                    id=f"codex:{session_id}:{seq}",
                    tool=self.tool,
                    session_id=session_id,
                    timestamp=_parse_ts(record.get("timestamp")),
                    model=_normalize_model(model),
                    input_tokens=int(usage.get("input_tokens", 0)),
                    output_tokens=(
                        int(usage.get("output_tokens", 0))
                        + int(usage.get("reasoning_output_tokens", 0))
                    ),
                    cache_read_tokens=int(usage.get("cached_input_tokens", 0)),
                    cwd=cwd,
                    project=project_for(cwd),
                    summary=_combine(last_user, last_agent),
                )


def _event_text(payload: dict[str, Any]) -> str:
    text = payload.get("message") or payload.get("text") or ""
    return text.strip() if isinstance(text, str) else ""


def _combine(user_text: str, agent_text: str) -> str:
    parts = [p for p in (user_text, agent_text) if p]
    return " ".join(parts)[:600]


def _last_usage(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Pull the per-turn token usage from a token_count event payload."""
    info = payload.get("info")
    if not isinstance(info, dict):
        return None
    usage = info.get("last_token_usage") or info.get("total_token_usage")
    return usage if isinstance(usage, dict) else None


def _normalize_model(model: str) -> str:
    # Codex reports e.g. "gpt-5.5"; normalize dots to dashes for pricing lookup.
    return model.replace(".", "-")


def _parse_ts(raw: object) -> datetime:
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now()
