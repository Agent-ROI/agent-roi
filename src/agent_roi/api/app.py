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

from agent_roi import __version__
from agent_roi.core.service import Service
from agent_roi.core.timeframe import parse_since


def create_app(service: Service | None = None) -> FastAPI:
    svc: Service = service or Service()
    app = FastAPI(title="Agent-ROI", version=__version__)

    # Allow the React dev server (vite default port) during development.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/api/report")
    def report(
        group_by: str = "topic",
        since: str = "",
    ) -> list[dict[str, object]]:
        """Usage/cost grouped by 'topic' | 'tool' | 'model', optionally windowed."""
        if group_by not in ("topic", "tool", "model"):
            raise HTTPException(400, f"Invalid group_by: {group_by}")
        start = _since(since)
        return [
            r.model_dump() | {"total_tokens": r.total_tokens}
            for r in svc.report(dimension=group_by, start=start)
        ]

    @app.get("/api/report/topic/{topic}")
    def topic_breakdown(topic: str, since: str = "") -> dict[str, object]:
        """Drill into one topic: split by tool and by model."""
        start = _since(since)
        bd = svc.topic_breakdown(topic, start=start)
        return {
            "topic": bd.topic,
            "total": bd.total.model_dump() | {"total_tokens": bd.total.total_tokens},
            "by_tool": [r.model_dump() | {"total_tokens": r.total_tokens} for r in bd.by_tool],
            "by_model": [r.model_dump() | {"total_tokens": r.total_tokens} for r in bd.by_model],
        }

    @app.get("/api/pricing")
    def pricing() -> list[dict[str, object]]:
        """The pricing table behind every cost figure."""
        return [p.model_dump() for p in svc.pricing()]

    @app.post("/api/ingest")
    def ingest() -> dict[str, int]:
        return {"ingested": svc.ingest()}

    @app.post("/api/classify")
    def classify() -> dict[str, int]:
        return {"classified": svc.classify()}

    _mount_web_ui(app)
    return app


def _since(value: str) -> datetime | None:
    try:
        return parse_since(value)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


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
