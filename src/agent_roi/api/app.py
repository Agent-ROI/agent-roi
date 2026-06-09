"""REST API for the web dashboard.

Thin layer over :class:`Service`. If a built web UI exists at ``web/dist`` it is
served as static files so ``agent-roi serve`` gives a single-URL experience.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent_roi import __version__
from agent_roi.core.platform import platform_label
from agent_roi.core.service import Service
from agent_roi.core.timeframe import parse_since, parse_until
from agent_roi.storage.db import Database


class ConfigUpdateBody(BaseModel):
    classifier: dict[str, object] | None = None
    collectors: dict[str, object] | None = None
    budget: dict[str, object] | None = None


def create_app(service: Service | None = None) -> FastAPI:
    svc: Service = service or Service()
    app = FastAPI(title="Agent-ROI", version=__version__)

    # Allow the React dev server (vite default port) during development.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/api/report")
    def report(
        group_by: str = "topic",
        since: str = "",
        until: str = "",
    ) -> list[dict[str, object]]:
        """Usage/cost grouped by 'topic' | 'tool' | 'model', optionally windowed."""
        if group_by not in Database.VALID_DIMENSIONS:
            raise HTTPException(400, f"Invalid group_by: {group_by}")
        start, end = _window(since, until)
        return [
            r.model_dump() | {"total_tokens": r.total_tokens}
            for r in svc.report(dimension=group_by, start=start, end=end)
        ]

    @app.get("/api/report/topic/{topic}")
    def topic_breakdown(topic: str, since: str = "", until: str = "") -> dict[str, object]:
        """Drill into one topic: split by tool and by model."""
        start, end = _window(since, until)
        bd = svc.topic_breakdown(topic, start=start, end=end)
        return {
            "topic": bd.topic,
            "total": bd.total.model_dump() | {"total_tokens": bd.total.total_tokens},
            "by_tool": [r.model_dump() | {"total_tokens": r.total_tokens} for r in bd.by_tool],
            "by_model": [r.model_dump() | {"total_tokens": r.total_tokens} for r in bd.by_model],
        }

    @app.get("/api/roi")
    def roi(since: str = "", until: str = "") -> list[dict[str, object]]:
        """Cost vs. active development time per topic — the ROI ranking."""
        start, end = _window(since, until)
        return [t.model_dump() for t in svc.roi_by_topic(start=start, end=end)]

    @app.get("/api/composition")
    def composition(since: str = "", until: str = "") -> dict[str, object]:
        """Where tokens went: overhead (cache writes) vs cached vs actual work."""
        start, end = _window(since, until)
        return svc.composition(start=start, end=end)

    @app.get("/api/activity")
    def activity(since: str = "", until: str = "", project: str = "") -> dict[str, object]:
        """What the agent did: tools called, MCP servers, files touched."""
        start, end = _window(since, until)
        return svc.activity(start=start, end=end, project=project or None).model_dump()

    @app.get("/api/sessions")
    def sessions(
        topic: str = "",
        since: str = "",
        until: str = "",
        search: str = "",
    ) -> list[dict[str, object]]:
        """Per-session rows, optionally scoped to one topic and time window."""
        start, end = _window(since, until)
        rows = svc.sessions(
            topic=topic or None,
            start=start,
            end=end,
            search=search or None,
        )
        return [s.model_dump() | {"total_tokens": s.total_tokens} for s in rows]

    @app.get("/api/sessions/{session_id}")
    def session_detail(session_id: str) -> dict[str, object]:
        """One session's aggregate plus the interactions (conversation turns)."""
        detail = svc.session_detail(session_id)
        if detail is None:
            raise HTTPException(404, f"No session {session_id!r}")
        return {
            "session": detail.session.model_dump() | {"total_tokens": detail.session.total_tokens},
            "interactions": [
                i.model_dump() | {"total_tokens": i.total_tokens} for i in detail.interactions
            ],
        }

    @app.get("/api/timeseries")
    def timeseries(
        since: str = "",
        until: str = "",
        granularity: str = "day",
    ) -> dict[str, object]:
        """Token/cost trends plus splits by tool and model."""
        if granularity not in Database.VALID_GRANULARITIES:
            raise HTTPException(400, f"Invalid granularity: {granularity}")
        start, end = _window(since, until)
        bundle = svc.timeseries(start=start, end=end, granularity=granularity)
        return {
            "granularity": granularity,
            "totals": [p.model_dump() | {"total_tokens": p.total_tokens} for p in bundle.totals],
            "by_tool": [r.model_dump() for r in bundle.by_tool],
            "by_model": [r.model_dump() for r in bundle.by_model],
            "tool_keys": bundle.tool_keys,
            "model_keys": bundle.model_keys,
        }

    @app.get("/api/pricing")
    def pricing() -> list[dict[str, object]]:
        """The pricing table behind every cost figure."""
        return [p.model_dump() for p in svc.pricing()]

    @app.get("/api/budget")
    def budget() -> dict[str, object]:
        """Spend so far this day/week/month vs. the configured limits."""
        return svc.budget_status().model_dump()

    @app.get("/api/sources")
    def sources() -> dict[str, object]:
        """Collector diagnostics: which tools were detected and where."""
        return {
            "platform": platform_label(),
            "collectors": [s.model_dump() for s in svc.sources()],
        }

    @app.get("/api/config")
    def get_config() -> dict[str, object]:
        return svc.get_config_info()

    @app.put("/api/config")
    def update_config(body: ConfigUpdateBody) -> dict[str, object]:
        return svc.update_config(
            classifier=body.classifier,
            collectors=body.collectors,
            budget=body.budget,
        )

    @app.post("/api/ingest")
    def ingest() -> dict[str, int]:
        return {"ingested": svc.ingest()}

    @app.post("/api/classify")
    def classify() -> dict[str, int]:
        return {"classified": svc.classify()}

    @app.post("/api/refresh")
    def refresh() -> dict[str, int]:
        """Ingest new logs and re-discover topics in one step."""
        return svc.refresh()

    _mount_web_ui(app)
    return app


def _since(value: str) -> datetime | None:
    try:
        return parse_since(value)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


def _until(value: str) -> datetime | None:
    try:
        return parse_until(value)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


def _window(since: str, until: str) -> tuple[datetime | None, datetime | None]:
    start = _since(since)
    end = _until(until)
    if start is not None and end is not None and start >= end:
        raise HTTPException(400, "since must be before until")
    return start, end


def _mount_web_ui(app: FastAPI) -> None:
    dist = _web_dist()
    if dist is not None:
        app.mount("/", StaticFiles(directory=str(dist), html=True), name="web")


def _web_dist() -> Path | None:
    """Locate the built web UI.

    Prefers the copy bundled inside the installed package (so a pip/uv install
    can serve the dashboard), then falls back to the dev build at ``web/dist``.
    """
    here = Path(__file__).resolve()
    candidates = [
        here.parent.parent / "webui",  # packaged: src/agent_roi/webui
        here.parents[3] / "web" / "dist",  # dev checkout
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None
