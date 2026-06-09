"""Tests for storage upsert idempotency and topic rollup."""

from __future__ import annotations

from datetime import datetime

from agent_roi.core.models import Interaction, Tool
from agent_roi.storage import Database


def _itx(id_: str, topic=None, out=100) -> Interaction:
    return Interaction(
        id=id_,
        tool=Tool.CLAUDE_CODE,
        session_id="s",
        timestamp=datetime(2026, 5, 4),
        model="claude-haiku-4-5",
        input_tokens=0,
        output_tokens=out,
        topic=topic,
        summary="some work",
    )


def test_upsert_is_idempotent(tmp_path):
    db = Database(tmp_path / "t.db")
    db.upsert_many([_itx("a"), _itx("b")])
    db.upsert_many([_itx("a"), _itx("b")])  # re-ingest
    rollups = db.rollup("topic")
    total = sum(r.interactions for r in rollups)
    assert total == 2  # not 4


def test_reingest_preserves_topic(tmp_path):
    db = Database(tmp_path / "t.db")
    db.upsert_many([_itx("a")])
    db.set_session_topic("s", "auth refactor")
    db.upsert_many([_itx("a")])  # incoming row has topic=None
    rows = db.unclassified()
    assert rows == []  # topic was preserved, so nothing unclassified


def test_rollup_groups_by_topic(tmp_path):
    db = Database(tmp_path / "t.db")
    db.upsert_many([_itx("a", topic="auth"), _itx("b", topic="auth"), _itx("c", topic="ci")])
    rollups = {r.key: r for r in db.rollup("topic")}
    assert rollups["auth"].interactions == 2
    assert rollups["ci"].interactions == 1


def test_migrates_db_missing_estimated_column(tmp_path):
    """A database created before the 'estimated' column was added must be
    upgraded on open, not 500 on query."""
    import sqlite3

    path = tmp_path / "old.db"
    # Build an old-schema table without the 'estimated' column.
    con = sqlite3.connect(path)
    con.execute(
        "CREATE TABLE interactions ("
        "id TEXT PRIMARY KEY, tool TEXT, session_id TEXT, timestamp DATETIME, "
        "model TEXT, input_tokens INT, output_tokens INT, cache_read_tokens INT, "
        "cache_write_tokens INT, summary TEXT, topic TEXT, cost_usd FLOAT)"
    )
    con.execute(
        "INSERT INTO interactions VALUES "
        "('x','claude_code','s','2026-05-04','claude-haiku-4-5',0,100,0,0,'','auth',0.0)"
    )
    con.commit()
    con.close()

    # Opening it should add the column; querying should work, not raise.
    db = Database(path)
    rollups = db.rollup("topic")
    assert rollups[0].interactions == 1
    assert rollups[0].estimated is False
