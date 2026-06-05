"""SQLite storage for interactions, with upsert + topic aggregation.

Local-first: a single SQLite file holds every collected interaction. Writes are
idempotent on the interaction ``id`` so re-running ingest never double-counts.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from sqlalchemy import String, create_engine, func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from agent_roi.core.models import Interaction, TopicRollup
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


class Database:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{path}")
        Base.metadata.create_all(self.engine)

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

    def rollup_by_topic(self) -> list[TopicRollup]:
        with Session(self.engine) as session:
            topic_col = func.coalesce(InteractionRow.topic, "uncategorized")
            stmt = (
                select(
                    topic_col.label("topic"),
                    func.count().label("interactions"),
                    func.sum(InteractionRow.input_tokens),
                    func.sum(InteractionRow.output_tokens),
                    func.sum(InteractionRow.cache_read_tokens),
                    func.sum(InteractionRow.cache_write_tokens),
                    func.sum(InteractionRow.cost_usd),
                )
                .group_by(topic_col)
                .order_by(func.sum(InteractionRow.cost_usd).desc())
            )
            rollups = []
            for row in session.execute(stmt):
                rollups.append(
                    TopicRollup(
                        topic=row[0],
                        interactions=row[1],
                        input_tokens=row[2] or 0,
                        output_tokens=row[3] or 0,
                        cache_read_tokens=row[4] or 0,
                        cache_write_tokens=row[5] or 0,
                        cost_usd=row[6] or 0.0,
                    )
                )
            return rollups
