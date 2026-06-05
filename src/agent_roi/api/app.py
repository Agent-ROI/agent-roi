"""REST API for the web dashboard.

Thin layer over :class:`Service`. If a built web UI exists at ``web/dist`` it is
served as static files so ``agent-roi serve`` gives a single-URL experience.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from agent_roi import __version__
from agent_roi.core.service import Service


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

    @app.get("/api/report/topics")
    def report_topics() -> list[dict[str, object]]:
        return [
            r.model_dump() | {"total_tokens": r.total_tokens}
            for r in svc.report_by_topic()
        ]

    @app.post("/api/ingest")
    def ingest() -> dict[str, int]:
        return {"ingested": svc.ingest()}

    @app.post("/api/classify")
    def classify() -> dict[str, int]:
        return {"classified": svc.classify()}

    _mount_web_ui(app)
    return app


def _mount_web_ui(app: FastAPI) -> None:
    dist = Path(__file__).resolve().parents[3] / "web" / "dist"
    if dist.is_dir():
        app.mount("/", StaticFiles(directory=str(dist), html=True), name="web")
