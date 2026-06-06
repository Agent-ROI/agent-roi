"""Collector for the Hermes Agent (NousResearch).

Hermes stores all CLI / messaging sessions in a single SQLite database at
``~/.hermes/state.db`` (FTS5-backed). Two tables matter:

- ``sessions`` — one row per session. Crucially, Hermes **aggregates exact token
  usage per session**: ``input_tokens``, ``output_tokens``, ``cache_read_tokens``,
  ``cache_write_tokens`` and ``reasoning_tokens``, plus the ``model``, ``title``,
  ``cwd`` and ``started_at``.
- ``messages`` — one row per turn, with a ``role`` and per-message ``token_count``
  (a single total, *not* an input/output split).

Hermes is unusual among the tools we read: it is a multi-provider router. The
same agent uses Claude via a Copilot subscription, NVIDIA models via OpenRouter's
free tier, local Ollama models, and so on. Model ids therefore vary in shape
(``anthropic/claude-opus-4.6``, ``claude-sonnet-4.6``, ``gpt-oss:20b``,
``nvidia/...:free``); we strip any provider prefix and normalize ``.`` to ``-``
so the shared pricing table resolves them (and unknown/free/local models price at
$0, which is correct for them).

Because the session row already carries the **exact, properly-split** token
counts — including cache reads, which are priced ~10× lower than fresh input and
dominate agent workloads — we emit **one interaction per session** straight from
those columns rather than guessing an input/output split from per-message totals.
``reasoning_tokens`` are folded into output (matching the Gemini collector). The
token counts are real, so Hermes interactions are exact, not estimated.

For older Hermes databases that predate the per-session token columns, we fall
back to summing per-message ``token_count`` (attributed by role). Schemas have
shifted across versions, so column discovery is defensive (``PRAGMA table_info``
with fallback names). The DB is opened strictly read-only and never modified.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

from agent_roi.collectors.base import Collector
from agent_roi.core.models import Interaction, Tool
from agent_roi.core.platform import find_tool_dirs
from agent_roi.core.project import project_for

# Candidate column names per logical field, in priority order. The first one
# that exists in a given table wins.
_SESSION_COLS = {
    "id": ["id", "session_id", "sessionId"],
    "model": ["model", "model_name", "llm"],
    "started": ["started_at", "created_at", "started", "timestamp"],
    "title": ["title", "summary", "name"],
    "cwd": ["cwd", "working_dir", "workdir"],
    "input": ["input_tokens", "prompt_tokens"],
    "output": ["output_tokens", "completion_tokens"],
    "cache_read": ["cache_read_tokens", "cached_tokens"],
    "cache_write": ["cache_write_tokens", "cache_creation_tokens"],
    "reasoning": ["reasoning_tokens", "thinking_tokens"],
}
_MESSAGE_COLS = {
    "session_id": ["session_id", "sessionId", "session", "conversation_id"],
    "role": ["role", "author", "sender"],
    "content": ["content", "text", "body", "message"],
    "tokens": ["token_count", "tokens", "total_tokens", "num_tokens"],
    "timestamp": ["timestamp", "created_at", "ts", "time", "created"],
    "id": ["id", "rowid", "message_id"],
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
            if "sessions" not in tables:
                return
            cols = _resolve_cols(conn, "sessions", _SESSION_COLS)
            if cols.get("id") is None:
                return
            # Prefer the exact per-session token columns; fall back to summing
            # per-message tokens only for older schemas that lack them.
            if cols.get("input") or cols.get("output") or cols.get("cache_read"):
                yield from self._iter_sessions(conn, cols)
            elif "messages" in tables:
                yield from self._iter_messages_legacy(conn, cols)
        except sqlite3.Error:
            return
        finally:
            conn.close()

    def _iter_sessions(
        self, conn: sqlite3.Connection, cols: dict[str, str]
    ) -> Iterator[Interaction]:
        """Emit one interaction per session from its exact token columns."""
        id_col = cols["id"]
        rows = list(conn.execute("SELECT * FROM sessions"))

        # The session ``title`` is the ideal classifier input, but many sessions
        # have none. For those, fall back to their first user message so they
        # still cluster into a topic instead of landing in "uncategorized".
        needs_summary = [
            str(r[id_col]) for r in rows if not str(_col(r, cols, "title") or "").strip()
        ]
        fallback = self._first_user_messages(conn, needs_summary)

        for row in rows:
            inp = _as_int(_col(row, cols, "input"))
            out = _as_int(_col(row, cols, "output"))
            cache_read = _as_int(_col(row, cols, "cache_read"))
            cache_write = _as_int(_col(row, cols, "cache_write"))
            reasoning = _as_int(_col(row, cols, "reasoning"))
            if inp <= 0 and out <= 0 and cache_read <= 0 and cache_write <= 0:
                continue

            sid = str(row[id_col])
            model = _normalize_model(str(_col(row, cols, "model") or "hermes"))
            started = _parse_ts(_col(row, cols, "started"))
            title = str(_col(row, cols, "title") or "").strip()
            cwd = str(_col(row, cols, "cwd") or "")
            summary = title or fallback.get(sid, "")

            yield Interaction(
                id=f"hermes:{sid}",
                tool=self.tool,
                session_id=sid,
                timestamp=started,
                model=model,
                input_tokens=inp,
                output_tokens=out + reasoning,  # fold reasoning into output
                cache_read_tokens=cache_read,
                cache_write_tokens=cache_write,
                cwd=cwd,
                project=project_for(cwd),
                summary=summary[:600],
            )

    def _first_user_messages(
        self, conn: sqlite3.Connection, session_ids: list[str]
    ) -> dict[str, str]:
        """First non-empty user message per session (classifier fallback)."""
        if not session_ids:
            return {}
        cols = _resolve_cols(conn, "messages", _MESSAGE_COLS)
        sid_col = cols.get("session_id")
        content_col = cols.get("content")
        if sid_col is None or content_col is None:
            return {}
        role_col = cols.get("role")
        order = cols.get("timestamp") or cols.get("id") or sid_col

        out: dict[str, str] = {}
        # Chunk the IN clause to stay well under SQLite's parameter limit.
        for start in range(0, len(session_ids), 400):
            chunk = session_ids[start : start + 400]
            placeholders = ",".join("?" for _ in chunk)
            where = f"{sid_col} IN ({placeholders}) AND {content_col} IS NOT NULL"
            if role_col:
                where += f" AND lower({role_col})='user'"
            query = f"SELECT * FROM messages WHERE {where} ORDER BY {sid_col}, {order}"
            for row in conn.execute(query, chunk):
                sid = str(row[sid_col])
                if sid in out:
                    continue  # ORDER BY keeps the earliest per session
                content = str(row[content_col] or "").strip()
                if content:
                    out[sid] = content
        return out

    def _iter_messages_legacy(
        self, conn: sqlite3.Connection, session_cols: dict[str, str]
    ) -> Iterator[Interaction]:
        """Older Hermes: no per-session token columns, so sum per-message tokens.

        ``token_count`` is a single total per message without an input/output
        split, so we attribute it by role (assistant -> output, else input).
        """
        sessions = self._load_session_meta(conn, session_cols)
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
            model, started, cwd = sessions.get(sid, ("hermes", _now(), ""))
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
                cwd=cwd,
                project=project_for(cwd),
                summary=content[:600],
            )

    def _load_session_meta(
        self, conn: sqlite3.Connection, cols: dict[str, str]
    ) -> dict[str, tuple[str, datetime, str]]:
        """Map session id -> (model, started_at, cwd) for the legacy path."""
        id_col = cols["id"]
        meta: dict[str, tuple[str, datetime, str]] = {}
        for row in conn.execute("SELECT * FROM sessions"):
            sid = str(row[id_col])
            model = _normalize_model(str(_col(row, cols, "model") or "hermes"))
            started = _parse_ts(_col(row, cols, "started"))
            cwd = str(_col(row, cols, "cwd") or "")
            meta[sid] = (model, started, cwd)
        return meta

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


def _col(row: sqlite3.Row, cols: dict[str, str], field: str) -> object:
    """Value of a logical field on *row*, or None if the column is absent."""
    name = cols.get(field)
    return row[name] if name is not None else None


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
    # Hermes reports provider-prefixed ids like "anthropic/claude-opus-4.6" or
    # "openai/gpt-5"; strip the provider and normalize dots so pricing resolves
    # exactly (e.g. "claude-sonnet-4.6" -> "claude-sonnet-4-6", which otherwise
    # prefix-matches the older "claude-sonnet-4").
    name = model.split("/")[-1].strip()
    return name.replace(".", "-") if name else "hermes"


def _parse_ts(raw: object) -> datetime:
    # Hermes timestamps may be unix epoch (s or ms, as int/float) or ISO-8601.
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
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
