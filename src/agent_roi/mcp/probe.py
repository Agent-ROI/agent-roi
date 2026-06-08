"""Estimate the per-turn token cost of each MCP server's tool definitions.

An MCP server contributes a fixed overhead to every agent request: the JSON
schema of every tool it exposes is injected into the system prompt. That schema
is sent (and usually cache-written) once per session regardless of whether the
tools are ever called, so a server wired up with many verbose tools quietly
taxes every conversation.

The API never breaks usage down per server, and the schemas aren't in any log —
they're produced at runtime by the server. So the only way to measure this is to
launch each server and ask it for its tool list (``tools/list``). That has side
effects (it runs the server's command), which is why this lives behind the
explicit ``agent-roi mcp-cost`` command and never runs during ingest or serve.

We speak just enough of the MCP stdio protocol (JSON-RPC over newline-delimited
stdio: ``initialize`` -> ``notifications/initialized`` -> ``tools/list``) to get
the tool list, then estimate the token size of the serialized schemas. HTTP/SSE
servers are reported as skipped (probing them would make network requests).
"""

from __future__ import annotations

import contextlib
import json
import os
import platform
import queue
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_roi.core.tokens import estimate_tokens

# How long to wait for a server to respond to a single request before giving up.
# Servers that hang (or prompt for auth) shouldn't block the whole probe.
_TIMEOUT_S = 12.0


@dataclass
class McpServerCost:
    """Estimated tool-schema cost for one MCP server (or why it was skipped)."""

    name: str
    transport: str
    tools: int = 0
    est_tokens: int = 0
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


def load_mcp_servers(config_path: Path | None = None) -> dict[str, dict[str, Any]]:
    """Read MCP server definitions from Claude Code's ``~/.claude.json``.

    Returns a name -> config mapping. Only Claude Code's config is read: the VS
    Code MCP servers on this machine are registered dynamically by extensions and
    have no static command we could launch.
    """
    path = config_path or Path.home() / ".claude.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    servers = data.get("mcpServers")
    return servers if isinstance(servers, dict) else {}


def probe_servers(
    servers: dict[str, dict[str, Any]],
    timeout: float = _TIMEOUT_S,
) -> list[McpServerCost]:
    """Probe each server's tool schemas. stdio servers are launched; others skipped."""
    results: list[McpServerCost] = []
    for name, cfg in servers.items():
        transport = _transport_of(cfg)
        if transport != "stdio":
            results.append(
                McpServerCost(
                    name=name,
                    transport=transport,
                    error="non-stdio transport not probed (would make network calls)",
                )
            )
            continue
        results.append(_probe_stdio(name, cfg, timeout))
    results.sort(key=lambda r: r.est_tokens, reverse=True)
    return results


def _transport_of(cfg: dict[str, Any]) -> str:
    declared = cfg.get("type")
    if isinstance(declared, str) and declared:
        return declared
    return "stdio" if cfg.get("command") else "http"


def _probe_stdio(name: str, cfg: dict[str, Any], timeout: float) -> McpServerCost:
    command = cfg.get("command")
    if not command:
        return McpServerCost(name=name, transport="stdio", error="no command in config")
    argv = [str(command), *[str(a) for a in cfg.get("args", [])]]
    env = {**os.environ, **{str(k): str(v) for k, v in (cfg.get("env") or {}).items()}}

    proc: subprocess.Popen[str] | None = None
    try:
        proc = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            env=env,
        )
        tools = _handshake_and_list_tools(proc, timeout)
    except FileNotFoundError:
        return McpServerCost(name=name, transport="stdio", error="command not found")
    except (OSError, _ProbeError) as exc:
        return McpServerCost(name=name, transport="stdio", error=str(exc))
    finally:
        if proc is not None:
            _terminate(proc)

    est = sum(estimate_tokens(json.dumps(t, ensure_ascii=False)) for t in tools)
    return McpServerCost(name=name, transport="stdio", tools=len(tools), est_tokens=est)


class _ProbeError(Exception):
    pass


def _handshake_and_list_tools(
    proc: subprocess.Popen[str], timeout: float
) -> list[dict[str, Any]]:
    assert proc.stdin is not None and proc.stdout is not None

    def send(obj: dict[str, Any]) -> None:
        proc.stdin.write(json.dumps(obj) + "\n")  # type: ignore[union-attr]
        proc.stdin.flush()  # type: ignore[union-attr]

    if platform.system() == "Windows":
        # select.select() doesn't work on pipes on Windows — use a reader thread.
        line_queue: queue.Queue[str | None] = queue.Queue()

        def _reader() -> None:
            try:
                for line in proc.stdout:  # type: ignore[union-attr]
                    line_queue.put(line)
            finally:
                line_queue.put(None)

        threading.Thread(target=_reader, daemon=True).start()

        def recv() -> dict[str, Any]:
            try:
                line = line_queue.get(timeout=timeout)
            except queue.Empty:
                raise _ProbeError("timed out waiting for response") from None
            if line is None:
                raise _ProbeError("server closed the connection")
            parsed: dict[str, Any] = json.loads(line)
            return parsed

    else:
        import select as _select

        def recv() -> dict[str, Any]:
            ready, _, _ = _select.select([proc.stdout], [], [], timeout)
            if not ready:
                raise _ProbeError("timed out waiting for response")
            line = proc.stdout.readline()  # type: ignore[union-attr]
            if not line:
                raise _ProbeError("server closed the connection")
            parsed2: dict[str, Any] = json.loads(line)
            return parsed2

    send(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "agent-roi", "version": "0"},
            },
        }
    )
    recv()  # initialize result; we don't need its contents
    send({"jsonrpc": "2.0", "method": "notifications/initialized"})
    send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})

    # Skip any out-of-order notifications until our tools/list reply arrives.
    for _ in range(20):
        msg = recv()
        if msg.get("id") == 2:
            tools = msg.get("result", {}).get("tools", [])
            return [t for t in tools if isinstance(t, dict)]
    raise _ProbeError("no tools/list response")


def _terminate(proc: subprocess.Popen[str]) -> None:
    try:
        proc.terminate()
        proc.wait(timeout=3)
    except (subprocess.TimeoutExpired, OSError):
        with contextlib.suppress(OSError):
            proc.kill()
