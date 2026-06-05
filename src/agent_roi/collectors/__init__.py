"""Collector registry.

New collectors register here so the CLI and config can refer to them by name.
"""

from __future__ import annotations

from agent_roi.collectors.base import Collector
from agent_roi.collectors.claude_code import ClaudeCodeCollector
from agent_roi.collectors.codex import CodexCollector

_REGISTRY: dict[str, type[Collector]] = {
    ClaudeCodeCollector.name: ClaudeCodeCollector,
    CodexCollector.name: CodexCollector,
}


def get_collectors(names: list[str]) -> list[Collector]:
    """Instantiate the named collectors, skipping unknown names."""
    return [_REGISTRY[name]() for name in names if name in _REGISTRY]


def all_collector_names() -> list[str]:
    return list(_REGISTRY)


__all__ = ["Collector", "get_collectors", "all_collector_names"]
