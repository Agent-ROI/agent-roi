"""Topic classifier interface.

A classifier looks at whole *sessions* (one continuous piece of agent work) and
groups the ones that are about the same thing, assigning each group a short topic
label such as "auth refactor" or "ci pipeline". Topics are how Agent-ROI
aggregates token cost per *subject* rather than per request, which is the whole
point of measuring agent ROI.

Classification is deliberately model-free: it discovers topics from the text of
the sessions themselves (semantic similarity), so it runs fully offline, costs
nothing, and never sends anything to an external service.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

UNCATEGORIZED = "uncategorized"
# Catch-all for clusters too small to be worth their own topic row. Distinct
# from UNCATEGORIZED (which means "no usable text"): these sessions *were*
# grouped, the group was just a one-off not worth surfacing on its own.
MISC = "misc"


@dataclass
class SessionDoc:
    """One session handed to the classifier for topic discovery.

    ``summary`` is a compact, combined snippet of the session's interactions;
    ``project`` is the coarse repo/folder grouping derived from the cwd.
    """

    session_id: str
    project: str
    summary: str


class Classifier(ABC):
    """Base class for topic classifiers.

    Implementations look at all the given sessions together so they can group
    similar ones, rather than labeling each session in isolation.
    """

    @abstractmethod
    def label_sessions(self, sessions: list[SessionDoc]) -> dict[str, str]:
        """Return a ``{session_id: topic}`` mapping for the given sessions."""
