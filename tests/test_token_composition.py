"""Tests for token-composition math (overhead / cached / work) and Rollup.sum."""

from __future__ import annotations

from agent_roi.core.models import Rollup, TokenComposition


def _rollup(**kw: object) -> Rollup:
    base: dict[str, object] = {
        "key": "k",
        "interactions": 1,
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_write_tokens": 0,
        "cost_usd": 0.0,
    }
    base.update(kw)
    return Rollup(**base)  # type: ignore[arg-type]


def test_composition_splits_into_three_buckets():
    r = _rollup(
        input_tokens=100,
        output_tokens=50,
        cache_read_tokens=600,
        cache_write_tokens=250,
    )
    c = TokenComposition.from_rollup(r)
    # overhead = cache_write, cached = cache_read, work = input + output
    assert c.overhead == 250
    assert c.cached == 600
    assert c.work == 150
    # Percentages are of the three-bucket total (1000), summing to ~100.
    assert c.overhead_pct == 25.0
    assert c.cached_pct == 60.0
    assert c.work_pct == 15.0


def test_composition_zero_total_is_safe():
    c = TokenComposition.from_rollup(_rollup())
    assert (c.overhead, c.cached, c.work) == (0, 0, 0)
    assert (c.overhead_pct, c.cached_pct, c.work_pct) == (0.0, 0.0, 0.0)


def test_composition_estimated_passes_through():
    # Copilot-style: no cache split, everything is uncached work, estimated.
    r = _rollup(input_tokens=80, output_tokens=20, estimated=True)
    c = TokenComposition.from_rollup(r)
    assert c.estimated is True
    assert c.work == 100
    assert c.work_pct == 100.0
    assert c.overhead == 0 and c.cached == 0


def test_rollup_sum_adds_fields_and_token_weights_estimated():
    real = _rollup(input_tokens=900, cost_usd=1.0)  # 900 real tokens
    est = _rollup(input_tokens=100, cost_usd=0.1, estimated=True)  # 100 estimated
    total = Rollup.sum("all", [real, est])
    assert total.key == "all"
    assert total.input_tokens == 1000
    assert total.cost_usd == 1.1
    # Estimated tokens (100) are < half of total (1000), so the sum is exact.
    assert total.estimated is False


def test_rollup_sum_flags_estimated_when_majority():
    real = _rollup(input_tokens=100)
    est = _rollup(input_tokens=100, estimated=True)
    # A tie (100 vs 100) leans estimated.
    assert Rollup.sum("all", [real, est]).estimated is True
