"""Tests for token cost computation."""

from __future__ import annotations

from datetime import datetime

import pytest

from agent_roi.core import pricing as pricing_mod
from agent_roi.core.models import Interaction, Tool
from agent_roi.core.pricing import (
    _EPOCH_ZERO,
    PriceEpoch,
    _ModelHistory,
    all_prices,
    cost_of,
    price_for,
)


def _itx(model: str, tool: Tool, *, input_tokens: int = 0, output_tokens: int = 0) -> Interaction:
    return Interaction(
        id="x",
        tool=tool,
        session_id="s",
        timestamp=datetime(2026, 6, 1),
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


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


def test_generic_price_applies_to_any_provider():
    # No provider-specific override for opus-4-6 -> every tool gets the list price.
    cc = _itx("claude-opus-4-6", Tool.CLAUDE_CODE, input_tokens=1_000_000)
    anti = _itx("claude-opus-4-6", Tool.ANTIGRAVITY, input_tokens=1_000_000)
    assert cost_of(cc) == cost_of(anti) == 15.0


def test_provider_override_beats_generic(monkeypatch):
    # A tool that resells the model at half the list price.
    histories = dict(pricing_mod._HISTORIES)
    histories[("claude-opus-4-6", "antigravity")] = _ModelHistory(
        [PriceEpoch(effective_from=_EPOCH_ZERO, input=7.5, output=37.5)]
    )
    monkeypatch.setattr(pricing_mod, "_HISTORIES", histories)

    # Provider-specific price wins, and prefix-matches the thinking variant.
    anti = _itx("claude-opus-4-6-thinking", Tool.ANTIGRAVITY, input_tokens=1_000_000)
    assert cost_of(anti) == 7.5
    # Other tools still fall back to the generic list price.
    cc = _itx("claude-opus-4-6", Tool.CLAUDE_CODE, input_tokens=1_000_000)
    assert cost_of(cc) == 15.0


def test_size_tiered_pricing():
    # gemini-2.5-pro: <=200k input uses tier 1, above uses tier 2.
    small = _itx("gemini-2.5-pro", Tool.GEMINI, input_tokens=100_000, output_tokens=1_000_000)
    big = _itx("gemini-2.5-pro", Tool.GEMINI, input_tokens=300_000, output_tokens=1_000_000)
    # Tier 1 output is $10/M, tier 2 is $15/M; input cost differs too.
    assert cost_of(small) == pytest.approx(0.1 * 1.25 + 10.0)
    assert cost_of(big) == pytest.approx(0.3 * 2.50 + 15.0)


def test_all_prices_exposes_provider_and_tiered_flag():
    rows = all_prices()
    opus = next(r for r in rows if r.model == "claude-opus-4-6")
    assert opus.tiered is False
    assert opus.tier_label == ""
    # Generic prices report no provider.
    assert opus.provider is None


def test_all_prices_expands_tiers_into_rows():
    # A size-tiered model emits one row per band, each labelled.
    pro = [r for r in all_prices() if r.model == "gemini-2.5-pro"]
    assert len(pro) == 2
    assert all(r.tiered for r in pro)
    labels = {r.tier_label for r in pro}
    assert labels == {"≤200k", ">200k"}
    # The bands carry their own distinct prices.
    by_label = {r.tier_label: r for r in pro}
    assert by_label["≤200k"].input == 1.25
    assert by_label[">200k"].input == 2.50
