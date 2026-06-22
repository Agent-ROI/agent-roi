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
class PriceTier:
    """One price band for tokens up to a prompt-size threshold.

    Some providers price the same model differently by context length (e.g.
    Gemini charges more once the prompt exceeds ~200k tokens). ``up_to`` is the
    inclusive upper bound on *input* tokens at which this tier applies; the
    final tier uses ``None`` to mean "and above".
    """

    up_to: int | None
    input: float
    output: float
    cache_read: float = 0.0
    cache_write: float = 0.0


@dataclass(frozen=True)
class PriceEpoch:
    effective_from: date
    input: float
    output: float
    cache_read: float = 0.0
    cache_write: float = 0.0
    # When set, prices vary by prompt size; ``input``/``output``/… above are the
    # base (smallest) tier, kept populated so simple callers still work.
    tiers: tuple[PriceTier, ...] = ()

    def rate_for(self, input_tokens: int) -> PriceTier:
        """Return the tier whose band covers a prompt of ``input_tokens``.

        Falls back to this epoch's flat rates when no tiers are defined.
        """
        if not self.tiers:
            return PriceTier(
                up_to=None,
                input=self.input,
                output=self.output,
                cache_read=self.cache_read,
                cache_write=self.cache_write,
            )
        for tier in self.tiers:
            if tier.up_to is None or input_tokens <= tier.up_to:
                return tier
        return self.tiers[-1]


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


def _tiers_from(entry: dict[str, Any]) -> tuple[PriceTier, ...]:
    raw = entry.get("tiers")
    if not isinstance(raw, list):
        return ()
    tiers: list[PriceTier] = []
    for t in raw:
        if not isinstance(t, dict):
            continue
        up_to = t.get("up_to")
        tiers.append(
            PriceTier(
                up_to=int(up_to) if up_to is not None else None,
                input=float(t.get("input", 0.0)),
                output=float(t.get("output", 0.0)),
                cache_read=float(t.get("cache_read", 0.0)),
                cache_write=float(t.get("cache_write", 0.0)),
            )
        )
    # A None bound sorts last; otherwise ascend by threshold.
    tiers.sort(key=lambda t: (t.up_to is None, t.up_to or 0))
    return tuple(tiers)


def _load() -> dict[tuple[str, str | None], _ModelHistory]:
    """Index price history by ``(model, provider)``.

    ``provider`` is the tool name a price is specific to (e.g. ``"antigravity"``
    when a tool resells the model at a different rate); ``None`` is the generic
    price that applies to any provider. Both the model name and ``provider`` are
    matched when pricing an interaction, with the generic price as the fallback.
    """
    raw: dict[str, Any] = tomllib.loads(_TOML_PATH.read_text(encoding="utf-8"))
    histories: dict[tuple[str, str | None], _ModelHistory] = {}
    for model, value in raw.items():
        if isinstance(value, dict):
            entries: list[dict[str, Any]] = [value]
        elif isinstance(value, list):
            entries = value
        else:
            continue

        for entry in entries:
            provider = entry.get("provider")
            provider = str(provider) if provider is not None else None
            from_str = entry.get("from")
            effective = date.fromisoformat(from_str) if from_str else _EPOCH_ZERO
            tiers = _tiers_from(entry)
            base = tiers[0] if tiers else None
            history = histories.setdefault((model, provider), _ModelHistory())
            history.epochs.append(
                PriceEpoch(
                    effective_from=effective,
                    input=float(entry.get("input", base.input if base else 0.0)),
                    output=float(entry.get("output", base.output if base else 0.0)),
                    cache_read=float(entry.get("cache_read", base.cache_read if base else 0.0)),
                    cache_write=float(
                        entry.get("cache_write", base.cache_write if base else 0.0)
                    ),
                    tiers=tiers,
                )
            )
    for history in histories.values():
        history.epochs.sort(key=lambda e: e.effective_from)
    return histories


_HISTORIES: dict[tuple[str, str | None], _ModelHistory] = _load()
_UNKNOWN_EPOCH = PriceEpoch(effective_from=_EPOCH_ZERO, input=0.0, output=0.0)


def _history_for(model: str, provider: str | None) -> _ModelHistory | None:
    """Resolve a model+provider to its price history.

    Within a fixed ``provider`` scope: exact model match first, then longest
    known prefix match (e.g. "claude-sonnet-4-6-20251231" -> "claude-sonnet-4-6").
    """
    exact = _HISTORIES.get((model, provider))
    if exact is not None:
        return exact
    candidates = [m for (m, p) in _HISTORIES if p == provider and model.startswith(m)]
    if candidates:
        return _HISTORIES[(max(candidates, key=len), provider)]
    return None


def price_for(model: str, on: date | None = None, provider: str | None = None) -> PriceEpoch:
    """Return the price epoch for *model* active on *on* (default: today).

    *provider* is the tool a price may be specific to (e.g. a model resold by a
    tool at a different rate). Resolution order:
    1. ``provider``-specific price (exact model, then longest prefix).
    2. Generic price (no provider) — the shared list price.
    3. $0 fallback so usage is always recorded.
    """
    if on is None:
        on = date.today()

    for scope in (provider, None) if provider is not None else (None,):
        history = _history_for(model, scope)
        if history is not None:
            epoch = history.price_at(on)
            if epoch is not None:
                return epoch

    return _UNKNOWN_EPOCH


def _tier_label(tier: PriceTier, is_first: bool) -> str:
    """Human-readable size band for a tier, e.g. "≤200k" or ">200k"."""
    if tier.up_to is not None:
        return f"≤{tier.up_to // 1000}k"
    return ">200k" if not is_first else ""


def all_prices() -> list[ModelPricing]:
    """Return all price rows sorted by model, provider, then effective date.

    Each price epoch is one row; a size-tiered epoch is expanded into one row
    per tier (``tier_label`` names the band) so the full schedule is visible
    rather than just the base tier.
    """
    rows: list[ModelPricing] = []
    for model, provider in sorted(_HISTORIES, key=lambda k: (k[0], k[1] or "")):
        for epoch in _HISTORIES[(model, provider)].epochs:
            tiers = epoch.tiers or (
                PriceTier(
                    up_to=None,
                    input=epoch.input,
                    output=epoch.output,
                    cache_read=epoch.cache_read,
                    cache_write=epoch.cache_write,
                ),
            )
            for i, tier in enumerate(tiers):
                rows.append(
                    ModelPricing(
                        model=model,
                        provider=provider,
                        effective_from=epoch.effective_from.isoformat(),
                        input=tier.input,
                        output=tier.output,
                        cache_read=tier.cache_read,
                        cache_write=tier.cache_write,
                        tiered=bool(epoch.tiers),
                        tier_label=_tier_label(tier, i == 0) if epoch.tiers else "",
                    )
                )
    return rows


def cost_of(interaction: Interaction) -> float:
    """Compute the USD cost of a single interaction using the price active at its timestamp.

    The price is resolved per provider (the tool that produced the interaction),
    falling back to the generic list price, and per prompt-size tier when the
    model is tiered.
    """
    ts = interaction.timestamp
    on = ts.astimezone(timezone.utc).date() if ts.tzinfo is not None else ts.date()
    epoch = price_for(interaction.model, on, provider=interaction.tool.value)
    rate = epoch.rate_for(interaction.input_tokens)
    return (
        interaction.input_tokens * rate.input
        + interaction.output_tokens * rate.output
        + interaction.cache_read_tokens * rate.cache_read
        + interaction.cache_write_tokens * rate.cache_write
    ) / 1_000_000
