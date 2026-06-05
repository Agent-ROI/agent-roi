"""Topic classifier interface.

A classifier reads the short ``summary`` of each interaction and assigns a
concise topic label (e.g. "auth refactor", "ci pipeline", "bug: race condition").
Topics are how Agent-ROI aggregates token cost per *subject* rather than per
request, which is the whole point of measuring agent ROI.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

SYSTEM_PROMPT = (
    "You label software-engineering chat turns with a short topic. "
    "Reply with ONLY a 2-5 word lowercase topic describing the task or subject "
    "(e.g. 'auth refactor', 'flaky ci test', 'pricing model bug'). "
    "No punctuation, no quotes, no explanation."
)


class Classifier(ABC):
    """Base class for topic classifiers."""

    @abstractmethod
    def classify(self, summary: str) -> str:
        """Return a short topic label for one interaction summary."""

    def classify_batch(self, summaries: list[str]) -> list[str]:
        """Classify many summaries. Default loops; providers may override."""
        return [self.classify(s) for s in summaries]
