"""Collector for the Hermes Agent (NousResearch).

Hermes stores all CLI / messaging sessions in a single SQLite database at
``~/.hermes/state.db`` (FTS5-backed). Two tables matter:

- ``sessions`` — one row per session, carrying the ``model`` and start time.
- ``messages`` — one row per turn, with a ``role`` (user / assistant / system /
  tool), the text ``content``, and a per-message ``token_count``.

Hermes records a single ``token_count`` per message rather than an input/output
split, so we attribute it by role: an ``assistant`` message's tokens are output,
everything else (user / system / tool) is input. The model is taken from the
owning session. These are **real** token counts the agent records, so Hermes
interactions are exact, not estimated.

Schemas have shifted across Hermes versions, so column discovery is defensive:
we read ``PRAGMA table_info`` and fall back across common column names. The DB is
opened strictly read-only (``mode=ro``) and never modified.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

from agent_roi.collectors.base import Collector
from agent_roi.core.models import Interaction, Tool
from agent_roi.core.platform import find_tool_dirs

# Candidate column names per logical field, in priority order. The first one
# that exists in a given table wins.
_MESSAGE_COLS = {
    "session_id": ["session_id", "sessionId", "session", "conversation_id"],
    "role": ["role", "author", "sender"],
    "content": ["content", "text", "body", "message"],
    "tokens": ["token_count", "tokens", "total_tokens", "num_tokens"],
    "timestamp": ["created_at", "timestamp", "ts", "time", "created"],
    "id": ["id", "rowid", "message_id"],
}
_SESSION_COLS = {
    "id": ["id", "session_id", "sessionId"],
    "model": ["model", "model_name", "llm"],
    "started": ["started_at", "created_at", "started", "timestamp"],
}


class HermesCollector(Collector):
    tool = Tool.HERMES
    name = "hermes"

    def __init__(self, roots: list[Path] | None = None) -> None:
        self.roots = roots if roots is not None else find_tool_dirs(".hermes")

    def is_available(self) -> bool:
        return any(self._db_files())

    def search_paths(self) -> list[Path]:
        return list(self.roots)

    def count_files(self) -> int:
        return len(self._db_files())

    def _db_files(self) -> list[Path]:
        files: list[Path] = []
        for root in self.roots:
            db = root / "state.db"
            try:
                if db.is_file():
                    files.append(db)
            except OSError:
                pass
        return files

    def collect(self) -> Iterator[Interaction]:
        for db in self._db_files():
            yield from self._parse_db(db)

    def _parse_db(self, db: Path) -> Iterator[Interaction]:
        try:
            conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        except sqlite3.Error:
            return
        try:
            conn.row_factory = sqlite3.Row
            tables = {
                row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            if "messages" not in tables:
                return
            sessions = self._load_sessions(conn, tables)
            yield from self._iter_messages(conn, sessions)
        except sqlite3.Error:
            return
        finally:
            conn.close()

    def _load_sessions(
        self, conn: sqlite3.Connection, tables: set[str]
    ) -> dict[str, tuple[str, datetime]]:
        """Map session id -> (model, started_at) from the sessions table."""
        if "sessions" not in tables:
            return {}
        cols = _resolve_cols(conn, "sessions", _SESSION_COLS)
        id_col = cols.get("id")
        if id_col is None:
            return {}
        model_col = cols.get("model")
        started_col = cols.get("started")
        sessions: dict[str, tuple[str, datetime]] = {}
        for row in conn.execute("SELECT * FROM sessions"):
            sid = str(row[id_col])
            model = _normalize_model(str(row[model_col])) if model_col else "hermes"
            started = _parse_ts(row[started_col]) if started_col else _now()
            sessions[sid] = (model, started)
        return sessions

    def _iter_messages(
        self,
        conn: sqlite3.Connection,
        sessions: dict[str, tuple[str, datetime]],
    ) -> Iterator[Interaction]:
        cols = _resolve_cols(conn, "messages", _MESSAGE_COLS)
        sid_col = cols.get("session_id")
        tok_col = cols.get("tokens")
        if sid_col is None or tok_col is None:
            return
        role_col = cols.get("role")
        content_col = cols.get("content")
        ts_col = cols.get("timestamp")
        id_col = cols.get("id")

        seq_by_session: dict[str, int] = {}
        for row in conn.execute("SELECT * FROM messages"):
            tokens = _as_int(row[tok_col])
            if tokens <= 0:
                continue
            sid = str(row[sid_col])
            model, started = sessions.get(sid, ("hermes", _now()))
            role = str(row[role_col]).lower() if role_col and row[role_col] else "assistant"
            is_output = role.startswith("assistant") or role == "model"

            seq_by_session[sid] = seq_by_session.get(sid, 0) + 1
            seq = seq_by_session[sid]
            msg_id = str(row[id_col]) if id_col and row[id_col] is not None else str(seq)
            ts = _parse_ts(row[ts_col]) if ts_col and row[ts_col] is not None else started
            content = str(row[content_col]) if content_col and row[content_col] else ""

            yield Interaction(
                id=f"hermes:{sid}:{msg_id}",
                tool=self.tool,
                session_id=sid,
                timestamp=ts,
                model=model,
                input_tokens=0 if is_output else tokens,
                output_tokens=tokens if is_output else 0,
                summary=content[:600],
            )

    def note(self) -> str:
        if not self._db_files() and self.roots:
            return "Found ~/.hermes but no state.db yet."
        return ""


def _resolve_cols(
    conn: sqlite3.Connection, table: str, wanted: dict[str, list[str]]
) -> dict[str, str]:
    """Pick the actual column name for each logical field, by availability."""
    available = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    resolved: dict[str, str] = {}
    for field, candidates in wanted.items():
        for candidate in candidates:
            if candidate in available:
                resolved[field] = candidate
                break
    return resolved


def _as_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return 0
    return 0


def _normalize_model(model: str) -> str:
    # Hermes reports provider-prefixed ids like "anthropic/claude-opus-4-8" or
    # "openai/gpt-5"; strip the provider and normalize dots for pricing lookup.
    name = model.split("/")[-1].strip()
    return name.replace(".", "-") if name else "hermes"


def _parse_ts(raw: object) -> datetime:
    # Hermes timestamps may be ISO-8601 strings or unix epoch (s or ms).
    if isinstance(raw, (int, float)):
        seconds = raw / 1000 if raw > 1e12 else raw
        try:
            return datetime.fromtimestamp(seconds, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return _now()
    if isinstance(raw, str):
        text = raw.strip()
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            if text.isdigit():
                return _parse_ts(int(text))
    return _now()


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)
