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


def test_estimated_badge_is_token_weighted(tmp_path):
    """A group dominated by exact tokens isn't badged estimated by a tiny minority.

    This is the Hermes case: hundreds of exact sessions plus a couple of
    estimated Copilot turns should read as exact, since the cost is near-exact.
    """
    big_exact = Interaction(
        id="exact",
        tool=Tool.HERMES,
        session_id="s",
        timestamp=datetime(2026, 5, 4, tzinfo=timezone.utc),
        model="claude-opus-4-6",
        input_tokens=1_000_000,
        topic="t",
        estimated=False,
    )
    tiny_estimated = Interaction(
        id="est",
        tool=Tool.COPILOT,
        session_id="s",
        timestamp=datetime(2026, 5, 4, tzinfo=timezone.utc),
        model="claude-opus-4-6",
        input_tokens=100,
        topic="t",
        estimated=True,
    )
    db = Database(tmp_path / "t.db")
    db.upsert_many([big_exact, tiny_estimated])

    # rollup, topic_breakdown total, and sessions all use the same rule.
    rollup = {r.key: r for r in db.rollup("topic")}["t"]
    assert rollup.estimated is False
    assert db.topic_breakdown("t").total.estimated is False
    assert db.sessions(topic="t")[0].estimated is False

    # Flip it: when estimated tokens dominate, the badge flips back on.
    db.upsert_many([tiny_estimated.model_copy(update={"id": "est2", "input_tokens": 5_000_000})])
    assert {r.key: r for r in db.rollup("topic")}["t"].estimated is True


def test_timeseries_daily_buckets(tmp_path):
    db = Database(tmp_path / "t.db")
    db.upsert_many(
        [
            _itx("a", ts=datetime(2026, 6, 1, 10, tzinfo=timezone.utc), topic="auth"),
            _itx("b", ts=datetime(2026, 6, 1, 12, tzinfo=timezone.utc), topic="auth"),
            _itx("c", ts=datetime(2026, 6, 2, 10, tzinfo=timezone.utc), topic="ci"),
        ]
    )
    bundle = db.timeseries()
    assert len(bundle.totals) == 2
    assert bundle.totals[0].date == "2026-06-01"
    assert bundle.totals[0].interactions == 2
    assert bundle.totals[0].total_tokens == 2000
    assert bundle.totals[1].interactions == 1
    assert bundle.tool_keys == ["claude_code"]
    assert bundle.by_tool[0].values["claude_code"] == 2000


def test_timeseries_monthly_buckets(tmp_path):
    db = Database(tmp_path / "t.db")
    db.upsert_many(
        [
            _itx("a", ts=datetime(2026, 5, 10, tzinfo=timezone.utc)),
            _itx("b", ts=datetime(2026, 5, 20, tzinfo=timezone.utc)),
            _itx("c", ts=datetime(2026, 6, 2, tzinfo=timezone.utc)),
        ]
    )
    bundle = db.timeseries(granularity="month")
    assert len(bundle.totals) == 2
    assert bundle.totals[0].date == "2026-05"
    assert bundle.totals[0].interactions == 2
    assert bundle.totals[1].date == "2026-06"


def test_until_excludes_later_rows(tmp_path):
    db = Database(tmp_path / "t.db")
    db.upsert_many(
        [
            _itx("a", ts=datetime(2026, 6, 1, tzinfo=timezone.utc)),
            _itx("b", ts=datetime(2026, 6, 10, tzinfo=timezone.utc)),
        ]
    )
    end = datetime(2026, 6, 6)
    rollups = db.rollup("topic", end=end)
    assert sum(r.interactions for r in rollups) == 1
