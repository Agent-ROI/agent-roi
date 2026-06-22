"""Tests for the Antigravity collector against a synthetic conversation DB.

Antigravity stores each generation as a protobuf blob, so the fixtures here
build the relevant wire-format bytes by hand (a tiny encoder mirroring the
fields the collector reads) and write them into a SQLite database shaped like a
real ``conversations/<id>.db``.
"""

from __future__ import annotations

import sqlite3

from agent_roi.collectors.antigravity import AntigravityCollector
from agent_roi.core.models import Tool


def _varint(n: int) -> bytes:
    out = bytearray()
    while True:
        byte = n & 0x7F
        n >>= 7
        out.append(byte | (0x80 if n else 0))
        if not n:
            return bytes(out)


def _tag(field: int, wire: int) -> bytes:
    return _varint((field << 3) | wire)


def _vfield(field: int, n: int) -> bytes:
    return _tag(field, 0) + _varint(n)


def _sfield(field: int, s: str) -> bytes:
    raw = s.encode("utf-8")
    return _tag(field, 2) + _varint(len(raw)) + raw


def _mfield(field: int, payload: bytes) -> bytes:
    return _tag(field, 2) + _varint(len(payload)) + payload


def _gen_blob(*, model, label, ts, system, fresh, output, cache_read) -> bytes:
    usage = _vfield(1, system) + _vfield(2, fresh) + _vfield(3, output)
    if cache_read:
        usage += _vfield(5, cache_read)
    gen_info = _mfield(4, _vfield(1, ts))  # .9.4.1 = unix seconds
    inner = (
        _mfield(4, usage)
        + _mfield(9, gen_info)
        + _sfield(19, model)
        + _sfield(21, label)
    )
    return _mfield(1, inner)


def _traj_blob(workspace_url: str) -> bytes:
    return _sfield(7, workspace_url)


def _write_db(root, conv_id, gens, workspace="file:///Users/me/proj"):
    conv_dir = root / "conversations"
    conv_dir.mkdir(parents=True, exist_ok=True)
    db = conv_dir / f"{conv_id}.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE gen_metadata (idx integer PRIMARY KEY, data blob)")
    con.execute("CREATE TABLE trajectory_metadata_blob (id text PRIMARY KEY, data blob)")
    for i, blob in enumerate(gens):
        con.execute("INSERT INTO gen_metadata (idx, data) VALUES (?, ?)", (i, blob))
    con.execute(
        "INSERT INTO trajectory_metadata_blob (id, data) VALUES ('main', ?)",
        (_traj_blob(workspace),),
    )
    con.commit()
    con.close()
    return db


def test_parses_usage_model_and_workspace(tmp_path):
    gens = [
        _gen_blob(
            model="claude-opus-4-6-thinking",
            label="Claude Opus 4.6 (Thinking)",
            ts=1780982484,
            system=1026,
            fresh=5891,
            output=666,
            cache_read=0,
        ),
        _gen_blob(
            model="claude-opus-4-6-thinking",
            label="Claude Opus 4.6 (Thinking)",
            ts=1780982493,
            system=1026,
            fresh=2090,
            output=786,
            cache_read=5296,
        ),
    ]
    _write_db(tmp_path, "conv-abc", gens, workspace="file:///Users/me/proj")

    interactions = list(AntigravityCollector(roots=[tmp_path]).collect())
    assert len(interactions) == 2

    first, second = interactions
    assert first.tool is Tool.ANTIGRAVITY
    assert first.session_id == "conv-abc"
    assert first.id == "antigravity:conv-abc:0"
    assert second.id == "antigravity:conv-abc:1"
    # Model carries the thinking suffix; pricing prefix-matches "claude-opus-4-6".
    assert first.model == "claude-opus-4-6-thinking"
    # Fixed system/tools prompt is folded into fresh input.
    assert first.input_tokens == 5891 + 1026
    assert first.output_tokens == 666
    assert first.cache_read_tokens == 0
    # Cache reads appear on later turns.
    assert second.cache_read_tokens == 5296
    # Real usage, not estimated.
    assert first.estimated is False
    # Workspace decoded from the file:// URL in the trajectory blob.
    assert first.cwd == "/Users/me/proj"
    assert first.project == "proj"
    # Timestamp comes from the embedded unix-seconds field.
    assert first.timestamp.year == 2026


def test_ids_are_stable_across_runs(tmp_path):
    gens = [
        _gen_blob(
            model="claude-opus-4-6-thinking",
            label="x",
            ts=1780982484,
            system=10,
            fresh=100,
            output=20,
            cache_read=0,
        )
    ]
    _write_db(tmp_path, "conv-1", gens)
    run1 = {i.id for i in AntigravityCollector(roots=[tmp_path]).collect()}
    run2 = {i.id for i in AntigravityCollector(roots=[tmp_path]).collect()}
    assert run1 == run2 == {"antigravity:conv-1:0"}


def test_skips_generations_without_usage(tmp_path):
    empty = _gen_blob(
        model="claude-opus-4-6-thinking",
        label="x",
        ts=1780982484,
        system=0,
        fresh=0,
        output=0,
        cache_read=0,
    )
    _write_db(tmp_path, "conv-empty", [empty])
    assert list(AntigravityCollector(roots=[tmp_path]).collect()) == []


def test_unavailable_when_no_roots():
    assert AntigravityCollector(roots=[]).is_available() is False


def test_available_when_db_present(tmp_path):
    _write_db(
        tmp_path,
        "conv-1",
        [_gen_blob(model="m", label="m", ts=1, system=1, fresh=1, output=1, cache_read=0)],
    )
    c = AntigravityCollector(roots=[tmp_path])
    assert c.is_available() is True
    assert c.count_files() == 1
