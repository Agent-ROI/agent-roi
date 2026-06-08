"""Tests for the opt-in MCP schema cost probe.

The stdio probe is exercised against a tiny fake MCP server (a Python script
that speaks just enough JSON-RPC to answer initialize + tools/list), so the test
is hermetic and doesn't depend on any real server being installed.
"""

from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

from agent_roi.mcp.probe import load_mcp_servers, probe_servers

# A minimal MCP stdio server: reads JSON-RPC lines, replies to initialize and
# tools/list. It exposes two trivial tools so the probe has a schema to size.
_FAKE_SERVER = textwrap.dedent(
    """
    import json, sys
    TOOLS = [
        {"name": "alpha", "description": "do alpha", "inputSchema": {"type": "object"}},
        {"name": "beta", "description": "do beta", "inputSchema": {"type": "object"}},
    ]
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        msg = json.loads(line)
        mid = msg.get("id")
        method = msg.get("method")
        if method == "initialize":
            print(json.dumps({"jsonrpc": "2.0", "id": mid, "result": {"capabilities": {}}}))
        elif method == "tools/list":
            print(json.dumps({"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}}))
        sys.stdout.flush()
    """
)


def _server_config(tmp_path: Path) -> dict[str, dict]:
    script = tmp_path / "fake_mcp.py"
    script.write_text(_FAKE_SERVER, encoding="utf-8")
    return {"fake": {"type": "stdio", "command": sys.executable, "args": [str(script)]}}


def test_probe_stdio_server_estimates_schema_tokens(tmp_path):
    results = probe_servers(_server_config(tmp_path))
    assert len(results) == 1
    r = results[0]
    assert r.name == "fake"
    assert r.ok
    assert r.tools == 2
    assert r.est_tokens > 0


def test_probe_skips_non_stdio(tmp_path):
    servers = {"remote": {"type": "http", "url": "https://example.com/mcp"}}
    [r] = probe_servers(servers)
    assert not r.ok
    assert r.transport == "http"
    assert "network" in (r.error or "")


def test_probe_reports_missing_command(tmp_path):
    servers = {"broken": {"type": "stdio", "command": "/nonexistent/binary-xyz"}}
    [r] = probe_servers(servers)
    assert not r.ok
    assert "not found" in (r.error or "")


def test_load_mcp_servers_reads_claude_config(tmp_path):
    cfg = tmp_path / ".claude.json"
    cfg.write_text(
        json.dumps({"mcpServers": {"x": {"type": "stdio", "command": "x"}}}), encoding="utf-8"
    )
    servers = load_mcp_servers(cfg)
    assert list(servers) == ["x"]


def test_load_mcp_servers_missing_file(tmp_path):
    assert load_mcp_servers(tmp_path / "nope.json") == {}
