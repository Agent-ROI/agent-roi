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


def platform_label() -> str:
    """A short human-readable label for the current OS (for diagnostics)."""
    names = {"darwin": "macOS", "win32": "Windows", "linux": "Linux"}
    base = names.get(sys.platform, sys.platform)
    return f"{base} (WSL)" if is_wsl() else base


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


def vscode_user_dirs() -> list[Path]:
    """Locate VS Code ``User`` directories across platforms (and forks/insiders).

    VS Code stores per-user state (including chat sessions) under different paths
    on each OS. We return every existing match so collectors can search them.
    """
    # Path of the "User" dir relative to each home, per platform.
    rel_by_platform: dict[str, list[tuple[str, ...]]] = {
        "darwin": [("Library", "Application Support", "{app}", "User")],
        "win32": [("AppData", "Roaming", "{app}", "User")],
        "linux": [(".config", "{app}", "User")],
    }
    # On WSL we also want the Windows-side VS Code, which lives under AppData.
    if is_wsl():
        rel_by_platform["linux"].append(("AppData", "Roaming", "{app}", "User"))

    apps = ["Code", "Code - Insiders", "VSCodium", "Cursor"]
    templates = rel_by_platform.get(sys.platform, rel_by_platform["linux"])

    found: list[Path] = []
    for home in home_candidates():
        for template in templates:
            for app in apps:
                parts = tuple(p.replace("{app}", app) for p in template)
                candidate = home.joinpath(*parts)
                if candidate.is_dir():
                    found.append(candidate)
    return found
