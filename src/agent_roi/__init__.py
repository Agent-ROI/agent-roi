"""Agent-ROI: track the cost, usage, and ROI of AI coding agents across tools."""

from importlib.metadata import PackageNotFoundError, version

try:
    # Read the installed distribution version so it never drifts from pyproject.
    __version__ = version("agent-roi-tracker")
except PackageNotFoundError:  # running from a source checkout without install
    __version__ = "0.0.0+dev"
