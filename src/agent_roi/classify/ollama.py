"""Local topic classifier backed by Ollama.

Runs entirely on the user's machine, so interaction summaries never leave it.
Requires a running Ollama server (``ollama serve``) and a pulled model.
"""

from __future__ import annotations

import httpx

from agent_roi.classify.base import SYSTEM_PROMPT, Classifier

_DEFAULT_TOPIC = "uncategorized"


class OllamaClassifier(Classifier):
    def __init__(
        self,
        model: str = "llama3.2",
        host: str = "http://localhost:11434",
        timeout: float = 30.0,
    ) -> None:
        self.model = model
        self.host = host.rstrip("/")
        self._client = httpx.Client(timeout=timeout)

    def classify(self, summary: str) -> str:
        summary = summary.strip()
        if not summary:
            return _DEFAULT_TOPIC
        try:
            resp = self._client.post(
                f"{self.host}/api/chat",
                json={
                    "model": self.model,
                    "stream": False,
                    "options": {"temperature": 0},
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": summary},
                    ],
                },
            )
            resp.raise_for_status()
            content = resp.json()["message"]["content"]
            return _normalize(content)
        except (httpx.HTTPError, KeyError, ValueError):
            return _DEFAULT_TOPIC


def _normalize(raw: str) -> str:
    topic = raw.strip().strip("\"'.").lower()
    # Keep it to the first line and a few words.
    topic = topic.splitlines()[0] if topic else ""
    words = topic.split()
    return " ".join(words[:5]) or _DEFAULT_TOPIC
