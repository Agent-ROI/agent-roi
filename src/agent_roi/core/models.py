"""Core domain models shared across collectors, classifier, and storage."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Tool(str, Enum):
    """Supported AI coding tools."""

    CLAUDE_CODE = "claude_code"
    CODEX = "codex"
    COPILOT = "copilot"
    CURSOR = "cursor"
    UNKNOWN = "unknown"


class Interaction(BaseModel):
    """A single normalized request/response turn parsed from a tool's logs.

    This is the canonical unit produced by collectors and stored in the database.
    Collectors translate each tool's native log format into this shape.
    """

    id: str = Field(..., description="Stable unique id (usually tool's own message id).")
    tool: Tool
    session_id: str = Field(..., description="Groups interactions from one agent session.")
    timestamp: datetime
    model: str = Field(..., description="Model name reported by the tool, e.g. 'claude-opus-4-8'.")

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    # Free-text summary the classifier reads to derive a topic. Kept short and
    # never includes full prompt bodies, to limit what leaves the machine when a
    # cloud classifier is used.
    summary: str = ""

    # Populated by the classifier; null until classification runs.
    topic: str | None = None

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_read_tokens
            + self.cache_write_tokens
        )


class TopicRollup(BaseModel):
    """Aggregated token usage and cost for a single topic."""

    topic: str
    interactions: int
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    cost_usd: float

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_read_tokens
            + self.cache_write_tokens
        )
