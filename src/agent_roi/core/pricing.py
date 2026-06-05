"""Per-model token pricing, used to turn token counts into USD cost.

Prices are USD per 1M tokens. This table is intentionally simple and easy to
edit; keep it current as providers change pricing. Unknown models fall back to a
zero price so usage is still tracked (cost just shows as 0).
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_roi.core.models import Interaction, ModelPricing


@dataclass(frozen=True)
class ModelPrice:
    input: float
    output: float
    cache_read: float = 0.0
    cache_write: float = 0.0


# Prices in USD per 1,000,000 tokens. Extend freely.
PRICES: dict[str, ModelPrice] = {
    "claude-opus-4-8": ModelPrice(input=15.0, output=75.0, cache_read=1.5, cache_write=18.75),
    "claude-sonnet-4-6": ModelPrice(input=3.0, output=15.0, cache_read=0.3, cache_write=3.75),
    "claude-haiku-4-5": ModelPrice(input=0.8, output=4.0, cache_read=0.08, cache_write=1.0),
    "gpt-4o": ModelPrice(input=2.5, output=10.0),
    "gpt-4o-mini": ModelPrice(input=0.15, output=0.6),
    # Codex normalizes "gpt-5.5" -> "gpt-5-5". Pricing is approximate; edit to match
    # your plan (see docs/configuration — pricing is user-verifiable).
    "gpt-5-5": ModelPrice(input=1.25, output=10.0, cache_read=0.125),
    "gpt-5": ModelPrice(input=1.25, output=10.0, cache_read=0.125),
}

_UNKNOWN = ModelPrice(input=0.0, output=0.0)


def price_for(model: str) -> ModelPrice:
    """Resolve a price by exact match, then by longest known prefix."""
    if model in PRICES:
        return PRICES[model]
    candidates = [name for name in PRICES if model.startswith(name)]
    if candidates:
        return PRICES[max(candidates, key=len)]
    return _UNKNOWN


def all_prices() -> list[ModelPricing]:
    """Return the full pricing table, so users can verify cost = usage x price."""
    return [
        ModelPricing(
            model=name,
            input=p.input,
            output=p.output,
            cache_read=p.cache_read,
            cache_write=p.cache_write,
        )
        for name, p in sorted(PRICES.items())
    ]


def cost_of(interaction: Interaction) -> float:
    """Compute the USD cost of a single interaction."""
    p = price_for(interaction.model)
    return (
        interaction.input_tokens * p.input
        + interaction.output_tokens * p.output
        + interaction.cache_read_tokens * p.cache_read
        + interaction.cache_write_tokens * p.cache_write
    ) / 1_000_000
