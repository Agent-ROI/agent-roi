#!/usr/bin/env bash
# Agent-ROI one-line installer.
#
#   curl -LsSf https://raw.githubusercontent.com/Agent-ROI/agent-roi/main/scripts/install.sh | sh
#
# Installs `uv` if needed, then installs Agent-ROI as a uv tool.
# Works on macOS, Linux, and WSL.
set -eu

REPO="${AGENT_ROI_REPO:-https://github.com/Agent-ROI/agent-roi}"
PACKAGE="agent-roi-tracker"
if [ "${AGENT_ROI_FROM_GIT:-0}" = "1" ]; then
  PACKAGE="git+${REPO}.git"
fi

# ── colours ─────────────────────────────────────────────────────────────────
BOLD='\033[1m'
DIM='\033[2m'
BLUE='\033[1;34m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
RESET='\033[0m'

# Disable colour when not writing to a terminal (piped to sh, redirected, etc.)
if [ ! -t 1 ]; then
  BOLD=''; DIM=''; BLUE=''; GREEN=''; YELLOW=''; RED=''; RESET=''
fi

step()  { printf "${BLUE}  →${RESET} ${BOLD}%s${RESET}\n" "$1"; }
ok()    { printf "${GREEN}  ✓${RESET} %s\n" "$1"; }
warn()  { printf "${YELLOW}  !${RESET} %s\n" "$1"; }
err()   { printf "${RED}  ✗${RESET} %s\n" "$1" >&2; }

# Spinner — runs in background, killed when the calling command finishes.
_spin_pid=''
spin_start() {
  # Only animate when attached to a terminal.
  [ -t 1 ] || return 0
  local msg="$1"
  local frames='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
  (
    i=0
    while true; do
      frame="${frames:$((i % ${#frames})):1}"
      printf "\r${BLUE}  %s${RESET}  ${DIM}%s${RESET}  " "$frame" "$msg"
      sleep 0.1
      i=$((i + 1))
    done
  ) &
  _spin_pid=$!
  disown "$_spin_pid" 2>/dev/null || true
}
spin_stop() {
  if [ -n "$_spin_pid" ] && kill -0 "$_spin_pid" 2>/dev/null; then
    kill "$_spin_pid" 2>/dev/null || true
    wait "$_spin_pid" 2>/dev/null || true
    printf "\r\033[2K"  # clear spinner line
  fi
  _spin_pid=''
}
# Always clean up spinner on exit.
trap 'spin_stop' EXIT

# ── banner ───────────────────────────────────────────────────────────────────
printf "\n"
printf "${BOLD}  Agent-ROI${RESET}  ${DIM}AI coding cost & ROI tracker${RESET}\n"
printf "${DIM}  ─────────────────────────────────────────${RESET}\n\n"

# ── 1. Ensure uv ─────────────────────────────────────────────────────────────
if ! command -v uv >/dev/null 2>&1; then
  step "Installing uv (Python tool manager)"
  spin_start "Downloading uv…"
  if curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1; then
    spin_stop
    ok "uv installed"
  else
    spin_stop
    err "uv installation failed — install manually: https://docs.astral.sh/uv/"
    exit 1
  fi
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

if ! command -v uv >/dev/null 2>&1; then
  err "uv not found after install — you may need to restart your shell"
  exit 1
fi

# ── 2. Install Agent-ROI ─────────────────────────────────────────────────────
step "Installing Agent-ROI"
spin_start "Fetching ${PACKAGE}…"
if uv tool install --upgrade --force "$PACKAGE" >/dev/null 2>&1; then
  spin_stop
  ok "agent-roi installed"
else
  spin_stop
  err "Installation failed — re-running with output:"
  uv tool install --upgrade --force "$PACKAGE"
  exit 1
fi

printf "\n"
printf "${DIM}  ─────────────────────────────────────────${RESET}\n"

# ── 3. Next steps ────────────────────────────────────────────────────────────
if command -v agent-roi >/dev/null 2>&1; then
  printf "${GREEN}${BOLD}  Done!${RESET}  Run:\n\n"
  printf "    ${BOLD}agent-roi ingest${RESET}   ${DIM}# collect logs from your AI tools${RESET}\n"
  printf "    ${BOLD}agent-roi serve${RESET}    ${DIM}# open the web dashboard${RESET}\n"
else
  printf "${GREEN}${BOLD}  Done!${RESET}  Restart your shell (or run ${BOLD}uv tool update-shell${RESET}), then:\n\n"
  printf "    ${BOLD}agent-roi ingest${RESET}   ${DIM}# collect logs from your AI tools${RESET}\n"
  printf "    ${BOLD}agent-roi serve${RESET}    ${DIM}# open the web dashboard${RESET}\n"
fi
printf "\n"
