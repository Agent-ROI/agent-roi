"""High-level orchestration used by both the CLI and the API.

Keeps the wiring of collectors -> storage -> classifier in one place so the CLI
and REST layers stay thin.
"""

from __future__ import annotations

from agent_roi.classify import get_classifier
from agent_roi.collectors import get_collectors
from agent_roi.core.config import Config
from agent_roi.core.models import TopicRollup
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
            total += self.db.upsert_many(collector.collect())
        return total

    def classify(self, limit: int | None = None) -> int:
        """Assign topics to interactions that don't have one yet.

        Returns the number newly classified.
        """
        rows = self.db.unclassified(limit=limit)
        if not rows:
            return 0
        classifier = get_classifier(self.config.classifier)
        for row in rows:
            topic = classifier.classify(row.summary)
            self.db.set_topic(row.id, topic)
        return len(rows)

    def report_by_topic(self) -> list[TopicRollup]:
        return self.db.rollup_by_topic()
