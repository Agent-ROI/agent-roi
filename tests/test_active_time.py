"""Tests for the active-development-time engine."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from agent_roi.core.active_time import (
    DEFAULT_IDLE_SECONDS,
    active_seconds,
    adaptive_idle_threshold,
    otsu_threshold_log,
    percentile,
    session_gaps_seconds,
)

BASE = datetime(2026, 5, 1, 9, 0, tzinfo=timezone.utc)


def _stamps(offsets_seconds: list[float]) -> list[datetime]:
    return [BASE + timedelta(seconds=s) for s in offsets_seconds]


def test_percentile_interpolates():
    assert percentile([], 0.5) == 0.0
    assert percentile([42], 0.9) == 42
    # 0,10,20,30,40 → p50 is the midpoint 20.
    assert percentile([0, 10, 20, 30, 40], 0.5) == 20
    assert percentile([0, 100], 0.9) == 90


def test_session_gaps_drops_nonpositive_and_unsorts():
    # Out of order, with a duplicate stamp (zero gap) that must be dropped.
    stamps = _stamps([0, 30, 30, 10])
    gaps = session_gaps_seconds(stamps)
    assert gaps == [10, 20]  # sorted: 0,10,30,30 → 10,20,0(drop)


def test_single_turn_has_no_active_time():
    assert active_seconds(_stamps([0]), idle_threshold=300) == 0.0
    assert session_gaps_seconds(_stamps([0])) == []


def test_active_seconds_excludes_idle_gaps():
    # 10s, 20s of work, then a 2h break, then 15s more.
    stamps = _stamps([0, 10, 30, 30 + 7200, 30 + 7200 + 15])
    # Threshold 300s: the 7200s break is dropped, the rest counted.
    assert active_seconds(stamps, idle_threshold=300) == 10 + 20 + 15


def test_few_gaps_fall_back_to_default():
    assert adaptive_idle_threshold([5, 10, 15]) == DEFAULT_IDLE_SECONDS


def test_adaptive_threshold_separates_work_from_idle():
    # A realistic bimodal distribution: a dense cluster of short "working" gaps
    # plus a sparse tail of long "stepped away" gaps. The threshold should land
    # between the two clusters, not inside the working peak nor out in the tail.
    work = [5, 6, 7, 8, 9, 10, 12, 15, 20, 30] * 8  # 80 short gaps
    idle = [3600, 5400, 7200, 9000]  # a handful of long breaks
    thr = adaptive_idle_threshold(work + idle)
    assert max(work) < thr < min(idle)


def test_adaptive_threshold_uses_p90_when_otsu_hugs_peak():
    # Extremely concentrated gaps make raw Otsu cling to the peak; max(otsu,p90)
    # must still admit normal think-time pauses rather than clipping them.
    gaps = [8.0] * 200 + [60, 90, 120, 180, 240]  # tight burst + a few pauses
    thr = adaptive_idle_threshold(gaps)
    p90 = percentile(gaps, 0.90)
    assert thr >= p90
    assert thr >= otsu_threshold_log(gaps)


def test_otsu_empty_is_zero():
    assert otsu_threshold_log([]) == 0.0
