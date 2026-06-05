"""Per-model token pricing, loaded from pricing.toml alongside this file.

Each model can have multiple price epochs (one TOML section per epoch). When
a model's price changes, a new epoch is added with a "from" date; historical
interactions are priced with whichever epoch was active at their timestamp.
Unknown models fall back to $0 so usage is still tracked (cost shows as 0).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import date, timezone
from pathlib import Path
from typing import Any

from agent_roi.core.models import Interaction, ModelPricing

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

_TOML_PATH = Path(__file__).parent / "pricing.toml"
_EPOCH_ZERO = date(1970, 1, 1)


@dataclass(frozen=True)
class PriceEpoch:
    effective_from: date
    input: float
    output: float
    cache_read: float = 0.0
    cache_write: float = 0.0


@dataclass
class _ModelHistory:
    epochs: list[PriceEpoch] = field(default_factory=list)

    def price_at(self, on: date) -> PriceEpoch | None:
        """Return the epoch active on the given date (latest epoch with from <= on)."""
        result: PriceEpoch | None = None
        for epoch in self.epochs:
            if epoch.effective_from <= on:
                result = epoch
            else:
                break
        return result


def _load() -> dict[str, _ModelHistory]:
    raw: dict[str, Any] = tomllib.loads(_TOML_PATH.read_text(encoding="utf-8"))
    histories: dict[str, _ModelHistory] = {}
    for model, value in raw.items():
        if isinstance(value, dict):
            entries: list[dict[str, Any]] = [value]
        elif isinstance(value, list):
            entries = value
        else:
            continue

        history = _ModelHistory()
        for entry in entries:
            from_str = entry.get("from")
            effective = date.fromisoformat(from_str) if from_str else _EPOCH_ZERO
            history.epochs.append(
                PriceEpoch(
                    effective_from=effective,
                    input=float(entry.get("input", 0.0)),
                    output=float(entry.get("output", 0.0)),
                    cache_read=float(entry.get("cache_read", 0.0)),
                    cache_write=float(entry.get("cache_write", 0.0)),
                )
            )
        history.epochs.sort(key=lambda e: e.effective_from)
        histories[model] = history
    return histories


_HISTORIES: dict[str, _ModelHistory] = _load()
_UNKNOWN_EPOCH = PriceEpoch(effective_from=_EPOCH_ZERO, input=0.0, output=0.0)


def price_for(model: str, on: date | None = None) -> PriceEpoch:
    """Return the price epoch for *model* active on *on* (default: today).

    Resolution order:
    1. Exact match on model name.
    2. Longest known prefix match (e.g. "claude-sonnet-4-6-20251231" -> "claude-sonnet-4-6").
    3. $0 fallback so usage is always recorded.
    """
    if on is None:
        on = date.today()

    history = _HISTORIES.get(model)
    if history is None:
        candidates = [name for name in _HISTORIES if model.startswith(name)]
        if candidates:
            history = _HISTORIES[max(candidates, key=len)]

    if history is not None:
        epoch = history.price_at(on)
        if epoch is not None:
            return epoch

    return _UNKNOWN_EPOCH


def all_prices() -> list[ModelPricing]:
    """Return all price epochs sorted by model name then effective date.

    Each epoch is a separate row so the full history is visible.
    """
    rows: list[ModelPricing] = []
    for model in sorted(_HISTORIES):
        for epoch in _HISTORIES[model].epochs:
            rows.append(
                ModelPricing(
                    model=model,
                    effective_from=epoch.effective_from.isoformat(),
                    input=epoch.input,
                    output=epoch.output,
                    cache_read=epoch.cache_read,
                    cache_write=epoch.cache_write,
                )
            )
    return rows


def cost_of(interaction: Interaction) -> float:
    """Compute the USD cost of a single interaction using the price active at its timestamp."""
    ts = interaction.timestamp
    on = ts.astimezone(timezone.utc).date() if ts.tzinfo is not None else ts.date()
    p = price_for(interaction.model, on)
    return (
        interaction.input_tokens * p.input
        + interaction.output_tokens * p.output
        + interaction.cache_read_tokens * p.cache_read
        + interaction.cache_write_tokens * p.cache_write
    ) / 1_000_000
