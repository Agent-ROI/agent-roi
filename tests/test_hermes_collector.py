"""Tests for the Hermes collector against a realistic state.db fixture."""

from __future__ import annotations

import sqlite3

from agent_roi.collectors.hermes import HermesCollector
from agent_roi.core.models import Tool


def _make_db(root, *, messages, sessions):
    hermes = root / ".hermes"
    hermes.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(hermes / "state.db")
    conn.execute(
        "CREATE TABLE sessions (id TEXT PRIMARY KEY, source TEXT, model TEXT, "
        "started_at TEXT, token_count INTEGER)"
    )
    conn.execute(
        "CREATE TABLE messages (id INTEGER PRIMARY KEY, session_id TEXT, role TEXT, "
        "content TEXT, token_count INTEGER, created_at TEXT)"
    )
    conn.executemany("INSERT INTO sessions VALUES (?,?,?,?,?)", sessions)
    conn.executemany("INSERT INTO messages VALUES (?,?,?,?,?,?)", messages)
    conn.commit()
    conn.close()
    return root


def test_parses_messages_with_role_split_and_session_model(tmp_path):
    _make_db(
        tmp_path,
        sessions=[("s1", "cli", "anthropic/claude-opus-4-8", "2026-06-05T10:00:00Z", 300)],
        messages=[
            (1, "s1", "user", "add a hermes collector", 100, "2026-06-05T10:00:01Z"),
            (2, "s1", "assistant", "sure, here is the plan", 200, "2026-06-05T10:00:05Z"),
            (3, "s1", "assistant", "", 0, "2026-06-05T10:00:06Z"),  # zero tokens -> skipped
        ],
    )

    interactions = list(HermesCollector(roots=[tmp_path / ".hermes"]).collect())
    assert len(interactions) == 2

    user, assistant = interactions
    assert user.tool is Tool.HERMES
    assert user.session_id == "s1"
    # provider prefix stripped, dots normalized -> matches the pricing table
    assert user.model == "claude-opus-4-8"
    # user message tokens count as input, assistant as output
    assert user.input_tokens == 100
    assert user.output_tokens == 0
    assert assistant.output_tokens == 200
    assert assistant.input_tokens == 0
    # real counts, not estimated
    assert assistant.estimated is False
    assert user.summary == "add a hermes collector"
    # stable, unique ids
    assert user.id == "hermes:s1:1"
    assert assistant.id == "hermes:s1:2"


def test_is_available_requires_state_db(tmp_path):
    empty = tmp_path / ".hermes"
    empty.mkdir()
    assert HermesCollector(roots=[empty]).is_available() is False

    _make_db(
        tmp_path,
        sessions=[("s1", "cli", "openai/gpt-5", "2026-06-05T10:00:00Z", 10)],
        messages=[(1, "s1", "assistant", "hi", 10, "2026-06-05T10:00:01Z")],
    )
    collector = HermesCollector(roots=[tmp_path / ".hermes"])
    assert collector.is_available() is True
    assert collector.count_files() == 1
    assert list(collector.collect())[0].model == "gpt-5"
