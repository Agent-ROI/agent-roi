#!/usr/bin/env bash
# Agent-ROI one-line installer.
#
#   curl -LsSf https://raw.githubusercontent.com/Agent-ROI/agent-roi/main/scripts/install.sh | sh
#
# It installs `uv` if needed, then installs Agent-ROI as a uv tool so the
# `agent-roi` command is available on your PATH. Works on macOS, Linux, and WSL.
set -eu

REPO="${AGENT_ROI_REPO:-https://github.com/Agent-ROI/agent-roi}"
# Install from PyPI by default; set AGENT_ROI_FROM_GIT=1 to install from source.
PACKAGE="agent-roi-tracker"
if [ "${AGENT_ROI_FROM_GIT:-0}" = "1" ]; then
  PACKAGE="git+${REPO}.git"
fi

info() { printf '\033[1;34m==>\033[0m %s\n' "$1"; }
err() { printf '\033[1;31merror:\033[0m %s\n' "$1" >&2; }

# 1. Ensure uv is installed (it's the fastest way to get an isolated tool env).
if ! command -v uv >/dev/null 2>&1; then
  info "Installing uv (Python tool manager)…"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # uv installs to ~/.local/bin or ~/.cargo/bin; make it visible for this run.
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

if ! command -v uv >/dev/null 2>&1; then
  err "uv installation failed. Install it manually: https://docs.astral.sh/uv/"
  exit 1
fi

# 2. Install (or upgrade) Agent-ROI as a uv tool.
info "Installing Agent-ROI ($PACKAGE)…"
uv tool install --upgrade "$PACKAGE"

# 3. Report.
if command -v agent-roi >/dev/null 2>&1; then
  info "Installed. Try:  agent-roi ingest && agent-roi serve"
else
  info "Installed. You may need to restart your shell, or run: uv tool update-shell"
  info "Then try:  agent-roi ingest && agent-roi serve"
fi
