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
    rollups = db.rollup_by_topic()
    total = sum(r.interactions for r in rollups)
    assert total == 2  # not 4


def test_reingest_preserves_topic(tmp_path):
    db = Database(tmp_path / "t.db")
    db.upsert_many([_itx("a")])
    db.set_topic("a", "auth refactor")
    db.upsert_many([_itx("a")])  # incoming row has topic=None
    rows = db.unclassified()
    assert rows == []  # topic was preserved, so nothing unclassified


def test_rollup_groups_by_topic(tmp_path):
    db = Database(tmp_path / "t.db")
    db.upsert_many([_itx("a", topic="auth"), _itx("b", topic="auth"), _itx("c", topic="ci")])
    rollups = {r.topic: r for r in db.rollup_by_topic()}
    assert rollups["auth"].interactions == 2
    assert rollups["ci"].interactions == 1
