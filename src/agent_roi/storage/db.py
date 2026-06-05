"""SQLite storage for interactions, with upsert + topic aggregation.

Local-first: a single SQLite file holds every collected interaction. Writes are
idempotent on the interaction ``id`` so re-running ingest never double-counts.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import String, create_engine, func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from agent_roi.core.models import (
    Interaction,
    InteractionView,
    Rollup,
    SessionDetail,
    SessionSummary,
    TimeSeriesBundle,
    TimeSeriesPoint,
    TimeSeriesSplitRow,
    TopicBreakdown,
)
from agent_roi.core.pricing import cost_of


@dataclass
class UnclassifiedSession:
    """A session awaiting classification, with a combined summary to label."""

    session_id: str
    project: str
    summary: str


class Base(DeclarativeBase):
    pass


class InteractionRow(Base):
    __tablename__ = "interactions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tool: Mapped[str] = mapped_column(String, index=True)
    session_id: Mapped[str] = mapped_column(String, index=True)
    timestamp: Mapped[datetime] = mapped_column(index=True)
    model: Mapped[str] = mapped_column(String, index=True)
    input_tokens: Mapped[int] = mapped_column(default=0)
    output_tokens: Mapped[int] = mapped_column(default=0)
    cache_read_tokens: Mapped[int] = mapped_column(default=0)
    cache_write_tokens: Mapped[int] = mapped_column(default=0)
    cwd: Mapped[str] = mapped_column(String, default="")
    project: Mapped[str] = mapped_column(String, default="", index=True)
    summary: Mapped[str] = mapped_column(String, default="")
    topic: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    cost_usd: Mapped[float] = mapped_column(default=0.0)
    estimated: Mapped[bool] = mapped_column(default=False)


class Database:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{path}")
        Base.metadata.create_all(self.engine)
        self._migrate()

    def _migrate(self) -> None:
        """Add columns introduced after a database was first created.

        ``create_all`` only creates missing *tables*, never missing *columns*, so
        a database from an older version is missing columns added later. We patch
        them in with ``ALTER TABLE`` (SQLite supports adding columns cheaply).
        """
        expected = {
            "estimated": "BOOLEAN DEFAULT 0",
            "cwd": "TEXT DEFAULT ''",
            "project": "TEXT DEFAULT ''",
        }
        with self.engine.begin() as conn:
            rows = conn.exec_driver_sql("PRAGMA table_info(interactions)").fetchall()
            existing = {row[1] for row in rows}
            for column, ddl in expected.items():
                if column not in existing:
                    conn.exec_driver_sql(f"ALTER TABLE interactions ADD COLUMN {column} {ddl}")

    def upsert_many(self, interactions: Iterable[Interaction]) -> int:
        """Insert or update interactions. Returns the number processed.

        Existing rows keep their ``topic`` unless the incoming row has one, so a
        re-ingest does not wipe classifications.
        """
        count = 0
        with Session(self.engine) as session:
            for itx in interactions:
                values = {
                    "id": itx.id,
                    "tool": itx.tool.value,
                    "session_id": itx.session_id,
                    "timestamp": itx.timestamp,
                    "model": itx.model,
                    "input_tokens": itx.input_tokens,
                    "output_tokens": itx.output_tokens,
                    "cache_read_tokens": itx.cache_read_tokens,
                    "cache_write_tokens": itx.cache_write_tokens,
                    "cwd": itx.cwd,
                    "project": itx.project,
                    "summary": itx.summary,
                    "topic": itx.topic,
                    "cost_usd": cost_of(itx),
                    "estimated": itx.estimated,
                }
                stmt = sqlite_insert(InteractionRow).values(**values)
                update_cols = {k: v for k, v in values.items() if k not in ("id", "topic")}
                stmt = stmt.on_conflict_do_update(index_elements=["id"], set_=update_cols)
                session.execute(stmt)
                count += 1
            session.commit()
        return count

    def unclassified(self, limit: int | None = None) -> list[InteractionRow]:
        with Session(self.engine) as session:
            stmt = select(InteractionRow).where(InteractionRow.topic.is_(None))
            if limit is not None:
                stmt = stmt.limit(limit)
            return list(session.scalars(stmt))

    def set_topic(self, interaction_id: str, topic: str) -> None:
        with Session(self.engine) as session:
            row = session.get(InteractionRow, interaction_id)
            if row is not None:
                row.topic = topic
                session.commit()

    def unclassified_sessions(self, limit: int | None = None) -> list[UnclassifiedSession]:
        """Sessions with at least one unclassified interaction (topic IS NULL)."""
        return self._session_docs(only_unclassified=True, limit=limit)

    def all_sessions(self, limit: int | None = None) -> list[UnclassifiedSession]:
        """Every session, classified or not.

        Semantic clustering works best when it sees all sessions together, so the
        classifier re-labels the whole corpus rather than only new sessions.
        """
        return self._session_docs(only_unclassified=False, limit=limit)

    def _session_docs(
        self, only_unclassified: bool, limit: int | None
    ) -> list[UnclassifiedSession]:
        with Session(self.engine) as session:
            stmt = select(InteractionRow).order_by(
                InteractionRow.session_id, InteractionRow.timestamp
            )
            if only_unclassified:
                stmt = stmt.where(InteractionRow.topic.is_(None))
            rows = list(session.scalars(stmt))

        by_session: dict[str, list[InteractionRow]] = {}
        for row in rows:
            by_session.setdefault(row.session_id, []).append(row)

        result: list[UnclassifiedSession] = []
        for session_id, items in by_session.items():
            # Build a compact summary from the most informative snippets, capped.
            snippets: list[str] = []
            for it in items:
                if it.summary and it.summary not in snippets:
                    snippets.append(it.summary)
                if len(snippets) >= 8:
                    break
            project = next((it.project for it in items if it.project), "")
            result.append(
                UnclassifiedSession(
                    session_id=session_id,
                    project=project,
                    summary="\n".join(snippets)[:2000],
                )
            )
            if limit is not None and len(result) >= limit:
                break
        return result

    def clear_topics(self) -> None:
        """Reset every interaction's topic so the next classify re-labels all."""
        with Session(self.engine) as session:
            for row in session.scalars(select(InteractionRow)):
                row.topic = None
            session.commit()

    def set_session_topic(self, session_id: str, topic: str) -> int:
        """Apply a topic to every interaction in a session. Returns rows updated."""
        with Session(self.engine) as session:
            rows = list(
                session.scalars(
                    select(InteractionRow).where(InteractionRow.session_id == session_id)
                )
            )
            for row in rows:
                row.topic = topic
            session.commit()
            return len(rows)

    # Columns that can be used as a grouping dimension.
    _DIMENSIONS = {
        "topic": func.coalesce(InteractionRow.topic, "uncategorized"),
        "tool": InteractionRow.tool,
        "model": InteractionRow.model,
        "project": func.coalesce(func.nullif(InteractionRow.project, ""), "unknown"),
    }

    def rollup(
        self,
        dimension: str = "topic",
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[Rollup]:
        """Aggregate usage and cost grouped by ``dimension`` over an optional
        time window. ``dimension`` is one of 'topic', 'tool', 'model'."""
        if dimension not in self._DIMENSIONS:
            raise ValueError(f"Unknown dimension: {dimension!r}")
        key_col = self._DIMENSIONS[dimension]

        with Session(self.engine) as session:
            stmt: Any = select(
                key_col.label("key"),
                func.count().label("interactions"),
                func.sum(InteractionRow.input_tokens),
                func.sum(InteractionRow.output_tokens),
                func.sum(InteractionRow.cache_read_tokens),
                func.sum(InteractionRow.cache_write_tokens),
                func.sum(InteractionRow.cost_usd),
                func.max(InteractionRow.estimated),
            )
            stmt = _apply_window(stmt, start, end)
            stmt = stmt.group_by(key_col).order_by(func.sum(InteractionRow.cost_usd).desc())
            return [_row_to_rollup(row) for row in session.execute(stmt)]

    def topic_breakdown(
        self,
        topic: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> TopicBreakdown:
        """For one topic, return its total plus a split by tool and by model."""
        is_uncat = topic == "uncategorized"
        topic_filter = (
            InteractionRow.topic.is_(None) if is_uncat else (InteractionRow.topic == topic)
        )

        def grouped(key_col: Any) -> list[Rollup]:
            with Session(self.engine) as session:
                stmt: Any = select(
                    key_col.label("key"),
                    func.count(),
                    func.sum(InteractionRow.input_tokens),
                    func.sum(InteractionRow.output_tokens),
                    func.sum(InteractionRow.cache_read_tokens),
                    func.sum(InteractionRow.cache_write_tokens),
                    func.sum(InteractionRow.cost_usd),
                    func.max(InteractionRow.estimated),
                ).where(topic_filter)
                stmt = _apply_window(stmt, start, end)
                stmt = stmt.group_by(key_col).order_by(func.sum(InteractionRow.cost_usd).desc())
                return [_row_to_rollup(row) for row in session.execute(stmt)]

        by_tool = grouped(InteractionRow.tool)
        by_model = grouped(InteractionRow.model)
        total = _sum_rollups(topic, by_tool)
        return TopicBreakdown(topic=topic, total=total, by_tool=by_tool, by_model=by_model)

    def sessions(
        self,
        topic: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
        search: str | None = None,
    ) -> list[SessionSummary]:
        """Aggregate interactions into per-session rows (optionally one topic).

        This is the middle of the topic -> session -> interaction drill-down: each
        row shows how a single session spent tokens, across which tools/models.
        """
        with Session(self.engine) as session:
            stmt: Any = select(
                InteractionRow.session_id,
                func.coalesce(InteractionRow.topic, "uncategorized"),
                func.max(InteractionRow.project),
                func.group_concat(InteractionRow.tool.distinct()),
                func.group_concat(InteractionRow.model.distinct()),
                func.min(InteractionRow.timestamp),
                func.max(InteractionRow.timestamp),
                func.count(),
                func.sum(InteractionRow.input_tokens),
                func.sum(InteractionRow.output_tokens),
                func.sum(InteractionRow.cache_read_tokens),
                func.sum(InteractionRow.cache_write_tokens),
                func.sum(InteractionRow.cost_usd),
                func.max(InteractionRow.estimated),
            )
            stmt = _apply_window(stmt, start, end)
            if topic is not None:
                stmt = stmt.where(_topic_filter(topic))
            if search:
                pattern = f"%{search}%"
                stmt = stmt.where(
                    InteractionRow.summary.ilike(pattern)
                    | InteractionRow.topic.ilike(pattern)
                    | InteractionRow.project.ilike(pattern)
                )
            stmt = stmt.group_by(InteractionRow.session_id).order_by(
                func.sum(InteractionRow.cost_usd).desc()
            )
            if limit is not None:
                stmt = stmt.limit(limit)
            return [_row_to_session(row) for row in session.execute(stmt)]

    def total_spend(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> float:
        """Total USD cost across all interactions in an optional time window."""
        with Session(self.engine) as session:
            stmt: Any = select(func.sum(InteractionRow.cost_usd))
            stmt = _apply_window(stmt, start, end)
            return float(session.execute(stmt).scalar() or 0.0)

    def timeseries(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        granularity: str = "day",
        top_series: int = 8,
    ) -> TimeSeriesBundle:
        """Token/cost buckets plus splits by tool and model."""
        bucket = _timeseries_bucket(granularity)
        totals = self._timeseries_totals(start, end, bucket)
        by_tool, tool_keys = self._timeseries_split(
            InteractionRow.tool, start, end, top_series, bucket
        )
        by_model, model_keys = self._timeseries_split(
            InteractionRow.model, start, end, top_series, bucket
        )
        return TimeSeriesBundle(
            totals=totals,
            by_tool=by_tool,
            by_model=by_model,
            tool_keys=tool_keys,
            model_keys=model_keys,
        )

    def _timeseries_totals(
        self,
        start: datetime | None,
        end: datetime | None,
        bucket: Any,
    ) -> list[TimeSeriesPoint]:
        period = bucket.label("period")
        with Session(self.engine) as session:
            stmt: Any = select(
                period,
                func.count(),
                func.sum(InteractionRow.input_tokens),
                func.sum(InteractionRow.output_tokens),
                func.sum(InteractionRow.cache_read_tokens),
                func.sum(InteractionRow.cache_write_tokens),
                func.sum(InteractionRow.cost_usd),
            )
            stmt = _apply_window(stmt, start, end)
            stmt = stmt.group_by(period).order_by(period)
            return [
                TimeSeriesPoint(
                    date=str(row[0]),
                    interactions=row[1],
                    input_tokens=row[2] or 0,
                    output_tokens=row[3] or 0,
                    cache_read_tokens=row[4] or 0,
                    cache_write_tokens=row[5] or 0,
                    cost_usd=row[6] or 0.0,
                )
                for row in session.execute(stmt)
            ]

    def _timeseries_split(
        self,
        key_col: Any,
        start: datetime | None,
        end: datetime | None,
        top: int,
        bucket: Any,
    ) -> tuple[list[TimeSeriesSplitRow], list[str]]:
        period = bucket.label("period")
        with Session(self.engine) as session:
            stmt: Any = select(
                period,
                key_col.label("series_key"),
                func.count(),
                func.sum(InteractionRow.input_tokens),
                func.sum(InteractionRow.output_tokens),
                func.sum(InteractionRow.cache_read_tokens),
                func.sum(InteractionRow.cache_write_tokens),
                func.sum(InteractionRow.cost_usd),
            )
            stmt = _apply_window(stmt, start, end)
            stmt = stmt.group_by(period, key_col).order_by(period)
            raw = list(session.execute(stmt))

        totals_by_key: dict[str, int] = {}
        by_day: dict[str, dict[str, int]] = {}
        meta: dict[str, tuple[int, float]] = {}
        for row in raw:
            d, key = str(row[0]), str(row[1])
            tokens = (row[3] or 0) + (row[4] or 0) + (row[5] or 0) + (row[6] or 0)
            totals_by_key[key] = totals_by_key.get(key, 0) + tokens
            bucket = by_day.setdefault(d, {})
            bucket[key] = bucket.get(key, 0) + tokens
            prev = meta.get(d, (0, 0.0))
            meta[d] = (prev[0] + row[2], prev[1] + (row[7] or 0.0))

        ranked = sorted(totals_by_key, key=lambda k: totals_by_key[k], reverse=True)
        keep = ranked[:top]
        other_label = "other"
        if len(ranked) > top:
            keep = [*keep, other_label]

        rows: list[TimeSeriesSplitRow] = []
        for d in sorted(by_day):
            values: dict[str, int] = {}
            overflow = 0
            for key, tokens in by_day[d].items():
                if key in keep and key != other_label:
                    values[key] = values.get(key, 0) + tokens
                elif other_label in keep:
                    overflow += tokens
            if overflow:
                values[other_label] = overflow
            interactions, cost = meta.get(d, (0, 0.0))
            rows.append(
                TimeSeriesSplitRow(
                    date=d,
                    values=values,
                    interactions=interactions,
                    cost_usd=cost,
                )
            )
        return rows, keep

    def session_detail(self, session_id: str) -> SessionDetail | None:
        """A session's aggregate plus its individual interactions, newest first."""
        summaries = [s for s in self.sessions() if s.session_id == session_id]
        if not summaries:
            return None
        with Session(self.engine) as session:
            rows = list(
                session.scalars(
                    select(InteractionRow)
                    .where(InteractionRow.session_id == session_id)
                    .order_by(InteractionRow.timestamp.desc())
                )
            )
        interactions = [
            InteractionView(
                id=r.id,
                tool=r.tool,
                model=r.model,
                timestamp=r.timestamp,
                input_tokens=r.input_tokens,
                output_tokens=r.output_tokens,
                cache_read_tokens=r.cache_read_tokens,
                cache_write_tokens=r.cache_write_tokens,
                cost_usd=r.cost_usd,
                estimated=r.estimated,
                summary=r.summary,
            )
            for r in rows
        ]
        return SessionDetail(session=summaries[0], interactions=interactions)


def _topic_filter(topic: str) -> Any:
    if topic == "uncategorized":
        return InteractionRow.topic.is_(None)
    return InteractionRow.topic == topic


def _split_concat(value: Any) -> list[str]:
    """Split SQLite group_concat output into a sorted, de-duplicated list."""
    if not value:
        return []
    return sorted({part for part in str(value).split(",") if part})


def _row_to_session(row: Any) -> SessionSummary:
    return SessionSummary(
        session_id=str(row[0]),
        topic=str(row[1]),
        project=str(row[2] or ""),
        tools=_split_concat(row[3]),
        models=_split_concat(row[4]),
        started=row[5],
        ended=row[6],
        interactions=row[7],
        input_tokens=row[8] or 0,
        output_tokens=row[9] or 0,
        cache_read_tokens=row[10] or 0,
        cache_write_tokens=row[11] or 0,
        cost_usd=row[12] or 0.0,
        estimated=bool(row[13]),
    )


def _timeseries_bucket(granularity: str) -> Any:
    if granularity == "week":
        return func.strftime("%Y-W%W", InteractionRow.timestamp)
    if granularity == "month":
        return func.strftime("%Y-%m", InteractionRow.timestamp)
    if granularity != "day":
        raise ValueError(f"Unknown granularity: {granularity!r}")
    return func.strftime("%Y-%m-%d", InteractionRow.timestamp)


def _apply_window(stmt: Any, start: datetime | None, end: datetime | None) -> Any:
    if start is not None:
        stmt = stmt.where(InteractionRow.timestamp >= start)
    if end is not None:
        stmt = stmt.where(InteractionRow.timestamp < end)
    return stmt


def _row_to_rollup(row: Any) -> Rollup:
    return Rollup(
        key=str(row[0]),
        interactions=row[1],
        input_tokens=row[2] or 0,
        output_tokens=row[3] or 0,
        cache_read_tokens=row[4] or 0,
        cache_write_tokens=row[5] or 0,
        cost_usd=row[6] or 0.0,
        estimated=bool(row[7]),
    )


def _sum_rollups(key: str, rollups: list[Rollup]) -> Rollup:
    return Rollup(
        key=key,
        interactions=sum(r.interactions for r in rollups),
        input_tokens=sum(r.input_tokens for r in rollups),
        output_tokens=sum(r.output_tokens for r in rollups),
        cache_read_tokens=sum(r.cache_read_tokens for r in rollups),
        cache_write_tokens=sum(r.cache_write_tokens for r in rollups),
        cost_usd=sum(r.cost_usd for r in rollups),
        estimated=any(r.estimated for r in rollups),
    )
