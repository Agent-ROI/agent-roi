"""Collector interface.

A collector knows how to find one tool's local logs and turn them into a stream
of normalized :class:`Interaction` objects. Collectors must be read-only and
idempotent: running ingest twice should not double-count, which is enforced
upstream by the stable ``Interaction.id``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from pathlib import Path

from agent_roi.core.models import Interaction, Tool


class Collector(ABC):
    """Base class for all tool log collectors."""

    #: Which tool this collector produces interactions for.
    tool: Tool

    #: Stable name used in config's ``collectors.enabled`` list.
    name: str

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this tool's logs exist on the current machine."""

    @abstractmethod
    def collect(self) -> Iterator[Interaction]:
        """Yield normalized interactions parsed from local logs."""

    def search_paths(self) -> list[Path]:
        """Directories this collector looked in (for the diagnostics report).

        Default is empty; collectors override to expose where they searched so
        users can see why a tool was or wasn't detected.
        """
        return []

    def count_files(self) -> int:
        """Number of log files this collector can see (cheap; no parsing)."""
        return 0

    def note(self) -> str:
        """Optional human-readable hint shown in diagnostics (e.g. why empty)."""
        return ""
