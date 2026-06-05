"""Cross-platform helpers for locating tool log directories.

Agent-ROI runs on Windows, macOS, and Linux. The tricky case is WSL: a user may
run their AI tools from Windows (logs under ``C:\\Users\\<name>``, visible from
WSL at ``/mnt/c/Users/<name>``) while running Agent-ROI from inside the Linux
distro. We therefore search several candidate roots and use whichever exist.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def is_wsl() -> bool:
    """Detect Windows Subsystem for Linux."""
    if not sys.platform.startswith("linux"):
        return False
    return "microsoft" in _osrelease()


def _osrelease() -> str:
    try:
        return Path("/proc/sys/kernel/osrelease").read_text().lower()
    except OSError:
        return ""


def home_candidates() -> list[Path]:
    """Home directories worth searching, most-specific first.

    Always includes the native home. Under WSL it also includes the mounted
    Windows user profile(s), since tools are commonly run from the Windows side.
    """
    candidates: list[Path] = [Path.home()]
    if is_wsl():
        candidates.extend(_windows_homes_from_wsl())
    # De-duplicate while preserving order.
    seen: set[Path] = set()
    result: list[Path] = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            result.append(c)
    return result


def _windows_homes_from_wsl() -> list[Path]:
    """Best-effort discovery of Windows user homes from inside WSL."""
    homes: list[Path] = []
    users_dir = Path("/mnt/c/Users")
    if not users_dir.is_dir():
        return homes
    # Prefer the matching username, but include all real profiles as a fallback.
    win_user = os.environ.get("WIN_USER") or os.environ.get("USER")
    skip = {"Default", "Default User", "Public", "All Users", "desktop.ini"}
    for entry in users_dir.iterdir():
        if entry.name in skip or not entry.is_dir():
            continue
        if win_user and entry.name.lower() == win_user.lower():
            homes.insert(0, entry)
        else:
            homes.append(entry)
    return homes


def find_tool_dirs(*relative_parts: str) -> list[Path]:
    """Return existing directories at ``<home>/<relative_parts>`` across all
    candidate homes (native + WSL-mounted Windows)."""
    found: list[Path] = []
    for home in home_candidates():
        candidate = home.joinpath(*relative_parts)
        if candidate.is_dir():
            found.append(candidate)
    return found
