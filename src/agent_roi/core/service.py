"""High-level orchestration used by both the CLI and the API.

Keeps the wiring of collectors -> storage -> classifier in one place so the CLI
and REST layers stay thin.
"""

from __future__ import annotations

import contextlib
from datetime import datetime

from agent_roi.classify import SessionDoc, get_classifier
from agent_roi.classify.base import UNCATEGORIZED
from agent_roi.collectors import get_collectors
from agent_roi.core.config import Config, config_path
from agent_roi.core.models import (
    ActivityReport,
    BudgetPeriodStatus,
    BudgetStatus,
    CollectorStatus,
    ModelPricing,
    Rollup,
    SessionDetail,
    SessionSummary,
    TimeSeriesBundle,
    TokenComposition,
    TopicBreakdown,
)
from agent_roi.core.pricing import all_prices
from agent_roi.core.timeframe import period_start
from agent_roi.storage import Database


class Service:
    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config.load()
        self.db = Database(self.config.db_path)

    def ingest(self) -> int:
        """Collect interactions from all enabled tools and store them.

        Returns the number of interactions processed.
        """
        collectors = get_collectors(self.config.collectors.enabled)
        total = 0
        for collector in collectors:
            if not collector.is_available():
                continue
            with contextlib.suppress(Exception):
                total += self.db.upsert_many(collector.collect())
        return total

    def classify(self, limit: int | None = None, reclassify: bool = True) -> int:
        """Group whole sessions into topics and apply them.

        A session is one continuous piece of work, so we classify sessions as a
        unit (not each interaction) and apply the discovered topic to all of a
        session's rows. The classifier looks at all sessions together so it can
        group the ones about the same kind of work — e.g. several sessions across
        different repos that are all "auth refactor" — into one topic.

        With ``reclassify`` (the default) every session is re-labeled, which keeps
        the clustering globally consistent. Set it to False to only label sessions
        that have no topic yet.

        Returns the number of interactions newly classified.
        """
        if reclassify:
            self.db.clear_topics()
        sessions = (
            self.db.all_sessions(limit=limit)
            if reclassify
            else self.db.unclassified_sessions(limit=limit)
        )
        if not sessions:
            return 0
        classifier = get_classifier(self.config.classifier)
        docs = [
            SessionDoc(session_id=s.session_id, project=s.project, summary=s.summary)
            for s in sessions
        ]
        labels = classifier.label_sessions(docs)
        updated = 0
        for sess in sessions:
            topic = labels.get(sess.session_id, UNCATEGORIZED)
            updated += self.db.set_session_topic(sess.session_id, topic)
        return updated

    def refresh(self) -> dict[str, int]:
        """Ingest fresh logs and re-classify everything in one step.

        This is the one-button flow for the dashboard: pull new interactions from
        every tool, then rebuild topics across the whole corpus.
        """
        ingested = self.ingest()
        classified = self.classify()
        return {"ingested": ingested, "classified": classified}

    def report(
        self,
        dimension: str = "topic",
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[Rollup]:
        """Aggregate usage/cost by 'topic', 'tool', or 'model' over a window."""
        return self.db.rollup(dimension, start=start, end=end)

    def topic_breakdown(
        self,
        topic: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> TopicBreakdown:
        """Drill into one topic: how its tokens split across tools and models."""
        return self.db.topic_breakdown(topic, start=start, end=end)

    def sessions(
        self,
        topic: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
        search: str | None = None,
    ) -> list[SessionSummary]:
        """Per-session breakdown, optionally scoped to one topic and window."""
        return self.db.sessions(
            topic=topic,
            start=start,
            end=end,
            limit=limit,
            search=search,
        )

    def composition(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> dict[str, object]:
        """Split token usage into overhead / cached / work, overall and per tool.

        Answers "where did my tokens go?" — how much is fixed agent + MCP overhead
        (cache writes), how much is cached re-sent context, how much is the actual
        conversation. The per-tool split surfaces which tools carry the heaviest
        overhead (e.g. a tool wired to many MCP servers).
        """
        by_tool = self.db.rollup("tool", start=start, end=end)
        total = Rollup.sum("all", by_tool)
        return {
            "total": TokenComposition.from_rollup(total).model_dump(),
            "by_tool": [
                {
                    "tool": r.key,
                    "estimated": r.estimated,
                    **TokenComposition.from_rollup(r).model_dump(),
                }
                for r in by_tool
            ],
        }

    def activity(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        project: str | None = None,
    ) -> ActivityReport:
        """What the agent actually did: tools called, MCP servers, files touched."""
        return self.db.activity_report(start=start, end=end, project=project)

    def get_config_info(self) -> dict[str, object]:
        return {
            "config_path": str(config_path()),
            "db_path": str(self.config.db_path),
            "classifier": self.config.classifier.model_dump(),
            "collectors": self.config.collectors.model_dump(),
            "budget": self.config.budget.model_dump(),
        }

    def update_config(
        self,
        classifier: dict[str, object] | None = None,
        collectors: dict[str, object] | None = None,
        budget: dict[str, object] | None = None,
    ) -> dict[str, object]:
        if classifier:
            self.config.classifier = self.config.classifier.model_copy(update=classifier)
        if collectors:
            self.config.collectors = self.config.collectors.model_copy(update=collectors)
        if budget is not None:
            self.config.budget = self.config.budget.model_copy(update=budget)
        self.config.save()
        return self.get_config_info()

    def session_detail(self, session_id: str) -> SessionDetail | None:
        """One session's aggregate plus its individual interactions."""
        return self.db.session_detail(session_id)

    def timeseries(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        granularity: str = "day",
    ) -> TimeSeriesBundle:
        """Usage trends for charts (day / week / month buckets)."""
        return self.db.timeseries(start=start, end=end, granularity=granularity)

    def pricing(self) -> list[ModelPricing]:
        """The pricing table behind every cost figure (for verification)."""
        return all_prices()

    def budget_status(self, now: datetime | None = None) -> BudgetStatus:
        """Spend so far this day / week / month against the configured limits.

        This turns raw cost tracking into a budget signal: each period reports
        actual spend and, where a limit is set, whether you're over it. Periods
        without a configured limit are still reported (limit ``None``) so the UI
        can show spend even before a budget is chosen.
        """
        budget = self.config.budget
        limits = {
            "day": budget.daily_usd,
            "week": budget.weekly_usd,
            "month": budget.monthly_usd,
        }
        periods = [
            BudgetPeriodStatus(
                period=period,
                start=(start := period_start(period, now=now)),
                spent_usd=self.db.total_spend(start=start),
                limit_usd=limit,
            )
            for period, limit in limits.items()
        ]
        return BudgetStatus(periods=periods)

    def sources(self) -> list[CollectorStatus]:
        """Diagnostics for every enabled collector: where it looked, what it
        found on disk, and how much is already in the database.

        This is what makes detection transparent — users can see exactly why a
        tool shows up (or doesn't) instead of guessing.
        """
        by_tool = {r.key: r for r in self.db.rollup("tool")}
        statuses: list[CollectorStatus] = []
        for collector in get_collectors(self.config.collectors.enabled):
            available = collector.is_available()
            files = collector.count_files()
            roll = by_tool.get(collector.tool.value)
            interactions = roll.interactions if roll else 0

            note = collector.note()
            if not note:
                if not available:
                    note = "No logs found on this machine."
                elif files and interactions == 0:
                    note = "Logs found but not ingested yet — run a refresh."

            statuses.append(
                CollectorStatus(
                    name=collector.name,
                    tool=collector.tool.value,
                    available=available,
                    search_paths=[str(p) for p in collector.search_paths()],
                    log_files=files,
                    interactions=interactions,
                    tokens=roll.total_tokens if roll else 0,
                    cost_usd=roll.cost_usd if roll else 0.0,
                    note=note,
                )
            )
        return statuses
