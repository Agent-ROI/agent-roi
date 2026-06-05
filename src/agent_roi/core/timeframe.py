"""Parse user-supplied time-window strings into datetimes.

Accepts:
- ISO dates: ``2026-05-01``
- ISO datetimes: ``2026-05-01T12:00``
- Shorthands: ``today``, ``7d`` (last 7 days), ``24h`` (last 24 hours),
  ``30m`` (last 30 minutes), ``8w`` (last 8 weeks).

Returns ``None`` for an empty string (meaning "no lower bound").

``parse_until`` is the upper bound (exclusive): an ISO date includes that whole
calendar day; ``today`` means through end of today.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

_SHORTHAND = re.compile(r"^(\d+)\s*([mhdw])$", re.IGNORECASE)
_UNIT_TO_DELTA = {
    "m": lambda n: timedelta(minutes=n),
    "h": lambda n: timedelta(hours=n),
    "d": lambda n: timedelta(days=n),
    "w": lambda n: timedelta(weeks=n),
}


def parse_since(value: str, *, now: datetime | None = None) -> datetime | None:
    """Parse a window-start string. Raises ``ValueError`` on bad input."""
    value = value.strip()
    if not value:
        return None
    now = now or datetime.now(tz=timezone.utc)

    if value.lower() == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)

    match = _SHORTHAND.match(value)
    if match:
        amount = int(match.group(1))
        unit = match.group(2).lower()
        return now - _UNIT_TO_DELTA[unit](amount)

    # Fall back to ISO date / datetime.
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            f"Could not parse time '{value}'. Use a date (YYYY-MM-DD) or 7d/24h/today."
        ) from exc


def parse_until(value: str, *, now: datetime | None = None) -> datetime | None:
    """Parse a window-end string (exclusive). Raises ``ValueError`` on bad input."""
    value = value.strip()
    if not value:
        return None
    now = now or datetime.now(tz=timezone.utc)

    if value.lower() == "today":
        start_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return start_today + timedelta(days=1)

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            f"Could not parse end time '{value}'. Use a date (YYYY-MM-DD) or today."
        ) from exc

    # Bare YYYY-MM-DD → include the full calendar day.
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        d = date.fromisoformat(value)
        return datetime(d.year, d.month, d.day) + timedelta(days=1)
    return parsed
