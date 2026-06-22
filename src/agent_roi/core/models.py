"""Core domain models shared across collectors, classifier, and storage."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, computed_field


class Tool(str, Enum):
    """Supported AI coding tools."""

    CLAUDE_CODE = "claude_code"
    CODEX = "codex"
    COPILOT = "copilot"
    GEMINI = "gemini"
    HERMES = "hermes"
    CURSOR = "cursor"
    ANTIGRAVITY = "antigravity"
    UNKNOWN = "unknown"


class Activity(BaseModel):
    """One concrete action an agent took inside an interaction.

    The token buckets in :class:`TokenComposition` say *how much* was spent on
    overhead vs work; activities say *what was actually done* — which tools were
    invoked, which MCP servers, which files were read or edited. This is what lets
    the UI show a user the real contents behind the abstract numbers rather than
    just "5.8M overhead tokens".

    ``kind`` is the tool name (``Bash``, ``Read``, ``Edit`` …). For MCP tools the
    name is ``mcp__<server>__<tool>``; ``mcp_server`` is then set to ``<server>``
    so MCP usage can be grouped. ``target`` is the file path the action touched,
    when the tool has one (Read/Edit/Write).
    """

    kind: str = Field(..., description="Tool name, e.g. 'Bash', 'Read', 'mcp__github__list'.")
    mcp_server: str | None = Field(default=None, description="MCP server, if this is an MCP tool.")
    target: str | None = Field(default=None, description="File path acted on, when applicable.")
    # Estimated tokens this call returned into the context (tool_result size).
    # Always an estimate — the API never reports per-tool token usage — so it is
    # surfaced with an "estimated" badge. 0 when the result isn't recorded.
    result_tokens: int = Field(default=0, description="Estimated tokens returned by the call.")


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

    # Concrete actions taken in this turn (tool calls, MCP calls, file edits).
    # Stored in a separate table; never part of token/cost aggregation.
    activities: list[Activity] = Field(default_factory=list)

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

    @classmethod
    def sum(cls, key: str, rollups: list[Rollup]) -> Rollup:
        """Combine rollups into one totaled row under ``key``.

        ``estimated`` is token-weighted: a child's interactions are uniform in
        estimated-ness, so weight each by its tokens and flag the total estimated
        only when estimated tokens are at least half (ties lean estimated).
        """
        est = sum(r.total_tokens for r in rollups if r.estimated)
        total = sum(r.total_tokens for r in rollups)
        return cls(
            key=key,
            interactions=sum(r.interactions for r in rollups),
            input_tokens=sum(r.input_tokens for r in rollups),
            output_tokens=sum(r.output_tokens for r in rollups),
            cache_read_tokens=sum(r.cache_read_tokens for r in rollups),
            cache_write_tokens=sum(r.cache_write_tokens for r in rollups),
            cost_usd=sum(r.cost_usd for r in rollups),
            estimated=est > 0 and est * 2 >= total,
        )


class TokenComposition(BaseModel):
    """Breaks token usage into *where it went*, not just how much.

    Most tokens an agent spends aren't the user's words — they're fixed per-turn
    overhead (system prompt + tool definitions + MCP schemas) and re-sent context.
    Prompt caching makes the repeated part cheap, but it's still volume. We split
    the same numbers a :class:`Rollup` already holds into three buckets so the UI
    can answer "where did my tokens actually go?":

    - ``overhead`` — tokens written into the cache (``cache_write``). The first
      turn of a session writes the system prompt, tool definitions and every MCP
      server's tool schema here, so this is the best available proxy for fixed
      agent/MCP overhead.
    - ``cached`` — tokens served from the cache (``cache_read``): context re-sent
      each turn but billed at the cheap cached rate. Large ``cached`` means
      caching is doing its job.
    - ``work`` — uncached input plus output (``input + output``): the part that
      actually varies with the conversation.

    ``estimated`` mirrors the rollup: when true (e.g. Copilot, which reports no
    real token counts and no cache split), the composition is approximate and
    everything lands in ``work``.
    """

    overhead: int
    cached: int
    work: int
    overhead_pct: float
    cached_pct: float
    work_pct: float
    estimated: bool = False

    @classmethod
    def from_rollup(cls, r: Rollup) -> TokenComposition:
        overhead = r.cache_write_tokens
        cached = r.cache_read_tokens
        work = r.input_tokens + r.output_tokens
        total = overhead + cached + work
        pct = (lambda n: round(100.0 * n / total, 1)) if total else (lambda n: 0.0)
        return cls(
            overhead=overhead,
            cached=cached,
            work=work,
            overhead_pct=pct(overhead),
            cached_pct=pct(cached),
            work_pct=pct(work),
            estimated=r.estimated,
        )


class ActivityCount(BaseModel):
    """A label (tool name, MCP server, or file path) with usage and return volume.

    ``count`` is how many times it was called; ``result_tokens`` is the estimated
    tokens it returned into the context across those calls (0 when the tool's
    return body isn't recorded, e.g. Copilot). The token figure is always an
    estimate — no API reports per-tool usage.
    """

    label: str
    count: int
    result_tokens: int = 0


class ActivityReport(BaseModel):
    """What the agent actually did, aggregated for the Activity Analysis page.

    Turns the abstract overhead/work split into concrete usage: which tools were
    called and how often, which MCP servers were involved, and which files were
    touched most. ``total_actions`` is every recorded tool call in the window.
    """

    total_actions: int
    by_tool: list[ActivityCount]
    by_mcp: list[ActivityCount]
    top_files: list[ActivityCount]


class TopicROI(BaseModel):
    """A topic's unit economics — what one "piece of work" of this kind costs.

    A topic is the natural unit of "a thing you did": the classifier groups
    continuous work into sessions, and like sessions into a topic. So the
    per-session averages here answer "on average, how much token / time / money
    does finishing one of these take?".

    ``active_seconds`` is summed active development time across the topic's
    sessions (idle excluded). ``usd_per_hour`` is the burn *rate* (intensity).
    ``cost_cv`` is the coefficient of variation of per-session cost (stdev /
    mean) — unitless, so it compares across topics: a high value means this kind
    of work is *inconsistent* (some sessions cost far more than others), a
    "spinning wheels / re-work" signal. None when there are too few sessions to
    have a meaningful spread.
    """

    topic: str
    sessions: int
    interactions: int
    cost_usd: float
    total_tokens: int
    active_seconds: float
    # Coefficient of variation of per-session cost; None if < 2 sessions.
    cost_cv: float | None = None
    estimated: bool = False

    @computed_field  # type: ignore[prop-decorator]
    @property
    def active_minutes(self) -> float:
        return round(self.active_seconds / 60, 1)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def usd_per_hour(self) -> float | None:
        if self.active_seconds <= 0:
            return None
        return round(self.cost_usd / (self.active_seconds / 3600), 2)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cost_per_session(self) -> float:
        """Average USD to finish one piece of work of this kind."""
        return round(self.cost_usd / self.sessions, 4) if self.sessions else 0.0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def minutes_per_session(self) -> float:
        """Average active minutes to finish one piece of work of this kind."""
        if not self.sessions:
            return 0.0
        return round(self.active_seconds / self.sessions / 60, 1)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def tokens_per_session(self) -> int:
        """Average tokens to finish one piece of work of this kind."""
        return round(self.total_tokens / self.sessions) if self.sessions else 0


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
    # Tool this price is specific to (e.g. a resold model), or None for the
    # generic list price that applies to any provider.
    provider: str | None = None
    effective_from: str  # ISO-8601 date; the first day this price was active
    input: float
    output: float
    cache_read: float
    cache_write: float
    # True when this model is priced by prompt size; each size band is emitted
    # as its own row, distinguished by ``tier_label``.
    tiered: bool = False
    # Human-readable size band this row's prices apply to (e.g. "≤200k",
    # ">200k"). Empty for flat (non-tiered) models.
    tier_label: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def vendor(self) -> str:
        """Brand the model belongs to, for grouping the pricing view."""
        m = self.model.lower()
        if m.startswith("claude"):
            return "Anthropic"
        if m.startswith("gpt"):
            return "OpenAI"
        if m.startswith("gemini"):
            return "Google"
        return "Other"


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

    # Estimated *active* development time in this session: the sum of gaps
    # between turns, excluding idle stretches (see core.active_time). 0 for a
    # single-turn session (no measurable elapsed work). Filled in by the service
    # layer, not stored — it depends on a globally-derived idle threshold.
    active_seconds: float = 0.0

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_read_tokens
            + self.cache_write_tokens
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def active_minutes(self) -> float:
        return round(self.active_seconds / 60, 1)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def usd_per_hour(self) -> float | None:
        """Spend rate over active time, or None when time is unmeasurable."""
        if self.active_seconds <= 0:
            return None
        return round(self.cost_usd / (self.active_seconds / 3600), 2)


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


class BudgetPeriodStatus(BaseModel):
    """Spend vs. an optional limit for one rolling period (day / week / month).

    This is the unit behind the dashboard's budget gauges. ``limit_usd`` is
    ``None`` when no budget is configured for the period, in which case spend is
    still reported but ``pct``/``over`` are meaningless (left at null/false).
    """

    period: str  # "day" | "week" | "month"
    start: datetime  # inclusive start of the current period
    spent_usd: float
    limit_usd: float | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def pct(self) -> float | None:
        """Spend as a percentage of the limit, or None when unbudgeted."""
        if self.limit_usd is None or self.limit_usd <= 0:
            return None
        return self.spent_usd / self.limit_usd * 100

    @computed_field  # type: ignore[prop-decorator]
    @property
    def over(self) -> bool:
        """True when a limit is set and spend has exceeded it."""
        return self.limit_usd is not None and self.spent_usd > self.limit_usd

    @computed_field  # type: ignore[prop-decorator]
    @property
    def remaining_usd(self) -> float | None:
        if self.limit_usd is None:
            return None
        return self.limit_usd - self.spent_usd


class BudgetStatus(BaseModel):
    """All configured budget periods at once — the dashboard's budget panel."""

    periods: list[BudgetPeriodStatus]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def any_over(self) -> bool:
        return any(p.over for p in self.periods)


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
