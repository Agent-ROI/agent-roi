"""Configuration loading for Agent-ROI.

Config is read from ``~/.config/agent-roi/config.toml`` (override with the
``AGENT_ROI_CONFIG`` env var). Every field has a sensible default so the tool
works out of the box with zero configuration.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from platformdirs import user_config_dir, user_data_dir
from pydantic import BaseModel

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

APP_NAME = "agent-roi"


class ClassifierConfig(BaseModel):
    # Only "semantic" exists: model-free, offline topic discovery.
    provider: str = "semantic"
    # Cosine similarity at/above which two sessions are grouped into the same
    # topic. Higher = stricter (more, smaller topics); lower = broader topics.
    similarity_threshold: float = 0.18
    # Number of distinctive terms used to name each discovered topic.
    label_terms: int = 3


class CollectorsConfig(BaseModel):
    enabled: list[str] = ["claude_code", "codex", "copilot", "gemini", "hermes"]


class BudgetConfig(BaseModel):
    """Optional spend limits (USD) per rolling period.

    All limits default to ``None`` (no budget). When set, the dashboard shows
    spend against the limit and flags when a period is over budget. This is what
    turns raw cost tracking into a real ROI signal — "am I within budget for
    this day / week / month?"
    """

    daily_usd: float | None = None
    weekly_usd: float | None = None
    monthly_usd: float | None = None


class Config(BaseModel):
    classifier: ClassifierConfig = ClassifierConfig()
    collectors: CollectorsConfig = CollectorsConfig()
    budget: BudgetConfig = BudgetConfig()
    db_path: Path = Path(user_data_dir(APP_NAME)) / "agent_roi.db"

    @classmethod
    def load(cls) -> Config:
        path = config_path()
        if not path.exists():
            return cls()
        with path.open("rb") as f:
            data = tomllib.load(f)
        return cls.model_validate(data)

    def save(self) -> None:
        path = config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        lines: list[str] = []
        lines.append(f'db_path = "{self.db_path.as_posix()}"')
        lines.append("")
        lines.append("[classifier]")
        lines.append(f'provider = "{self.classifier.provider}"')
        lines.append(f"similarity_threshold = {self.classifier.similarity_threshold}")
        lines.append(f"label_terms = {self.classifier.label_terms}")
        lines.append("")
        lines.append("[collectors]")
        enabled = ", ".join(f'"{e}"' for e in self.collectors.enabled)
        lines.append(f"enabled = [{enabled}]")
        lines.append("")
        lines.append("[budget]")
        # Only write limits that are set; TOML has no null, so omit None values.
        for key, value in (
            ("daily_usd", self.budget.daily_usd),
            ("weekly_usd", self.budget.weekly_usd),
            ("monthly_usd", self.budget.monthly_usd),
        ):
            if value is not None:
                lines.append(f"{key} = {value}")
        lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")


def config_path() -> Path:
    override = os.environ.get("AGENT_ROI_CONFIG")
    if override:
        return Path(override)
    return Path(user_config_dir(APP_NAME)) / "config.toml"
