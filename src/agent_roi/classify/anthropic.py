"""Cloud topic classifier backed by the Anthropic API (Claude Haiku).

Opt-in: only the short ``summary`` of each interaction is sent, never full
prompts. Requires the ``ANTHROPIC_API_KEY`` environment variable.
"""

from __future__ import annotations

import os

import httpx

from agent_roi.classify.base import SYSTEM_PROMPT, Classifier

_DEFAULT_TOPIC = "uncategorized"
_API_URL = "https://api.anthropic.com/v1/messages"


class AnthropicClassifier(Classifier):
    def __init__(self, model: str = "claude-haiku-4-5", timeout: float = 30.0) -> None:
        self.model = model
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set; required for the anthropic classifier."
            )
        self._client = httpx.Client(
            timeout=timeout,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )

    def classify(self, summary: str) -> str:
        summary = summary.strip()
        if not summary:
            return _DEFAULT_TOPIC
        try:
            resp = self._client.post(
                _API_URL,
                json={
                    "model": self.model,
                    "max_tokens": 20,
                    "temperature": 0,
                    "system": SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": summary}],
                },
            )
            resp.raise_for_status()
            content = resp.json()["content"][0]["text"]
            return _normalize(content)
        except (httpx.HTTPError, KeyError, IndexError, ValueError):
            return _DEFAULT_TOPIC


def _normalize(raw: str) -> str:
    topic = raw.strip().strip("\"'.").lower()
    topic = topic.splitlines()[0] if topic else ""
    return " ".join(topic.split()[:5]) or _DEFAULT_TOPIC
