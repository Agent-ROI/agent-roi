"""Estimate *active* development time from interaction timestamps.

The whole point of "Agent-ROI" is to weigh cost against value, and the value
people care about most is their *time*: "this work took me 3 hours and $40 — was
it worth it?". Wall-clock span (last timestamp minus first) is useless for that,
because sessions are routinely left open overnight: in real data a naive span
inflates total time by ~48x (1,667h vs ~35h of genuine work).

So we measure active time by summing the gaps *between* consecutive turns, but
dropping any gap longer than an idle threshold — those are the user stepping
away, not work. An agent firing turn after turn (median gap ~8s) is counted; a
gap of hours is not.

Idle threshold: data-driven, no hard-coded time constants
---------------------------------------------------------
People work at different rhythms (a heavy agent user's gaps are seconds; someone
who pauses to think has minutes), so the threshold must come from *each user's
own* gap distribution, not a fixed "5 minutes". We combine two purely
mathematical, dependency-free estimators and take the looser of the two:

- **Otsu natural break** on ``log10(gap)``: the split that maximises
  between-class variance — i.e. the valley between the "agent working" cluster
  and the "human stepped away" cluster. Fully shape-driven.
- **90th percentile** of gaps: a robust upper bound on "normal" gaps.

``max(otsu, p90)`` is used because, when gaps are extremely concentrated (a
tight burst of agent turns), Otsu hugs that peak and would clip legitimate
think-time pauses; p90 then rescues a sensible cutoff. Neither carries an
absolute hard-coded time — both scale with the user's data. The only constants
are algorithmic (histogram bins, a small-sample fallback), not assumptions about
how long "a pause" is.

Everything here is pure arithmetic: no model weights, no numpy, consistent with
the project's model-free, offline design.
"""

from __future__ import annotations

import math
from datetime import datetime

# Fallback when there are too few gaps for a distribution to mean anything.
# This is a small-sample guard, not an assumption about work rhythm.
DEFAULT_IDLE_SECONDS = 300.0  # 5 minutes
# Below this many gaps, percentile/Otsu are noise — fall back to the default.
_MIN_GAPS_FOR_FIT = 20
# Otsu histogram resolution (an algorithmic parameter, not a time constant).
_OTSU_BINS = 256


def percentile(values: list[float], q: float) -> float:
    """Linear-interpolated ``q``-th percentile (q in [0, 1]) of ``values``.

    Small, dependency-free stand-in for ``numpy.percentile`` so the engine stays
    model-free. ``values`` need not be sorted. Empty input returns 0.0.
    """
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = q * (len(ordered) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    frac = pos - lo
    return ordered[lo] * (1 - frac) + ordered[hi] * frac


def otsu_threshold_log(values: list[float]) -> float:
    """Otsu's natural-break split of positive ``values``, computed in log space.

    Otsu's method picks the threshold that minimises within-class variance (==
    maximises between-class variance) of a two-class split — classically used
    for image binarisation, here to separate "agent working" gaps from "stepped
    away" gaps. Working in ``log10`` handles the heavy-tailed, multi-scale gap
    distribution (seconds to hours). Returns the threshold in the original unit
    (seconds). Empty input returns 0.0.
    """
    logs = sorted(math.log10(v) for v in values if v > 0)
    if not logs:
        return 0.0
    lo, hi = logs[0], logs[-1]
    if hi <= lo:
        return values[0]
    width = (hi - lo) / _OTSU_BINS
    hist = [0] * _OTSU_BINS
    for v in logs:
        hist[min(_OTSU_BINS - 1, int((v - lo) / width))] += 1

    total = len(logs)
    sum_all = sum(i * h for i, h in enumerate(hist))
    weight_bg = 0
    sum_bg = 0.0
    best_variance = -1.0
    best_bin = 0
    for i, h in enumerate(hist):
        weight_bg += h
        if weight_bg == 0:
            continue
        weight_fg = total - weight_bg
        if weight_fg == 0:
            break
        sum_bg += i * h
        mean_bg = sum_bg / weight_bg
        mean_fg = (sum_all - sum_bg) / weight_fg
        variance_between = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
        if variance_between > best_variance:
            best_variance, best_bin = variance_between, i
    return 10 ** (lo + (best_bin + 0.5) * width)


def adaptive_idle_threshold(all_gaps_seconds: list[float]) -> float:
    """Derive the idle cutoff from the user's own gap distribution.

    Returns ``max(Otsu natural break, 90th percentile)`` of the gaps — see the
    module docstring for why the two are combined. Falls back to
    :data:`DEFAULT_IDLE_SECONDS` when there are too few gaps to fit.
    """
    if len(all_gaps_seconds) < _MIN_GAPS_FOR_FIT:
        return DEFAULT_IDLE_SECONDS
    otsu = otsu_threshold_log(all_gaps_seconds)
    p90 = percentile(all_gaps_seconds, 0.90)
    return max(otsu, p90)


def session_gaps_seconds(timestamps: list[datetime]) -> list[float]:
    """Gaps (in seconds) between consecutive turns of one session.

    Sorts defensively; a session with fewer than two turns has no gaps.
    Non-positive gaps (clock skew, identical stamps) are dropped.
    """
    if len(timestamps) < 2:
        return []
    ordered = sorted(timestamps)
    gaps = [
        (ordered[i] - ordered[i - 1]).total_seconds()
        for i in range(1, len(ordered))
    ]
    return [g for g in gaps if g > 0]


def active_seconds(timestamps: list[datetime], idle_threshold: float) -> float:
    """Active time of one session: sum of gaps that are under the idle cutoff.

    A single-turn session has no gaps and therefore 0 active seconds — which is
    correct: one request/response isn't measurable "time spent".
    """
    return sum(g for g in session_gaps_seconds(timestamps) if g <= idle_threshold)
