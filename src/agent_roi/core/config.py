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
    import tomli as tomllib  # type: ignore[import-not-found]

APP_NAME = "agent-roi"


class ClassifierConfig(BaseModel):
    provider: str = "ollama"  # "ollama" | "anthropic"
    model: str = "llama3.2"
    # Max interactions sent to the classifier in one batch.
    batch_size: int = 20


class CollectorsConfig(BaseModel):
    enabled: list[str] = ["claude_code", "codex", "copilot"]


class Config(BaseModel):
    classifier: ClassifierConfig = ClassifierConfig()
    collectors: CollectorsConfig = CollectorsConfig()
    db_path: Path = Path(user_data_dir(APP_NAME)) / "agent_roi.db"

    @classmethod
    def load(cls) -> Config:
        path = _config_path()
        if not path.exists():
            return cls()
        with path.open("rb") as f:
            data = tomllib.load(f)
        return cls.model_validate(data)


def _config_path() -> Path:
    override = os.environ.get("AGENT_ROI_CONFIG")
    if override:
        return Path(override)
    return Path(user_config_dir(APP_NAME)) / "config.toml"
