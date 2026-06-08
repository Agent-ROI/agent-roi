"""Tests for activity persistence and aggregation (tools / MCP / files)."""

from __future__ import annotations

from datetime import datetime, timezone

from agent_roi.core.models import Activity, Interaction, Tool
from agent_roi.storage import Database


def test_activity_report_sums_result_tokens(tmp_path):
    db = Database(tmp_path / "t.db")
    db.upsert_many(
        [
            _itx(
                "a",
                [
                    Activity(kind="Read", target="/a", result_tokens=100),
                    Activity(kind="Read", target="/b", result_tokens=50),
                    Activity(kind="Bash", result_tokens=10),
                ],
            )
        ]
    )
    by_tool = {c.label: c for c in db.activity_report().by_tool}
    assert by_tool["Read"].count == 2
    assert by_tool["Read"].result_tokens == 150
    assert by_tool["Bash"].result_tokens == 10


def _itx(id_, activities, ts=None):
    return Interaction(
        id=id_,
        tool=Tool.CLAUDE_CODE,
        session_id="s",
        timestamp=ts or datetime(2026, 5, 4, tzinfo=timezone.utc),
        model="claude-opus-4-8",
        output_tokens=10,
        activities=activities,
    )


def test_activity_report_counts_tools_mcp_files(tmp_path):
    db = Database(tmp_path / "t.db")
    db.upsert_many(
        [
            _itx(
                "a",
                [
                    Activity(kind="Bash"),
                    Activity(kind="Bash"),
                    Activity(kind="Edit", target="/repo/app.py"),
                    Activity(kind="mcp__github__create", mcp_server="github"),
                ],
            ),
            _itx("b", [Activity(kind="Edit", target="/repo/app.py")]),
        ]
    )

    report = db.activity_report()
    assert report.total_actions == 5
    tools = {c.label: c.count for c in report.by_tool}
    assert tools == {"Bash": 2, "Edit": 2, "mcp__github__create": 1}
    assert [(c.label, c.count) for c in report.by_mcp] == [("github", 1)]
    # The same file touched twice ranks first.
    assert report.top_files[0].label == "/repo/app.py"
    assert report.top_files[0].count == 2


def test_activity_reingest_is_idempotent(tmp_path):
    db = Database(tmp_path / "t.db")
    itx = _itx("a", [Activity(kind="Bash"), Activity(kind="Read")])
    db.upsert_many([itx])
    db.upsert_many([itx])  # re-ingest the same interaction
    # Activities are replaced, not doubled.
    assert db.activity_report().total_actions == 2


def test_activity_report_empty(tmp_path):
    db = Database(tmp_path / "t.db")
    report = db.activity_report()
    assert report.total_actions == 0
    assert report.by_tool == []
    assert report.by_mcp == []
    assert report.top_files == []
