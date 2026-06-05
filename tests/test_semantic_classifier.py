"""Tests for the model-free semantic topic classifier."""

from __future__ import annotations

from datetime import datetime, timezone

from agent_roi.classify.base import UNCATEGORIZED, SessionDoc
from agent_roi.classify.semantic import SemanticClassifier
from agent_roi.core.config import Config
from agent_roi.core.models import Interaction, Tool
from agent_roi.core.service import Service


def _doc(session_id: str, summary: str, project: str = "repo") -> SessionDoc:
    return SessionDoc(session_id=session_id, project=project, summary=summary)


def test_similar_sessions_share_a_topic():
    """Sessions about the same kind of work get grouped under one topic."""
    docs = [
        _doc("a", "refactor the authentication login flow and jwt session tokens"),
        _doc("b", "authentication jwt token refresh and login session handling"),
        _doc("c", "build the react dashboard pricing chart and table layout"),
    ]
    labels = SemanticClassifier().label_sessions(docs)

    # a and b are both auth work -> same topic; c is different.
    assert labels["a"] == labels["b"]
    assert labels["a"] != labels["c"]
    assert labels["a"] != UNCATEGORIZED


def test_label_uses_distinctive_terms():
    docs = [
        _doc("a", "authentication jwt session login token"),
        _doc("b", "authentication jwt session login token refresh"),
    ]
    labels = SemanticClassifier().label_sessions(docs)
    assert "jwt" in labels["a"] or "authentication" in labels["a"]


def test_empty_summary_is_uncategorized():
    labels = SemanticClassifier().label_sessions([_doc("a", "   ")])
    assert labels["a"] == UNCATEGORIZED


def test_empty_input_returns_empty():
    assert SemanticClassifier().label_sessions([]) == {}


def test_threshold_controls_grouping():
    docs = [
        _doc("a", "database migration schema sqlite index"),
        _doc("b", "database migration schema postgres index"),
    ]
    # A very high threshold keeps them apart; a low one merges them.
    strict = SemanticClassifier(similarity_threshold=0.99).label_sessions(docs)
    loose = SemanticClassifier(similarity_threshold=0.05).label_sessions(docs)
    assert strict["a"] != strict["b"]
    assert loose["a"] == loose["b"]


def _itx(id_: str, session: str, summary: str, ts=None) -> Interaction:
    return Interaction(
        id=id_,
        tool=Tool.CLAUDE_CODE,
        session_id=session,
        timestamp=ts or datetime(2026, 5, 4, tzinfo=timezone.utc),
        model="claude-haiku-4-5",
        output_tokens=1000,
        summary=summary,
    )


def test_service_classify_groups_sessions(tmp_path):
    service = Service(Config(db_path=tmp_path / "t.db"))
    service.db.upsert_many(
        [
            _itx("1", "s1", "authentication login jwt session refactor"),
            _itx("2", "s2", "authentication jwt login session token work"),
            _itx("3", "s3", "react dashboard pricing chart table ui"),
        ]
    )

    updated = service.classify()
    assert updated == 3

    # All rows are now classified, so nothing remains unclassified.
    assert service.db.unclassified_sessions() == []
    rollups = {r.key: r for r in service.db.rollup("topic")}
    # s1 and s2 collapsed into one auth topic, s3 into its own.
    assert len(rollups) == 2
