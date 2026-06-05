"""Tests for the offline token estimator."""

from __future__ import annotations

from agent_roi.core.tokens import estimate_tokens


def test_empty_is_zero():
    assert estimate_tokens("") == 0


def test_estimate_is_positive_and_scales():
    short = estimate_tokens("hello world")
    long = estimate_tokens("hello world " * 100)
    assert short >= 1
    assert long > short


def test_estimate_in_reasonable_range():
    # ~20 English words should land in a sane token range, not orders of
    # magnitude off (sanity check for the heuristic, not exact BPE).
    text = "the quick brown fox jumps over the lazy dog " * 2
    est = estimate_tokens(text)
    assert 10 < est < 60
