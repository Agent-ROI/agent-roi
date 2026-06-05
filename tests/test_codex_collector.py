"""Tests for the Codex collector against a realistic rollout JSONL fixture."""

from __future__ import annotations

import json

from agent_roi.collectors.codex import CodexCollector
from agent_roi.core.models import Tool


def _write_rollout(root, records):
    day = root / "2026" / "06" / "05"
    day.mkdir(parents=True, exist_ok=True)
    path = day / "rollout-2026-06-05T10-25-09-019e9599-abc.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")
    return path


def test_parses_token_count_with_model_and_text(tmp_path):
    records = [
        {"type": "session_meta", "payload": {"id": "019e9599", "cwd": "/x"}},
        {"type": "turn_context", "payload": {"model": "gpt-5.5", "turn_id": "t1"}},
        {
            "type": "event_msg",
            "timestamp": "2026-06-05T02:25:13.580Z",
            "payload": {"type": "user_message", "message": "add a codex collector"},
        },
        {
            "type": "event_msg",
            "timestamp": "2026-06-05T02:25:20.000Z",
            "payload": {
                "type": "token_count",
                "info": {
                    "last_token_usage": {
                        "input_tokens": 11698,
                        "cached_input_tokens": 1920,
                        "output_tokens": 14,
                        "reasoning_output_tokens": 6,
                    },
                    "total_token_usage": {"input_tokens": 99999},
                },
            },
        },
    ]
    _write_rollout(tmp_path, records)

    interactions = list(CodexCollector(roots=[tmp_path]).collect())
    assert len(interactions) == 1
    itx = interactions[0]
    assert itx.tool is Tool.CODEX
    # Model picked up from turn_context, dots normalized for pricing.
    assert itx.model == "gpt-5-5"
    assert itx.input_tokens == 11698
    assert itx.cache_read_tokens == 1920
    # output = output_tokens + reasoning_output_tokens
    assert itx.output_tokens == 14 + 6
    # Uses last_token_usage (the per-turn delta), not the running total.
    assert itx.input_tokens != 99999
    assert itx.summary == "add a codex collector"
    assert itx.estimated is False


def test_unavailable_when_no_roots():
    assert CodexCollector(roots=[]).is_available() is False


def test_skips_records_without_usage(tmp_path):
    _write_rollout(tmp_path, [{"type": "event_msg", "payload": {"type": "task_started"}}])
    assert list(CodexCollector(roots=[tmp_path]).collect()) == []
