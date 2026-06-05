"""SQLite storage for interactions, with upsert + topic aggregation.

Local-first: a single SQLite file holds every collected interaction. Writes are
idempotent on the interaction ``id`` so re-running ingest never double-counts.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import String, create_engine, func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from agent_roi.core.models import Interaction, Rollup, TopicBreakdown
from agent_roi.core.pricing import cost_of


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
        }
        with self.engine.begin() as conn:
            rows = conn.exec_driver_sql("PRAGMA table_info(interactions)").fetchall()
            existing = {row[1] for row in rows}
            for column, ddl in expected.items():
                if column not in existing:
                    conn.exec_driver_sql(
                        f"ALTER TABLE interactions ADD COLUMN {column} {ddl}"
                    )

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

    # Columns that can be used as a grouping dimension.
    _DIMENSIONS = {
        "topic": func.coalesce(InteractionRow.topic, "uncategorized"),
        "tool": InteractionRow.tool,
        "model": InteractionRow.model,
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
