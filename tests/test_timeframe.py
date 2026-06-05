"""Tests for time-window parsing."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agent_roi.core.timeframe import parse_since, parse_until

_NOW = datetime(2026, 5, 4, 12, 0, tzinfo=timezone.utc)


def test_empty_is_none():
    assert parse_since("") is None


def test_shorthand_days():
    assert parse_since("7d", now=_NOW) == _NOW - timedelta(days=7)


def test_shorthand_hours():
    assert parse_since("24h", now=_NOW) == _NOW - timedelta(hours=24)


def test_today_truncates_to_midnight():
    assert parse_since("today", now=_NOW) == _NOW.replace(hour=0, minute=0)


def test_iso_date():
    assert parse_since("2026-01-15") == datetime(2026, 1, 15)


def test_invalid_raises():
    with pytest.raises(ValueError):
        parse_since("nonsense")


def test_until_empty_is_none():
    assert parse_until("") is None


def test_until_date_is_exclusive_next_day():
    assert parse_until("2026-06-05") == datetime(2026, 6, 6)


def test_until_today_is_end_of_day():
    end = parse_until("today", now=_NOW)
    assert end == datetime(2026, 5, 5, 0, 0, tzinfo=timezone.utc)
