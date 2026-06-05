<div align="center">

# Agent-ROI

**Track the cost, usage, and ROI of your AI coding agents — across every tool.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/your-org/agent-roi/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/agent-roi/actions/workflows/ci.yml)

[English](./README.md) · [繁體中文](./README.zh.md)

</div>

---

## What is Agent-ROI?

When you use multiple AI coding tools — Claude Code, Codex CLI, GitHub Copilot, Cursor, and others — your token spend is scattered everywhere and impossible to evaluate. **Agent-ROI** unifies all of it.

It reads the local session logs each tool already writes, uses a **small classifier model** (local Ollama or cloud Haiku) to label *what topic / task* each interaction was about, and then shows you **how many tokens each topic consumed** — so you can measure the **return on investment** of your agents, not just raw token counts.

> The core question Agent-ROI answers: *"For this feature / bug / topic, how many tokens did my agents burn — and was it worth it?"*

## Features

- 🔌 **Tool-agnostic collectors** — parse local logs from Claude Code, Codex CLI, and more (no proxy, no workflow change).
- 🧠 **Topic classification** — a pluggable small model groups interactions by topic so you see cost *per subject*, not per request.
- 💰 **Cost & ROI tracking** — token usage mapped to per-model pricing, aggregated by topic, tool, and time window.
- 🖥️ **CLI** — query and report straight from the terminal.
- 🌐 **Web UI** — a modern React dashboard for trends, breakdowns, and drill-downs.
- 🗄️ **Local-first** — everything stays on your machine (SQLite); cloud classification is opt-in.

## Architecture

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  Collectors  │──▶│  Classifier  │──▶│   Storage    │
│ (parse logs) │   │ (small model)│   │  (SQLite)    │
└──────────────┘   └──────────────┘   └──────┬───────┘
                                             │
                          ┌──────────────────┼──────────────────┐
                          ▼                                      ▼
                   ┌────────────┐                        ┌────────────┐
                   │    CLI     │                        │  REST API  │──▶ Web UI (React)
                   └────────────┘                        └────────────┘
```

See [docs/architecture.md](./docs/architecture.md) for details.

## Quick Start

This project uses [uv](https://docs.astral.sh/uv/) for Python dependency management.

```bash
# Install dependencies into a managed virtualenv
uv sync --extra dev

# Pull a local classifier model (optional, recommended)
ollama pull llama3.2

# Ingest logs from all detected tools
uv run agent-roi ingest

# See a cost breakdown by topic
uv run agent-roi report --by topic

# Launch the web dashboard (API + React UI)
uv run agent-roi serve
```

## Configuration

Agent-ROI looks for config at `~/.config/agent-roi/config.toml`. See [docs/configuration.md](./docs/configuration.md).

```toml
[classifier]
provider = "ollama"     # or "anthropic"
model = "llama3.2"

[collectors]
enabled = ["claude_code", "codex"]
```

## Documentation

| Doc | English | 繁體中文 |
|-----|---------|----------|
| Architecture | [architecture.md](./docs/architecture.md) | [architecture.zh.md](./docs/architecture.zh.md) |
| Configuration | [configuration.md](./docs/configuration.md) | [configuration.zh.md](./docs/configuration.zh.md) |
| Collectors | [collectors.md](./docs/collectors.md) | [collectors.zh.md](./docs/collectors.zh.md) |
| Contributing | [CONTRIBUTING.md](./CONTRIBUTING.md) | [CONTRIBUTING.zh.md](./CONTRIBUTING.zh.md) |

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](./CONTRIBUTING.md) and our [Code of Conduct](./CODE_OF_CONDUCT.md).

## License

[MIT](./LICENSE) © Agent-ROI contributors
