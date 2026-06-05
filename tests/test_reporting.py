"""Tests for multi-dimension rollups, time windows, and topic drill-down."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from agent_roi.core.models import Interaction, Tool
from agent_roi.storage import Database


def _itx(
    id_: str,
    tool=Tool.CLAUDE_CODE,
    model="claude-haiku-4-5",
    topic="auth",
    ts=None,
    est=False,
):
    return Interaction(
        id=id_,
        tool=tool,
        session_id="s",
        timestamp=ts or datetime(2026, 5, 4, tzinfo=timezone.utc),
        model=model,
        output_tokens=1000,
        topic=topic,
        estimated=est,
    )


def test_rollup_by_tool(tmp_path):
    db = Database(tmp_path / "t.db")
    db.upsert_many(
        [
            _itx("a", tool=Tool.CLAUDE_CODE),
            _itx("b", tool=Tool.CLAUDE_CODE),
            _itx("c", tool=Tool.COPILOT, est=True),
        ]
    )
    rollups = {r.key: r for r in db.rollup("tool")}
    assert rollups["claude_code"].interactions == 2
    assert rollups["copilot"].interactions == 1
    # Copilot is estimated; Claude Code is exact.
    assert rollups["copilot"].estimated is True
    assert rollups["claude_code"].estimated is False


def test_time_window_filters(tmp_path):
    db = Database(tmp_path / "t.db")
    now = datetime.now(tz=timezone.utc)
    db.upsert_many(
        [
            _itx("recent", ts=now - timedelta(hours=1)),
            _itx("old", ts=now - timedelta(days=30)),
        ]
    )
    recent = db.rollup("topic", start=now - timedelta(days=1))
    assert sum(r.interactions for r in recent) == 1


def test_topic_breakdown_splits_by_tool_and_model(tmp_path):
    db = Database(tmp_path / "t.db")
    db.upsert_many(
        [
            _itx("a", tool=Tool.CLAUDE_CODE, model="claude-opus-4-8", topic="auth"),
            _itx("b", tool=Tool.COPILOT, model="claude-haiku-4-5", topic="auth", est=True),
            _itx("c", tool=Tool.CLAUDE_CODE, model="claude-opus-4-8", topic="other"),
        ]
    )
    bd = db.topic_breakdown("auth")
    assert bd.total.interactions == 2  # only the 'auth' rows
    tools = {r.key for r in bd.by_tool}
    models = {r.key for r in bd.by_model}
    assert tools == {"claude_code", "copilot"}
    assert models == {"claude-opus-4-8", "claude-haiku-4-5"}
    assert bd.total.estimated is True  # one of the two is estimated
