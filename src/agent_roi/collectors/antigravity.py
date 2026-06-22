"""Collector for the Antigravity CLI (``agy`` / Google Antigravity).

Antigravity keeps one SQLite database per conversation under::

    ~/.gemini/antigravity-cli/conversations/<conversationId>.db

Each database has a ``gen_metadata`` table with one row per model generation
(one assistant turn). The row's ``data`` column is a protobuf blob; this module
walks the wire format directly (no ``.proto`` needed) to recover, per turn:

- the model id (``.1.19``, e.g. ``claude-opus-4-6-thinking``) and a human label
  (``.1.21``, e.g. ``Claude Opus 4.6 (Thinking)``);
- the token usage block (``.1.4`` — mirrored at ``.1.17.2``), whose sub-fields
  are ``1`` = system/tools prompt, ``2`` = fresh input, ``3`` = output,
  ``5`` = cache read; and
- a Unix-seconds timestamp (``.1.9.4.1``).

The conversation's working directory comes from the sibling
``trajectory_metadata_blob`` table, whose single row carries the workspace as a
``file://`` URL (``.7`` / ``.1.1``). Usage is **real** (reported by the tool),
so Antigravity interactions are exact, not estimated. Databases are opened
read-only and never written.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

from agent_roi.collectors.base import Collector
from agent_roi.core.models import Interaction, Tool
from agent_roi.core.platform import find_tool_dirs
from agent_roi.core.project import project_for

_SUMMARY_MAX = 600


class AntigravityCollector(Collector):
    tool = Tool.ANTIGRAVITY
    name = "antigravity"

    def __init__(self, roots: list[Path] | None = None) -> None:
        # Each root is a ``~/.gemini/antigravity-cli`` dir; conversation
        # databases live under ``conversations/``. Multiple roots support WSL
        # reading the Windows-side profile too.
        self.roots = (
            roots if roots is not None else find_tool_dirs(".gemini", "antigravity-cli")
        )

    def is_available(self) -> bool:
        return any(self._conversation_dbs(root) for root in self.roots)

    def search_paths(self) -> list[Path]:
        return [root / "conversations" for root in self.roots]

    def count_files(self) -> int:
        return sum(1 for root in self.roots for _ in self._conversation_dbs(root))

    def collect(self) -> Iterator[Interaction]:
        for root in self.roots:
            for db in self._conversation_dbs(root):
                yield from self._parse_db(db)

    @staticmethod
    def _conversation_dbs(root: Path) -> Iterator[Path]:
        yield from (root / "conversations").glob("*.db")

    def _parse_db(self, path: Path) -> Iterator[Interaction]:
        session = path.stem
        try:
            con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        except sqlite3.Error:
            return
        try:
            cwd = _workspace(con)
            project = project_for(cwd)
            try:
                rows = con.execute("SELECT data FROM gen_metadata ORDER BY idx").fetchall()
            except sqlite3.Error:
                return
            for seq, (blob,) in enumerate(rows):
                if not isinstance(blob, (bytes, bytearray)):
                    continue
                gen = _parse_generation(bytes(blob))
                if gen is None:
                    continue
                yield Interaction(
                    id=f"antigravity:{session}:{seq}",
                    tool=self.tool,
                    session_id=session,
                    timestamp=gen.timestamp,
                    model=gen.model,
                    input_tokens=gen.input_tokens,
                    output_tokens=gen.output_tokens,
                    cache_read_tokens=gen.cache_read_tokens,
                    cwd=cwd,
                    project=project,
                    summary=gen.label[:_SUMMARY_MAX],
                )
        finally:
            con.close()


# --- protobuf wire-format walking (minimal, no .proto needed) ---------------


def _read_varint(buf: bytes, i: int) -> tuple[int, int]:
    shift = 0
    result = 0
    n = len(buf)
    while True:
        if i >= n:
            raise IndexError("truncated varint")
        byte = buf[i]
        i += 1
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result, i
        shift += 7


def _fields(buf: bytes) -> Iterator[tuple[int, int, object]]:
    """Yield ``(field_number, wire_type, value)`` for one message level.

    Length-delimited values (wire type 2) yield their raw ``bytes``; varints
    (wire type 0) yield an ``int``. Malformed or truncated input stops
    iteration rather than raising, so a partially written blob is skipped.
    """
    i = 0
    n = len(buf)
    while i < n:
        try:
            tag, i = _read_varint(buf, i)
        except IndexError:
            return
        field = tag >> 3
        wire = tag & 7
        if wire == 0:
            try:
                value, i = _read_varint(buf, i)
            except IndexError:
                return
            yield field, 0, value
        elif wire == 2:
            try:
                length, i = _read_varint(buf, i)
            except IndexError:
                return
            if i + length > n:
                return
            yield field, 2, buf[i : i + length]
            i += length
        elif wire == 5:
            i += 4
        elif wire == 1:
            i += 8
        else:
            return


def _submessage(buf: bytes, *path: int) -> bytes | None:
    """Descend ``path`` of length-delimited fields, returning the leaf bytes."""
    current = buf
    for want in path:
        nxt: bytes | None = None
        for field, wire, value in _fields(current):
            if field == want and wire == 2 and isinstance(value, bytes):
                nxt = value
                break
        if nxt is None:
            return None
        current = nxt
    return current


def _varint_field(buf: bytes, field: int) -> int | None:
    for f, wire, value in _fields(buf):
        if f == field and wire == 0 and isinstance(value, int):
            return value
    return None


def _string_field(buf: bytes, field: int) -> str | None:
    for f, wire, value in _fields(buf):
        if f == field and wire == 2 and isinstance(value, bytes):
            try:
                return value.decode("utf-8")
            except UnicodeDecodeError:
                return None
    return None


class _Generation:
    __slots__ = (
        "model",
        "label",
        "timestamp",
        "input_tokens",
        "output_tokens",
        "cache_read_tokens",
    )

    def __init__(
        self,
        model: str,
        label: str,
        timestamp: datetime,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int,
    ) -> None:
        self.model = model
        self.label = label
        self.timestamp = timestamp
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.cache_read_tokens = cache_read_tokens


def _parse_generation(blob: bytes) -> _Generation | None:
    """Decode one ``gen_metadata`` row into model + usage + timestamp."""
    inner = _submessage(blob, 1)
    if inner is None:
        return None

    # Usage lives at .1.4 (mirrored at .1.17.2); take whichever is present.
    usage = _submessage(inner, 4) or _submessage(inner, 17, 2)
    if usage is None:
        return None
    system = _varint_field(usage, 1) or 0
    fresh_input = _varint_field(usage, 2) or 0
    output = _varint_field(usage, 3) or 0
    cache_read = _varint_field(usage, 5) or 0
    if fresh_input == 0 and output == 0 and cache_read == 0:
        return None

    model = _string_field(inner, 19) or "antigravity"
    label = _string_field(inner, 21) or model

    return _Generation(
        model=model,
        label=label,
        timestamp=_timestamp(inner),
        # The fixed system/tools prompt is billed as fresh (uncached) input.
        input_tokens=fresh_input + system,
        output_tokens=output,
        cache_read_tokens=cache_read,
    )


def _timestamp(inner: bytes) -> datetime:
    """Read the Unix-seconds turn timestamp at ``.1.9.4.1``."""
    gen_info = _submessage(inner, 9, 4)
    if gen_info is not None:
        secs = _varint_field(gen_info, 1)
        if secs:
            try:
                return datetime.fromtimestamp(secs)
            except (OverflowError, OSError, ValueError):
                pass
    return datetime.now()


def _workspace(con: sqlite3.Connection) -> str:
    """Recover the conversation's working directory from the metadata blob.

    The single ``trajectory_metadata_blob`` row carries the workspace as a
    ``file://`` URL at ``.7`` (also at ``.1.1``); decode it back to a path.
    """
    try:
        row = con.execute("SELECT data FROM trajectory_metadata_blob LIMIT 1").fetchone()
    except sqlite3.Error:
        return ""
    if not row or not isinstance(row[0], (bytes, bytearray)):
        return ""
    blob = bytes(row[0])
    url = _string_field(blob, 7) or _string_field(_submessage(blob, 1) or b"", 1)
    if not url:
        return ""
    if url.startswith("file://"):
        return unquote(urlparse(url).path)
    return url
