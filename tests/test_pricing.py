"""Tests for token cost computation."""

from __future__ import annotations

from datetime import datetime

from agent_roi.core.models import Interaction, Tool
from agent_roi.core.pricing import cost_of, price_for


def test_price_prefix_match():
    # Exact and prefix/version variants both resolve.
    assert price_for("claude-opus-4-8").output == 75.0
    assert price_for("claude-opus-4-8-20260101").output == 75.0


def test_unknown_model_is_free_not_error():
    assert price_for("some-future-model").input == 0.0


def test_cost_of_interaction():
    itx = Interaction(
        id="x",
        tool=Tool.CLAUDE_CODE,
        session_id="s",
        timestamp=datetime(2026, 5, 4),
        model="claude-haiku-4-5",
        input_tokens=1_000_000,
        output_tokens=1_000_000,
    )
    # 0.8 (input) + 4.0 (output) per 1M each.
    assert cost_of(itx) == 0.8 + 4.0
