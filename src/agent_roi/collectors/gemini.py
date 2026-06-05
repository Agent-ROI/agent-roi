"""Collector for the Gemini CLI.

The Gemini CLI keeps one chat log per session under a per-project temp tree::

    ~/.gemini/tmp/<projectHash>/chats/session-<timestamp>-<id>.json
    ~/.gemini/tmp/<projectHash>/chats/session-<timestamp>-<id>.jsonl   # newer

``<projectHash>`` is ``sha256(cwd)``; the real working directory is written
verbatim next to the chats in ``~/.gemini/tmp/<projectHash>/.project_root`` (or
the parent of ``chats/``), which we read to recover a meaningful ``project``.

Both file shapes carry the same per-message structure — the difference is only
the container:

- ``.json``  — a single object ``{"sessionId", "projectHash", "messages": [...]}``
- ``.jsonl`` — one record per line; a ``kind: "main"`` header line, then one
  record per message (lines like ``{"$set": ...}`` are state deltas we skip).

Either way, ``type == "gemini"`` messages carry **real** token usage in a
``tokens`` block (``input``/``output``/``cached``/``thoughts``/``total``) plus the
``model``, so Gemini interactions are exact, not estimated. ``thoughts``
(reasoning) tokens are folded into output, and ``cached`` maps to cache reads.
Files are read read-only and never modified.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from agent_roi.collectors.base import Collector
from agent_roi.core.models import Interaction, Tool
from agent_roi.core.platform import find_tool_dirs
from agent_roi.core.project import project_for

_SUMMARY_MAX = 600


class GeminiCollector(Collector):
    tool = Tool.GEMINI
    name = "gemini"

    def __init__(self, roots: list[Path] | None = None) -> None:
        # Each root is a ``~/.gemini/tmp`` dir; chat logs live under
        # ``<projectHash>/chats/``. Multiple roots support WSL reading the
        # Windows-side profile too.
        self.roots = roots if roots is not None else find_tool_dirs(".gemini", "tmp")

    def is_available(self) -> bool:
        return any(self._chat_files(root) for root in self.roots)

    def search_paths(self) -> list[Path]:
        return list(self.roots)

    def count_files(self) -> int:
        return sum(1 for root in self.roots for _ in self._chat_files(root))

    def collect(self) -> Iterator[Interaction]:
        for root in self.roots:
            for chat in self._chat_files(root):
                yield from self._parse_file(chat)

    @staticmethod
    def _chat_files(root: Path) -> Iterator[Path]:
        # ``<projectHash>/chats/session-*.json{,l}`` — glob both extensions.
        yield from root.glob("*/chats/session-*.json")
        yield from root.glob("*/chats/session-*.jsonl")

    def _parse_file(self, path: Path) -> Iterator[Interaction]:
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            return

        cwd = _project_root_for(path)
        project = project_for(cwd)
        session_id = ""
        last_user = ""
        seq = 0

        for record in _records(raw):
            if not isinstance(record, dict):
                continue

            # Header / metadata: capture the session id once.
            sid = record.get("sessionId")
            if isinstance(sid, str) and sid:
                session_id = sid

            rtype = record.get("type")
            if rtype == "user":
                text = _content_text(record.get("content"))
                if text:
                    last_user = text
                continue
            if rtype != "gemini":
                continue

            tokens = record.get("tokens")
            if not isinstance(tokens, dict):
                continue

            seq += 1
            sess = session_id or path.stem
            assistant_text = _content_text(record.get("content"))
            yield Interaction(
                id=f"gemini:{sess}:{seq}",
                tool=self.tool,
                session_id=sess,
                timestamp=_parse_ts(record.get("timestamp")),
                model=str(record.get("model") or "gemini"),
                input_tokens=int(tokens.get("input", 0)),
                # Reasoning ("thoughts") tokens are billed like output.
                output_tokens=int(tokens.get("output", 0)) + int(tokens.get("thoughts", 0)),
                cache_read_tokens=int(tokens.get("cached", 0)),
                cwd=cwd,
                project=project,
                summary=_combine(last_user, assistant_text),
            )


def _records(raw: str) -> Iterator[Any]:
    """Yield message records from either container shape.

    A ``.json`` file is one object with a ``messages`` list; a ``.jsonl`` file is
    one record per line. We also yield the top-level object so callers can read
    ``sessionId`` from a ``.json``'s header.
    """
    stripped = raw.lstrip()
    if stripped.startswith("{") and '"messages"' in raw:
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            return
        if isinstance(obj, dict):
            yield obj  # header (sessionId, projectHash, ...)
            yield from obj.get("messages", [])
        return

    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


def _project_root_for(chat_file: Path) -> str:
    """Recover the real cwd for a chat file.

    Layout is ``<root>/<projectHash>/chats/<file>``. We try, in order:

    1. the ``.project_root`` marker in the ``<projectHash>`` dir (authoritative,
       written by newer Gemini CLI), then
    2. a reverse lookup of ``<projectHash>`` (which is ``sha256(cwd)``) against
       the cwds Gemini recorded in ``~/.gemini/projects.json`` — this recovers a
       real path for older sessions that predate the marker file.
    """
    project_dir = chat_file.parent.parent  # .../<projectHash>
    marker = project_dir / ".project_root"
    try:
        text = marker.read_text(encoding="utf-8").strip()
        if text:
            return text
    except OSError:
        pass

    gemini_home = project_dir.parent.parent  # .../.gemini
    return _hash_to_cwd(gemini_home).get(project_dir.name, "")


@lru_cache(maxsize=8)
def _hash_to_cwd(gemini_home: Path) -> dict[str, str]:
    """Map ``sha256(cwd) -> cwd`` for every project in ``projects.json``."""
    try:
        data = json.loads((gemini_home / "projects.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    projects = data.get("projects") if isinstance(data, dict) else None
    if not isinstance(projects, dict):
        return {}
    return {hashlib.sha256(cwd.encode()).hexdigest(): cwd for cwd in projects}


def _content_text(content: object) -> str:
    """Extract prose from a Gemini message ``content`` field (string or blocks)."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        pieces: list[str] = []
        for block in content:
            if isinstance(block, dict):
                text = block.get("text")
                if isinstance(text, str):
                    pieces.append(text)
            elif isinstance(block, str):
                pieces.append(block)
        return " ".join(p for p in pieces if p).strip()
    return ""


def _combine(user_text: str, assistant_text: str) -> str:
    parts = [p for p in (user_text, assistant_text) if p]
    return " ".join(parts)[:_SUMMARY_MAX]


def _parse_ts(raw: object) -> datetime:
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now()
