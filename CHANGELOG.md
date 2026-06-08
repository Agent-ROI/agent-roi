# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-06-08

### Added
- `scripts/install.ps1` — one-line installer for Windows (`irm … | iex`); installs `uv` if needed, then `agent-roi`, and prints the installed version.
- README now documents the Windows install command and `agent-roi doctor`.
- **Hermes Agent collector** — reads NousResearch Hermes sessions from its
  SQLite store (`~/.hermes/state.db`), with real (exact) token counts. Emits one
  interaction per session straight from Hermes's exact per-session token columns
  (input/output/cache-read/cache-write/reasoning), so cache reads — which
  dominate agent workloads and are priced ~10× lower — are costed correctly.
  Handles Hermes's multi-provider model ids (`anthropic/…`, `openai/…`,
  `nvidia/…:free`, `gpt-oss:20b`): the provider prefix is stripped and `.`
  normalized to `-` so pricing resolves, with free/local models at $0. Enabled
  by default.
- **Budgets & ROI** — optional daily/weekly/monthly spend limits under `[budget]`
  in config (and the web Settings page). New `agent-roi budget` command and an
  Overview budget panel show spend vs. limit and flag over-budget periods.
- **"vs average" column** on the Topics table — each topic's cost relative to the
  average, so outlier-cost subjects stand out.
- **Token composition view** — splits every token total into three buckets:
  *overhead* (system prompt + tool/MCP schemas, re-sent each turn),
  *cached* (context served from cache), and *work* (actual conversation).
  Shown on the Overview page per-tool and in aggregate.
- **Activity analysis page** — concrete actions behind the cost: which tools and
  MCP servers were called, how often, how many tokens each returned, and which
  files were touched most. Extracted from Claude Code `tool_use` blocks and
  Copilot `toolInvocationSerialized` stream parts.
- **`agent-roi mcp-cost`** — opt-in command that launches each configured stdio
  MCP server, performs the JSON-RPC handshake, reads `tools/list`, and estimates
  the per-turn token overhead of each server's schemas. Never runs during
  `ingest` or `serve`.
- OSS project health files: `SECURITY.md`, Dependabot config, issue-template
  chooser, and YAML issue forms.

### Changed
- Budget/vs-average i18n keys added across all 11 locales.
- Composition and activity i18n keys added across all 11 locales.
- Moved trivial in-function imports to module top level; kept (and documented)
  only the deliberate lazy imports (`uvicorn`, the scikit-learn classifier).
- GitHub Copilot collector rewritten for the new `{kind, k, v}` patch-stream
  log format; previous format is no longer produced by VS Code.

### Fixed
- The `estimated` badge on grouped rows (topic/model totals) is now token-
  weighted: a group reads `estimated` only when estimated interactions are at
  least half of its tokens, instead of flipping if *any* single one was. A
  topic that is 99% exact Hermes plus a couple of estimated Copilot turns now
  correctly reads exact.
- Hermes sessions without a title now fall back to their first user message as
  the classifier summary, so they cluster into topics instead of all landing in
  "uncategorized".
- Hermes Agent now renders with a proper icon and "Hermes Agent" label on the
  Sources and Settings pages (previously a generic fallback badge).
- Language switching broken in i18next v26: `supportedLngs` caused the
  `zh-TW→zh→en` resolution chain to collapse to `[en]`, showing English for
  all non-English locales. Fixed by removing the redundant option.
- 210 missing translations filled across 8 locales (chart titles, nav labels,
  page hints, date range controls).
- `mcp-cost` probe now uses a threading-based reader on Windows instead of
  `select.select()`, which only works on sockets (not pipes) on that platform.
- `mcp-cost` probe now catches `JSONDecodeError` and validates response shapes,
  so a misbehaving server produces an error row instead of crashing the command.

## [0.2.2] - 2026-06-05

### Added
- `agent-roi --version` / `-V` global flag (in addition to the `version` command).
- `install.sh` now prints the installed version when it finishes.

### Changed
- `agent-roi update` now reports the exact version change (`Updated 0.2.0 → 0.2.1`)
  instead of a generic success message.
- Copilot token estimates are far more accurate: input now also accounts for the
  attached file context (editor working set), the accumulated conversation
  history re-sent on each turn, and a fixed system-prompt/tool-definition
  overhead. Previously only the user's typed message was counted, which
  undercounted real input by roughly 20×. Estimates remain flagged `estimated`.

## [0.2.1] - 2026-06-05

### Added
- `agent-roi update` command — checks PyPI and upgrades in place, choosing the
  right installer (`uv tool` vs `pip`) automatically (`--check`, `--pre`).
- `agent-roi version` command.

### Fixed
- `__version__` is now read from the installed distribution metadata instead of a
  hardcoded string that had drifted from `pyproject.toml`.

## [0.2.0] - 2026-06-05

### Added
- Time-aware pricing archive (`pricing.toml`): each model can have multiple price
  epochs keyed by date, so historical interactions are costed with the price that
  was active at their timestamp.
- Cross-tool model coverage — Opus/Sonnet point releases (4.5–4.8, etc.) reached
  via Claude Code, Copilot, Codex, or Gemini CLI now price correctly instead of
  falling back to $0.
- Full-page animated loading overlay during sync, with automatic refresh of all
  pages on completion.
- Client-side pagination for sessions (10/page) and call patterns (15/page).
- Pricing page shows the effective-from date per price epoch.

### Changed
- New i18n keys (`pricing.effectiveFrom`, `pagination.pageOf`) across all 11 locales.

## [0.1.0] - 2026-06-05

### Added
- Initial public release: local-first tracker for token cost and ROI of AI coding
  agents across Claude Code, Codex, Copilot, and Gemini CLI.
- Offline semantic (TF-IDF) session classification, multi-dimension reporting
  (topic / tool / model / project), time windows, and a React web dashboard.
- One-line `install.sh`, published as `agent-roi-tracker` on PyPI.

[Unreleased]: https://github.com/Agent-ROI/agent-roi/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/Agent-ROI/agent-roi/compare/v0.2.2...v0.3.0
[0.2.2]: https://github.com/Agent-ROI/agent-roi/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/Agent-ROI/agent-roi/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/Agent-ROI/agent-roi/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Agent-ROI/agent-roi/releases/tag/v0.1.0
