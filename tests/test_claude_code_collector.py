"""Tests for the Claude Code collector against a realistic JSONL fixture."""

from __future__ import annotations

import json

from agent_roi.collectors.claude_code import ClaudeCodeCollector
from agent_roi.core.models import Tool


def _write_session(root, session_id, records):
    project = root / "-Users-test"
    project.mkdir(parents=True, exist_ok=True)
    path = project / f"{session_id}.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")
    return path


def test_parses_usage_and_ignores_non_assistant(tmp_path):
    records = [
        # A config-only record with no message -> ignored.
        {"type": "system", "sessionId": "s1"},
        # An assistant turn with a real usage block -> parsed.
        {
            "type": "assistant",
            "timestamp": "2026-05-04T06:50:08.560Z",
            "message": {
                "id": "msg_abc",
                "model": "claude-opus-4-8",
                "content": [{"type": "text", "text": "fixing the auth bug"}],
                "usage": {
                    "input_tokens": 6,
                    "output_tokens": 292,
                    "cache_read_input_tokens": 14896,
                    "cache_creation_input_tokens": 10039,
                },
            },
        },
    ]
    _write_session(tmp_path, "s1", records)

    collector = ClaudeCodeCollector(roots=[tmp_path])
    interactions = list(collector.collect())

    assert len(interactions) == 1
    itx = interactions[0]
    assert itx.id == "msg_abc"
    assert itx.tool is Tool.CLAUDE_CODE
    assert itx.model == "claude-opus-4-8"
    assert itx.input_tokens == 6
    assert itx.output_tokens == 292
    assert itx.cache_read_tokens == 14896
    assert itx.cache_write_tokens == 10039
    assert itx.total_tokens == 6 + 292 + 14896 + 10039
    assert itx.summary == "fixing the auth bug"


def test_unavailable_when_no_roots():
    assert ClaudeCodeCollector(roots=[]).is_available() is False


def test_skips_malformed_lines(tmp_path):
    path = _write_session(tmp_path, "s2", [{"type": "system"}])
    path.write_text(path.read_text() + "\nnot json\n", encoding="utf-8")
    # Should not raise.
    assert list(ClaudeCodeCollector(roots=[tmp_path]).collect()) == []
