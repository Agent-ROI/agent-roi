"""Tests for the Hermes collector against realistic state.db fixtures.

Hermes has two schema generations we support: the modern one carries exact
per-session token columns (preferred), and the legacy one only has per-message
``token_count`` totals (fallback). Both are covered here.
"""

from __future__ import annotations

import sqlite3

from agent_roi.collectors.hermes import HermesCollector
from agent_roi.core.models import Tool

# Modern sessions table: Hermes aggregates exact token usage per session.
_MODERN_SESSIONS_DDL = (
    "CREATE TABLE sessions (id TEXT PRIMARY KEY, source TEXT, model TEXT, "
    "title TEXT, cwd TEXT, started_at REAL, input_tokens INTEGER, "
    "output_tokens INTEGER, cache_read_tokens INTEGER, cache_write_tokens INTEGER, "
    "reasoning_tokens INTEGER)"
)
# Legacy sessions table: no per-session token columns at all.
_LEGACY_SESSIONS_DDL = (
    "CREATE TABLE sessions (id TEXT PRIMARY KEY, source TEXT, model TEXT, started_at TEXT)"
)
_MESSAGES_DDL = (
    "CREATE TABLE messages (id INTEGER PRIMARY KEY, session_id TEXT, role TEXT, "
    "content TEXT, token_count INTEGER, timestamp TEXT)"
)


def _make_db(root, *, sessions_ddl, sessions, messages=None):
    hermes = root / ".hermes"
    hermes.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(hermes / "state.db")
    conn.execute(sessions_ddl)
    conn.execute(_MESSAGES_DDL)
    placeholders = ",".join("?" for _ in sessions[0])
    conn.executemany(f"INSERT INTO sessions VALUES ({placeholders})", sessions)
    if messages:
        conn.executemany("INSERT INTO messages VALUES (?,?,?,?,?,?)", messages)
    conn.commit()
    conn.close()
    return root / ".hermes"


def test_modern_schema_uses_exact_per_session_tokens(tmp_path):
    """Preferred path: read the exact input/output/cache split off the session."""
    root = _make_db(
        tmp_path,
        sessions_ddl=_MODERN_SESSIONS_DDL,
        sessions=[
            # id, source, model, title, cwd, started_at, in, out, cr, cw, reasoning
            (
                "s1",
                "cli",
                "anthropic/claude-opus-4.6",
                "Add a hermes collector",
                "/home/u/repo/agent-roi",
                1780651817.9,
                1000,
                200,
                50000,
                300,
                40,
            ),
            # A session with no usage at all is skipped.
            ("s2", "cli", "claude-sonnet-4.6", "Idle", "", 1780651000.0, 0, 0, 0, 0, 0),
        ],
    )

    interactions = list(HermesCollector(roots=[root]).collect())
    assert len(interactions) == 1

    it = interactions[0]
    assert it.tool is Tool.HERMES
    assert it.session_id == "s1"
    # one interaction per session, stable id (no per-message suffix)
    assert it.id == "hermes:s1"
    # provider prefix stripped, dots normalized so pricing resolves exactly
    assert it.model == "claude-opus-4-6"
    # exact split straight from the session row
    assert it.input_tokens == 1000
    assert it.cache_read_tokens == 50000
    assert it.cache_write_tokens == 300
    # reasoning folded into output (200 + 40)
    assert it.output_tokens == 240
    # real counts, not estimated
    assert it.estimated is False
    # title feeds the classifier; project derived from cwd
    assert it.summary == "Add a hermes collector"
    assert it.project == "agent-roi"


def test_empty_title_falls_back_to_first_user_message(tmp_path):
    """No session title -> use the first user message so it still classifies."""
    root = _make_db(
        tmp_path,
        sessions_ddl=_MODERN_SESSIONS_DDL,
        sessions=[
            # empty title, but the session has messages
            ("s1", "cli", "claude-opus-4.6", "", "", 1780651817.9, 1000, 200, 0, 0, 0),
        ],
        messages=[
            # a non-user message first; the user message is what we want
            (1, "s1", "system", "you are a helpful agent", 50, "2026-06-05T10:00:00Z"),
            (2, "s1", "user", "compare claw3d and hermes3d", 30, "2026-06-05T10:00:01Z"),
            (3, "s1", "user", "and then summarize", 10, "2026-06-05T10:00:02Z"),
        ],
    )

    interactions = list(HermesCollector(roots=[root]).collect())
    assert len(interactions) == 1
    # first *user* message wins (not the system prompt, not the later turn)
    assert interactions[0].summary == "compare claw3d and hermes3d"


def test_legacy_schema_falls_back_to_per_message_tokens(tmp_path):
    """Older Hermes lacks per-session token columns -> sum messages by role."""
    root = _make_db(
        tmp_path,
        sessions_ddl=_LEGACY_SESSIONS_DDL,
        sessions=[("s1", "cli", "openai/gpt-5", "2026-06-05T10:00:00Z")],
        messages=[
            (1, "s1", "user", "add a hermes collector", 100, "2026-06-05T10:00:01Z"),
            (2, "s1", "assistant", "sure, here is the plan", 200, "2026-06-05T10:00:05Z"),
            (3, "s1", "assistant", "", 0, "2026-06-05T10:00:06Z"),  # zero tokens -> skipped
        ],
    )

    interactions = list(HermesCollector(roots=[root]).collect())
    assert len(interactions) == 2

    user, assistant = interactions
    assert user.model == "gpt-5"
    # user message tokens are input, assistant tokens are output
    assert user.input_tokens == 100
    assert user.output_tokens == 0
    assert assistant.output_tokens == 200
    assert assistant.input_tokens == 0
    assert assistant.estimated is False
    # per-message ids in the legacy path
    assert user.id == "hermes:s1:1"
    assert assistant.id == "hermes:s1:2"


def test_is_available_requires_state_db(tmp_path):
    empty = tmp_path / ".hermes"
    empty.mkdir()
    assert HermesCollector(roots=[empty]).is_available() is False

    root = _make_db(
        tmp_path,
        sessions_ddl=_MODERN_SESSIONS_DDL,
        sessions=[("s1", "cli", "gpt-oss:20b", "Local run", "", 1780651817.9, 50, 10, 0, 0, 0)],
    )
    collector = HermesCollector(roots=[root])
    assert collector.is_available() is True
    assert collector.count_files() == 1
    # local model id with a ":tag" is left as-is (prices at $0, which is correct)
    assert list(collector.collect())[0].model == "gpt-oss:20b"
