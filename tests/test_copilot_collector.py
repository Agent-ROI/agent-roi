"""Tests for the Copilot collector against a realistic chat-session fixture."""

from __future__ import annotations

import json

from agent_roi.collectors.copilot import CopilotCollector
from agent_roi.core.models import Tool


def _write_session(user_root, ws_id, session_id, payload):
    sessions = user_root / "workspaceStorage" / ws_id / "chatSessions"
    sessions.mkdir(parents=True, exist_ok=True)
    (sessions / f"{session_id}.json").write_text(json.dumps(payload), encoding="utf-8")


def test_parses_request_and_estimates_tokens(tmp_path):
    payload = {
        "version": 3,
        "requests": [
            {
                "requestId": "req-1",
                "timestamp": 1772256970068,
                "modelId": "copilot/claude-opus-4.6",
                "message": {"text": "how do I add auth middleware"},
                "response": [{"value": "Add a middleware that checks the session token..."}],
                "result": {},
            }
        ],
    }
    _write_session(tmp_path, "ws1", "sess-1", payload)

    collector = CopilotCollector(roots=[tmp_path])
    interactions = list(collector.collect())

    assert len(interactions) == 1
    itx = interactions[0]
    assert itx.id == "copilot:req-1"
    assert itx.tool is Tool.COPILOT
    # Vendor prefix stripped, dots normalized to dashes for pricing lookup.
    assert itx.model == "claude-opus-4-6"
    assert itx.estimated is True
    assert itx.input_tokens > 0
    assert itx.output_tokens > 0
    assert itx.summary.startswith("how do I add auth")


def test_unavailable_without_workspace_storage(tmp_path):
    assert CopilotCollector(roots=[tmp_path]).is_available() is False


def test_skips_records_without_request_id(tmp_path):
    payload = {"requests": [{"modelId": "copilot/x", "message": {"text": "hi"}}]}
    _write_session(tmp_path, "ws1", "sess-1", payload)
    assert list(CopilotCollector(roots=[tmp_path]).collect()) == []
