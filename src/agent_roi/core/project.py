"""Derive a coarse 'project' label from a working directory.

This is only a *grouping hint* (the semantic topic still comes from the
classifier). We map a cwd to the nearest meaningful root so that subfolders of
one repo (``/repo`` and ``/repo/web``) collapse to the same project. Because
collectors run over historical logs, the original directory may no longer exist,
so we can't always stat ``.git`` — we fall back to a path heuristic.
"""

from __future__ import annotations

from pathlib import Path

# Workspace parents whose immediate child is the actual project (e.g. the folder
# under ~/Desktop or ~/projects is the project, not Desktop itself).
_WORKSPACE_PARENTS = {
    "desktop",
    "documents",
    "projects",
    "code",
    "src",
    "repos",
    "repo",
    "dev",
    "work",
    "workspaces",
}


def project_for(cwd: str) -> str:
    """Return a short project label for a working directory.

    Empty or root cwds yield ``"unknown"``.
    """
    if not cwd or cwd in ("/", "."):
        return "unknown"

    path = Path(cwd)

    # If the directory still exists, prefer a real git root.
    git_root = _git_root(path)
    if git_root is not None:
        return git_root.name

    # Otherwise: walk up until the parent looks like a workspace container, and
    # take the child of that container as the project root.
    parts = [p for p in path.parts if p not in ("/", "")]
    for i, part in enumerate(parts):
        if part.lower() in _WORKSPACE_PARENTS and i + 1 < len(parts):
            return parts[i + 1]

    # Fall back to the last path segment.
    return path.name or "unknown"


def _git_root(path: Path) -> Path | None:
    try:
        for candidate in (path, *path.parents):
            if (candidate / ".git").exists():
                return candidate
    except OSError:
        return None
    return None
