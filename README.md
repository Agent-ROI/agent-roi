<div align="center">

<img src="docs/assets/logo.jpg" alt="Agent-ROI" width="280" />

# Agent-ROI

**Track the cost, usage, and ROI of your AI coding agents — across every tool.**

[![CI](https://github.com/Agent-ROI/agent-roi/actions/workflows/ci.yml/badge.svg)](https://github.com/Agent-ROI/agent-roi/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/agent-roi-tracker?label=PyPI)](https://pypi.org/project/agent-roi-tracker/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[English](./README.md) · [繁體中文](./README.zh.md)

</div>

---

When you use multiple AI coding tools — Claude Code, Codex CLI, GitHub Copilot, Cursor, Gemini CLI — your token spend is scattered and impossible to evaluate. **Agent-ROI** reads the local logs each tool already writes, uses a **model-free semantic classifier** to discover *what topic each session was about*, and shows you how many tokens each topic consumed.

> *"For this feature / bug fix / topic — how many tokens did my agents burn, and was it worth it?"*

## Install

**macOS / Linux / WSL:**

```bash
curl -LsSf https://raw.githubusercontent.com/Agent-ROI/agent-roi/main/scripts/install.sh | sh
```

**Windows (PowerShell):**

```powershell
irm https://raw.githubusercontent.com/Agent-ROI/agent-roi/main/scripts/install.ps1 | iex
```

Installs `uv` if needed, then the `agent-roi` command. No Python version management needed.

<details>
<summary>Other install methods</summary>

```bash
pipx install agent-roi-tracker
# or
uv tool install agent-roi-tracker
```

Set `AGENT_ROI_FROM_GIT=1` before running the install script to get the latest from source.

</details>

## Quick start

```bash
agent-roi ingest                          # parse logs from all detected tools
agent-roi report --by topic --since 7d   # cost per topic this week
agent-roi serve                           # web dashboard on http://127.0.0.1:8000
agent-roi doctor                          # see which tools were detected and why
agent-roi mcp-cost                        # estimate each MCP server's per-turn overhead
```

## Features

| | |
|---|---|
| **Tool-agnostic** | Reads local logs from Claude Code, Codex CLI, GitHub Copilot, Gemini CLI, and Hermes Agent — no proxy, no workflow change |
| **Topic classification** | Model-free TF-IDF + cosine-similarity clustering; runs fully offline, no API keys |
| **Cost & ROI** | Token usage mapped to per-model pricing, aggregated by **topic, tool, or model**, over any time window |
| **Where tokens go** | Splits every total into **overhead** (system prompt + tool + MCP schemas), **cached** re-sent context, and actual **work** — so you see what your tokens are really spent on |
| **Activity analysis** | Concrete actions behind the cost: which tools and **MCP servers** were called, how often, how many tokens each returned, and which files were touched most |
| **MCP cost** | `agent-roi mcp-cost` estimates each MCP server's per-turn schema overhead (opt-in; launches the servers to read their tool list) |
| **Drill-down** | Click any topic to see which tools and models contributed; estimated vs exact counts clearly badged |
| **Local-first** | Everything in one SQLite file; data never leaves your machine |

## Supported tools

| Tool | Status |
|------|--------|
| Claude Code | ✅ |
| Codex CLI | ✅ |
| GitHub Copilot | ✅ |
| Gemini CLI | ✅ |
| Hermes Agent | ✅ |
| Cursor | 🔜 |

## Architecture

```
Collectors ──▶ Storage ──▶ Classifier ──▶ Storage ──▶ CLI / API / Web
(parse logs)   (SQLite)    (semantic)     (topics)
```

Both the CLI (`typer`) and REST API (`fastapi`) are thin shells over a single `Service` class.
See [docs/architecture.md](./docs/architecture.md) for details.

## Configuration

`~/.config/agent-roi/config.toml` (all fields optional — works with zero config):

```toml
[classifier]
similarity_threshold = 0.18   # higher = more, smaller topics
label_terms = 3

[collectors]
enabled = ["claude_code", "codex", "copilot", "gemini", "hermes"]
```

See [docs/configuration.md](./docs/configuration.md).

## Documentation

| | English | 繁體中文 |
|--|---------|----------|
| Architecture | [architecture.md](./docs/architecture.md) | [architecture.zh.md](./docs/architecture.zh.md) |
| Configuration | [configuration.md](./docs/configuration.md) | [configuration.zh.md](./docs/configuration.zh.md) |
| Collectors | [collectors.md](./docs/collectors.md) | [collectors.zh.md](./docs/collectors.zh.md) |
| Contributing | [CONTRIBUTING.md](./CONTRIBUTING.md) | [CONTRIBUTING.zh.md](./CONTRIBUTING.zh.md) |

## Contributing

Read [CONTRIBUTING.md](./CONTRIBUTING.md). Local dev uses `uv` for the backend and Vite for the frontend.

## License

[MIT](./LICENSE) © Agent-ROI contributors
