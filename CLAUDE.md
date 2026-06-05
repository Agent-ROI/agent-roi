# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Backend (Python, managed with `uv`):

```bash
uv sync --extra dev          # install deps incl. dev tools
uv run pytest                # run the full test suite
uv run pytest tests/test_semantic_classifier.py            # single file
uv run pytest tests/test_sessions.py::test_name -x         # single test
uv run ruff check src tests  # lint
uv run mypy                  # type-check (strict; checks src/ only)
```

Frontend (React + Vite, in `web/`, managed with npm):

```bash
cd web
npm install
npm run dev      # Vite dev server on :5173 (CORS-allowed by the API)
npm run build    # tsc -b && vite build
```

Run the app locally:

```bash
uv run agent-roi ingest      # collect logs from enabled tools, then classify
uv run agent-roi report --by tool --since 7d
uv run agent-roi serve       # FastAPI on :8000 (serves built web UI if present)
uv run agent-roi doctor      # which tools were detected, where, and what was found
```

During UI dev run `agent-roi serve` (API on :8000) and `npm run dev` (UI on :5173) together; the API allows the Vite origin via CORS.

## Release builds

The web UI is bundled into the Python package so `agent-roi serve` works after a plain install. The bundle lives at `src/agent_roi/webui/` — it is **gitignored** but listed as a hatch build artifact, so it must be regenerated before building a wheel:

```bash
./scripts/build_web.sh    # npm ci + build, then copy web/dist -> src/agent_roi/webui
uv build                  # wheel/sdist (includes the web UI)
```

## Architecture

A local-first pipeline that turns the session logs AI coding tools already write into a per-topic view of token cost. Data never leaves the machine; everything is in one SQLite file.

```
Collectors ──▶ Storage ──▶ Classifier ──▶ Storage ──▶ Reports (CLI / API / Web)
 (parse logs)   (SQLite)    (semantic)     (topics)
```

`core/service.py` (`Service`) is the single orchestration point wiring collectors → storage → classifier. **Both the CLI (`cli/main.py`, Typer) and the REST API (`api/app.py`, FastAPI) are thin layers over `Service`** — put logic in `Service`, not in either entry point. The API serves the built web UI as static files when present.

### Pipeline stages

1. **Collectors** (`collectors/`) — one `Collector` subclass per tool (Claude Code, Codex, Copilot, Gemini CLI). They parse local logs into normalized `Interaction` objects and are **read-only and idempotent**: each `Interaction.id` is stable, so re-running `ingest` upserts rather than double-counts. Collectors expose `is_available()`, `collect()`, plus diagnostics hooks (`search_paths()`, `count_files()`, `note()`) surfaced by `doctor`.

2. **Storage** (`storage/db.py`, `Database`) — SQLite via SQLAlchemy. Upserts interactions, computes per-interaction USD cost at write time from the pricing table, and does all aggregation (`rollup`, `topic_breakdown`, `sessions`, `session_detail`). Topic labels are stored on rows and cleared/rebuilt by classify.

3. **Classifier** (`classify/`) — **model-free, offline only**. The single provider is `semantic` (`classify/semantic.py`): TF-IDF + cosine-similarity clustering, no model weights, no API keys, no network. It classifies **whole sessions as a unit** (a session = one continuous piece of work) and applies the discovered topic to all of that session's rows, so cost can be aggregated *per subject* rather than per request. `classify()` defaults to `reclassify=True`, which wipes and rebuilds all topics to keep clustering globally consistent.

4. **Reports** — `Service.report(dimension=...)` aggregates by `topic | tool | model | project`, optionally time-windowed (`parse_since` accepts dates or shorthand like `7d`, `24h`, `today`). Drill into a topic with `topic_breakdown` (split by tool and model). Estimated token counts (tools that don't report usage) are badged distinctly from exact ones throughout CLI/API/UI.

### Core domain (`core/`)

`models.py` defines the canonical types — `Interaction` (the unit), `Rollup`, `TopicBreakdown`, `SessionSummary/Detail`, `CollectorStatus`. `pricing.py` is the per-model price table (USD per 1M tokens) behind every cost figure; surfaced verbatim by `agent-roi pricing` for trust. `platform.py` handles cross-platform log discovery (Windows/macOS/Linux + WSL where tools run on the Windows side) — use `find_tool_dirs(...)` from collectors. `config.py` loads `~/.config/agent-roi/config.toml` (override via `AGENT_ROI_CONFIG`); all fields have defaults so the tool works with zero config.

## Adding a collector

1. Create `collectors/<tool>.py` subclassing `Collector`; set `tool` and `name`.
2. Implement `is_available()` and `collect()`; use `core.platform.find_tool_dirs(...)` for log discovery so all platforms work.
3. Register it in `collectors/__init__.py` (and the default `collectors.enabled` list in `core/config.py` if it should be on by default).

See `docs/collectors.md` for the full guide.

## Conventions

- The frontend follows the design system in `design/DESIGN.md`; its tokens are mirrored as CSS variables in `web/src/index.css`. Read it before changing UI styles.
- Docs are bilingual: every `docs/*.md` (and `README.md`, `CONTRIBUTING.md`) has a `*.zh.md` translation — update both when changing docs.
- Python is `strict` mypy and ruff-linted (`E,F,I,UP,B,SIM`, line length 100).
