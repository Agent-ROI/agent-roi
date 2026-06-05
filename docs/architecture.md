# Architecture

> 繁體中文版：[architecture.zh.md](./architecture.zh.md)

Agent-ROI is a local-first pipeline that turns the logs your AI coding tools
already write into a per-topic view of token cost and ROI.

## Pipeline

```
Collectors ──▶ Storage ──▶ Classifier ──▶ Storage ──▶ Reports (CLI / API / Web)
 (parse logs)   (SQLite)    (semantic)     (topics)
```

1. **Collectors** read each tool's local session logs and normalize every
   request/response turn into an `Interaction` (tool, session, timestamp, model,
   token counts, short summary). They are read-only — they never touch the
   original logs.
2. **Storage** upserts interactions into SQLite, keyed by a stable id so
   re-running ingest is idempotent (no double counting). Per-interaction USD cost
   is computed at write time from the pricing table.
3. **Classifier** looks at whole *sessions* together and groups similar ones into
   a shared **topic** (e.g. `auth jwt session`, `ci pipeline test`). It uses
   TF-IDF vectors and cosine similarity — no model, no API key, fully offline.
   This is what lets cost be aggregated *per subject* instead of per request.
4. **Reports** aggregate by topic and are exposed through the CLI, a REST API,
   and a React web dashboard.

## Components

| Layer | Module | Responsibility |
|-------|--------|----------------|
| Collectors | `agent_roi.collectors` | Parse tool logs → `Interaction` |
| Classifier | `agent_roi.classify` | Model-free semantic topic discovery |
| Storage | `agent_roi.storage` | SQLite persistence + aggregation |
| Core | `agent_roi.core` | Models, config, pricing, platform, service |
| API | `agent_roi.api` | FastAPI REST layer + static web hosting |
| CLI | `agent_roi.cli` | Typer command-line interface |
| Web | `web/` | React + Vite dashboard |

## Key design decisions

- **Local-first.** All data lives in a single SQLite file on the user's machine.
  Classification runs entirely offline and never sends any data externally.
- **Tool-agnostic via collectors.** Supporting a new tool means writing one
  `Collector` subclass — no changes to the rest of the system.
- **Model-free classifier.** Topics are discovered from the session text itself
  using TF-IDF vectors and cosine-similarity clustering. No model weights, no API
  keys, no extra dependencies — it works out of the box.
- **Idempotent ingest.** Stable interaction ids mean you can run `ingest` as
  often as you like; classifications are preserved across re-ingests.
- **Cross-platform.** Log discovery handles Windows, macOS, Linux, and WSL
  (where tools may run on the Windows side). See
  [`core/platform.py`](../src/agent_roi/core/platform.py).

## Data model

The canonical unit is `Interaction`. Aggregations produce `TopicRollup` objects.
See [`core/models.py`](../src/agent_roi/core/models.py).
