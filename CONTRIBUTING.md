# Contributing to Agent-ROI

Thanks for your interest in improving Agent-ROI! This guide gets you set up and
explains how we work.

> 繁體中文版：[CONTRIBUTING.zh.md](./CONTRIBUTING.zh.md)

## Development setup

Agent-ROI has a Python backend (managed with [uv](https://docs.astral.sh/uv/))
and a React frontend (managed with npm).

```bash
# Backend
uv sync --extra dev
uv run agent-roi serve   # API on :8000 (also serves the built web UI)

uv run pytest            # run tests
uv run ruff check src    # lint
uv run mypy              # type-check

# Frontend (only needed when working on the UI)
cd web
npm install
npm run dev              # Vite dev server on :5173 (proxies API calls to :8000)
npm run build            # production build
```

Run `agent-roi serve` and `npm run dev` together when developing the UI. For
everything else, `agent-roi serve` alone is enough.

## Project layout

```
src/agent_roi/
  collectors/   # parse each tool's local logs -> Interaction
  classify/     # model-free semantic topic discovery (TF-IDF + cosine clustering)
  storage/      # SQLite persistence + aggregation
  core/         # domain models, config, pricing, platform, service
  api/          # FastAPI REST layer
  cli/          # Typer command-line interface
web/            # React + Vite dashboard
design/         # DESIGN.md design system (Linear) — read before UI changes
docs/           # English docs (*.md) + Chinese translations (*.zh.md)
tests/          # pytest suite
```

The frontend follows the design system in [`design/DESIGN.md`](./design/DESIGN.md)
(Notion). Its tokens are mirrored as CSS variables in `web/src/index.css`; read
it before changing UI styles so the look stays consistent.

### Building a release

The web UI is bundled into the Python package so `agent-roi serve` works after a
plain install. Before building a wheel:

```bash
./scripts/build_web.sh   # builds web/ and copies it into src/agent_roi/webui
uv build                 # produces the wheel/sdist (includes the web UI)
```

## Adding a collector

A new tool integration is just a `Collector` subclass:

1. Create `src/agent_roi/collectors/<tool>.py` subclassing `Collector`.
2. Implement `is_available()` and `collect()` (see existing collectors).
3. Use `core.platform.find_tool_dirs(...)` to locate logs so Windows/macOS/Linux
   and WSL all work.
4. Register it in `collectors/__init__.py`.
5. Add a fixture-based test under `tests/`.

See [docs/collectors.md](./docs/collectors.md) for the full guide.

## Pull requests

- Keep PRs focused; one logical change per PR.
- Add or update tests for behavior changes.
- Run `uv run ruff check src tests` and `uv run pytest` before pushing.
- Update both the English doc and its `.zh.md` translation when changing docs.

## Code of Conduct

By participating you agree to our [Code of Conduct](./CODE_OF_CONDUCT.md).
