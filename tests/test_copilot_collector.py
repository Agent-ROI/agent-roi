"""Tests for the Copilot collector against a realistic chat-session fixture."""

from __future__ import annotations

import json

from agent_roi.collectors.copilot import CopilotCollector, _workspace_cwd
from agent_roi.core.models import Tool


def _write_session(user_root, ws_id, session_id, payload):
    sessions = user_root / "workspaceStorage" / ws_id / "chatSessions"
    sessions.mkdir(parents=True, exist_ok=True)
    (sessions / f"{session_id}.json").write_text(json.dumps(payload), encoding="utf-8")


def _write_patch_stream(user_root, ws_id, session_id, patches):
    sessions = user_root / "workspaceStorage" / ws_id / "chatSessions"
    sessions.mkdir(parents=True, exist_ok=True)
    lines = "\n".join(json.dumps(p) for p in patches)
    (sessions / f"{session_id}.jsonl").write_text(lines, encoding="utf-8")


def test_parses_request_and_estimates_tokens(tmp_path):
    payload = {
        "version": 3,
        "requests": [
            {
                "requestId": "req-1",
                "timestamp": 1772256970068,
                "modelId": "copilot/claude-opus-4.6",
                "message": {"text": "how do I add auth middleware"},
                "response": [{"value": "Add a middleware that checks the session token..."}],
                "result": {},
            }
        ],
    }
    _write_session(tmp_path, "ws1", "sess-1", payload)

    collector = CopilotCollector(roots=[tmp_path])
    interactions = list(collector.collect())

    assert len(interactions) == 1
    itx = interactions[0]
    assert itx.id == "copilot:req-1"
    assert itx.tool is Tool.COPILOT
    # Vendor prefix stripped, dots normalized to dashes for pricing lookup.
    assert itx.model == "claude-opus-4-6"
    assert itx.estimated is True
    assert itx.input_tokens > 0
    assert itx.output_tokens > 0
    assert itx.summary.startswith("how do I add auth")


def test_parses_patch_stream_format(tmp_path):
    """Newer VS Code writes a kind:0 snapshot followed by kind:1/2 patches.

    The streamed response arrives as kind:2 appends to ``response``; we must
    replay the patches to reconstruct the full conversation.
    """
    patches = [
        {
            "kind": 0,
            "v": {
                "sessionId": "sess-1",
                "requests": [
                    {
                        "requestId": "req-1",
                        "timestamp": 1772256970068,
                        "modelId": "copilot/claude-opus-4.6",
                        "message": {"text": "how do I add auth middleware"},
                        "response": [],
                    }
                ],
            },
        },
        {"kind": 2, "k": ["requests", 0, "response"], "v": [{"value": "Add a middleware "}]},
        {"kind": 2, "k": ["requests", 0, "response"], "v": [{"value": "that checks the token."}]},
        {"kind": 1, "k": ["requests", 0, "result"], "v": {"timings": {}}},
    ]
    _write_patch_stream(tmp_path, "ws1", "sess-1", patches)

    interactions = list(CopilotCollector(roots=[tmp_path]).collect())

    assert len(interactions) == 1
    itx = interactions[0]
    assert itx.id == "copilot:req-1"
    assert itx.model == "claude-opus-4-6"
    assert itx.estimated is True
    # The appended response chunks were reassembled into the summary.
    assert "Add a middleware that checks the token." in itx.summary


def test_extracts_activities_tools_mcp_and_files(tmp_path):
    payload = {
        "version": 3,
        "requests": [
            {
                "requestId": "req-1",
                "timestamp": 1772256970068,
                "modelId": "copilot/claude-opus-4.6",
                "message": {"text": "do the thing"},
                "response": [
                    {
                        "kind": "toolInvocationSerialized",
                        "toolId": "copilot_readFile",
                        "source": {"type": "internal", "label": "Built-In"},
                        "invocationMessage": {"value": "讀取 [](file:///Users/yen/repo/app.py)"},
                    },
                    {
                        "kind": "toolInvocationSerialized",
                        "toolId": "run_in_terminal",
                        "source": {"type": "internal"},
                        "toolSpecificData": {"kind": "terminal", "cwd": "/Users/yen/repo"},
                    },
                    {
                        "kind": "toolInvocationSerialized",
                        "toolId": "mcp_gitkraken_pull_request",
                        "source": {
                            "type": "mcp",
                            "label": "GitKraken",
                            "serverLabel": "GitKraken CLI",
                        },
                    },
                    # Non-tool parts are ignored.
                    {"kind": "thinking", "value": "hmm"},
                ],
            }
        ],
    }
    _write_session(tmp_path, "ws1", "sess-1", payload)

    interactions = list(CopilotCollector(roots=[tmp_path]).collect())
    acts = interactions[0].activities
    assert [a.kind for a in acts] == ["readFile", "run_in_terminal", "mcp_gitkraken_pull_request"]
    # readFile path recovered from the file:// URI in the invocation message.
    assert acts[0].target == "/Users/yen/repo/app.py"
    # terminal records its working directory.
    assert acts[1].target == "/Users/yen/repo"
    # MCP server uses the short label, not the long serverLabel.
    assert acts[2].mcp_server == "GitKraken"
    assert acts[0].mcp_server is None


def test_unavailable_without_workspace_storage(tmp_path):
    assert CopilotCollector(roots=[tmp_path]).is_available() is False


def _write_workspace_json(tmp_path, folder):
    ws_dir = tmp_path / "ws"
    ws_dir.mkdir(parents=True, exist_ok=True)
    (ws_dir / "workspace.json").write_text(json.dumps({"folder": folder}), encoding="utf-8")
    return ws_dir


def test_workspace_cwd_local(tmp_path):
    ws = _write_workspace_json(tmp_path, "file:///Users/yen/Desktop/app")
    assert _workspace_cwd(ws) == "/Users/yen/Desktop/app"


def test_workspace_cwd_ssh_remote(tmp_path):
    ws = _write_workspace_json(tmp_path, "vscode-remote://ssh-remote%2Bwsl/home/yen/repo/rich-way")
    assert _workspace_cwd(ws) == "/home/yen/repo/rich-way"


def test_workspace_cwd_dev_container_host_path(tmp_path):
    # dev-container authority encodes {"hostPath": "/Users/yen/Desktop/saltar-backend"}.
    blob = json.dumps({"hostPath": "/Users/yen/Desktop/saltar-backend"}).encode().hex()
    folder = f"vscode-remote://dev-container%2B{blob}/workspaces/saltar-backend"
    ws = _write_workspace_json(tmp_path, folder)
    assert _workspace_cwd(ws) == "/Users/yen/Desktop/saltar-backend"


def test_workspace_cwd_dev_container_volume(tmp_path):
    # A named-volume dev container has no host path; fall back to the folder name.
    blob = json.dumps({"volumeName": "postgres", "folder": "postgres"}).encode().hex()
    folder = f"vscode-remote://dev-container%2B{blob}/workspaces/postgres"
    ws = _write_workspace_json(tmp_path, folder)
    assert _workspace_cwd(ws) == "postgres"


def test_skips_records_without_request_id(tmp_path):
    payload = {"requests": [{"modelId": "copilot/x", "message": {"text": "hi"}}]}
    _write_session(tmp_path, "ws1", "sess-1", payload)
    assert list(CopilotCollector(roots=[tmp_path]).collect()) == []
