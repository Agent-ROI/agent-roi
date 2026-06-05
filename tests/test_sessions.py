"""Tests for the topic -> session -> interaction hierarchy and diagnostics."""

from __future__ import annotations

from datetime import datetime, timezone

from agent_roi.core.config import Config
from agent_roi.core.models import Interaction, Tool
from agent_roi.core.service import Service
from agent_roi.storage import Database


def _itx(id_, session, tool=Tool.CLAUDE_CODE, model="claude-opus-4-8", topic="auth", ts=None):
    return Interaction(
        id=id_,
        tool=tool,
        session_id=session,
        timestamp=ts or datetime(2026, 5, 4, tzinfo=timezone.utc),
        model=model,
        output_tokens=1000,
        project="repo",
        topic=topic,
    )


def test_sessions_aggregate_tools_and_models(tmp_path):
    db = Database(tmp_path / "t.db")
    db.upsert_many(
        [
            _itx("a", "s1", tool=Tool.CLAUDE_CODE, model="claude-opus-4-8"),
            _itx("b", "s1", tool=Tool.COPILOT, model="claude-haiku-4-5"),
            _itx("c", "s2", topic="other"),
        ]
    )
    sessions = {s.session_id: s for s in db.sessions()}
    assert set(sessions) == {"s1", "s2"}
    s1 = sessions["s1"]
    assert s1.interactions == 2
    assert s1.tools == ["claude_code", "copilot"]
    assert set(s1.models) == {"claude-opus-4-8", "claude-haiku-4-5"}
    assert s1.topic == "auth"


def test_sessions_filter_by_topic(tmp_path):
    db = Database(tmp_path / "t.db")
    db.upsert_many([_itx("a", "s1", topic="auth"), _itx("b", "s2", topic="ci")])
    auth = db.sessions(topic="auth")
    assert [s.session_id for s in auth] == ["s1"]


def test_session_detail_lists_interactions(tmp_path):
    db = Database(tmp_path / "t.db")
    db.upsert_many([_itx("a", "s1"), _itx("b", "s1")])
    detail = db.session_detail("s1")
    assert detail is not None
    assert detail.session.session_id == "s1"
    assert len(detail.interactions) == 2
    assert db.session_detail("missing") is None


def test_sources_reports_collectors(tmp_path):
    # No real logs are read here (collectors just report availability/paths), so
    # this exercises the diagnostics plumbing deterministically.
    service = Service(Config(db_path=tmp_path / "t.db"))
    statuses = {s.name for s in service.sources()}
    assert {"claude_code", "codex", "copilot"} <= statuses
