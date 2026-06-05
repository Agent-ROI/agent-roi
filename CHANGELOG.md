# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `scripts/install.ps1` — one-line installer for Windows (`irm … | iex`); installs `uv` if needed, then `agent-roi`, and prints the installed version.
- README now documents the Windows install command and `agent-roi doctor`.

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

[Unreleased]: https://github.com/Agent-ROI/agent-roi/compare/v0.2.2...HEAD
[0.2.2]: https://github.com/Agent-ROI/agent-roi/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/Agent-ROI/agent-roi/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/Agent-ROI/agent-roi/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Agent-ROI/agent-roi/releases/tag/v0.1.0
