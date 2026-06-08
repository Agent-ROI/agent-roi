"""Opt-in probing of MCP servers to estimate their tool-schema token cost.

This is deliberately *not* part of the ingest/serve pipeline: estimating a
server's schema cost means actually launching it and asking for its tool list,
which runs external programs. It only happens when the user explicitly invokes
``agent-roi mcp-cost``.
"""

from agent_roi.mcp.probe import McpServerCost, load_mcp_servers, probe_servers

__all__ = ["McpServerCost", "load_mcp_servers", "probe_servers"]
