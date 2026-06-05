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
    GEMINI = "gemini"
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

    # Working directory the agent ran in, when the tool records it. Used to derive
    # ``project`` and as a signal for topic classification.
    cwd: str = ""
    # A coarse grouping derived from cwd (git root / folder name). Not the final
    # topic — the classifier still assigns a semantic ``topic`` per session.
    project: str = ""

    # Free-text summary the classifier reads to derive a topic. Kept short and
    # never includes full prompt bodies. Classification is local and offline, so
    # nothing here ever leaves the machine.
    summary: str = ""

    # Populated by the classifier; null until classification runs.
    topic: str | None = None

    # True when token counts are estimated (e.g. via a tokenizer) rather than
    # reported by the tool. Copilot doesn't expose real usage, so its
    # interactions are flagged here and shown as "estimated" in reports.
    estimated: bool = False

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_read_tokens
            + self.cache_write_tokens
        )


class Rollup(BaseModel):
    """Aggregated token usage and cost for one value of a grouping dimension.

    ``key`` is the dimension value (a topic, a tool, or a model, depending on how
    the rollup was requested). ``estimated`` is true if *any* interaction in the
    group has estimated rather than tool-reported tokens, so the UI can mark the
    number as approximate.
    """

    key: str
    interactions: int
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    cost_usd: float
    estimated: bool = False

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_read_tokens
            + self.cache_write_tokens
        )


class TopicBreakdown(BaseModel):
    """A topic's total, plus how it splits across tools and models.

    This is what lets a user answer "this topic's tokens came from which tools,
    at what price?" — the drill-down behind a single topic row.
    """

    topic: str
    total: Rollup
    by_tool: list[Rollup]
    by_model: list[Rollup]


class ModelPricing(BaseModel):
    """Per-model unit prices (USD per 1M tokens), exposed so users can verify
    that cost = usage x these numbers."""

    model: str
    effective_from: str  # ISO-8601 date; the first day this price was active
    input: float
    output: float
    cache_read: float
    cache_write: float


class SessionSummary(BaseModel):
    """One agent session aggregated: the unit a topic is made of.

    A topic groups many sessions; a session groups many interactions. This is the
    middle layer of the topic -> session -> interaction drill-down.
    """

    session_id: str
    topic: str
    project: str
    tools: list[str]
    models: list[str]
    started: datetime
    ended: datetime
    interactions: int
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    cost_usd: float
    estimated: bool = False

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_read_tokens
            + self.cache_write_tokens
        )


class InteractionView(BaseModel):
    """A single interaction as shown when drilling into a session."""

    id: str
    tool: str
    model: str
    timestamp: datetime
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    cost_usd: float
    estimated: bool
    summary: str

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_read_tokens
            + self.cache_write_tokens
        )


class SessionDetail(BaseModel):
    """A session's aggregate plus the interactions (conversation turns) in it."""

    session: SessionSummary
    interactions: list[InteractionView]


class TimeSeriesPoint(BaseModel):
    """Daily usage bucket for trend charts."""

    date: str
    interactions: int
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cost_usd: float

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_read_tokens
            + self.cache_write_tokens
        )


class TimeSeriesSplitRow(BaseModel):
    """One day of token usage split across a dimension (tool, model, …)."""

    date: str
    values: dict[str, int]
    cost_usd: float
    interactions: int


class TimeSeriesBundle(BaseModel):
    """Everything the trends dashboard needs in one round trip."""

    totals: list[TimeSeriesPoint]
    by_tool: list[TimeSeriesSplitRow]
    by_model: list[TimeSeriesSplitRow]
    tool_keys: list[str]
    model_keys: list[str]


class CollectorStatus(BaseModel):
    """Diagnostics for one tool collector: where it looked and what it found.

    This powers the `doctor` command and the dashboard's "data sources" panel so
    users can see *why* a tool was or wasn't picked up, instead of guessing.
    """

    name: str
    tool: str
    available: bool
    search_paths: list[str]
    log_files: int
    interactions: int = 0
    tokens: int = 0
    cost_usd: float = 0.0
    note: str = ""
