"""Classifier factory."""

from __future__ import annotations

from agent_roi.classify.base import Classifier
from agent_roi.core.config import ClassifierConfig


def get_classifier(config: ClassifierConfig) -> Classifier:
    """Build the classifier described by config. Imports lazily so an unused
    provider's dependencies/credentials are never required."""
    if config.provider == "ollama":
        from agent_roi.classify.ollama import OllamaClassifier

        return OllamaClassifier(model=config.model)
    if config.provider == "anthropic":
        from agent_roi.classify.anthropic import AnthropicClassifier

        return AnthropicClassifier(model=config.model)
    raise ValueError(f"Unknown classifier provider: {config.provider!r}")


__all__ = ["Classifier", "get_classifier"]
