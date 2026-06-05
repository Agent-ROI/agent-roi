"""Classifier factory."""

from __future__ import annotations

from agent_roi.classify.base import Classifier, SessionDoc
from agent_roi.core.config import ClassifierConfig


def get_classifier(config: ClassifierConfig) -> Classifier:
    """Build the classifier described by config.

    Only the model-free ``semantic`` provider exists: it discovers topics locally
    from session text, so there is nothing to install, no server to run, and no
    tokens to spend.
    """
    if config.provider == "semantic":
        from agent_roi.classify.semantic import SemanticClassifier

        return SemanticClassifier(
            similarity_threshold=config.similarity_threshold,
            label_terms=config.label_terms,
        )
    raise ValueError(f"Unknown classifier provider: {config.provider!r}")


__all__ = ["Classifier", "SessionDoc", "get_classifier"]
