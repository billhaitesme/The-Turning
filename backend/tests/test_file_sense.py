"""File sense (2026-11-07) — read-only eyes on the operator's files, inside whitelisted roots.

Laws under test: no roots = no sense; resolution kills traversal; outside the roots does not
exist; credential-shaped names are refused; binary is reported, never dumped; reads are capped
and pageable; everything is read-only and registered as a direct command.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import app
from services.adapters.file_sense import ListFolderAdapter, ReadFileAdapter


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("COMMAND_EXECUTION", "true")
    with TestClient(app) as c:
        yield c


@pytest.fixture
def root(tmp_path, monkeypatch):
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes" / "plan.txt").write_text("the lighthouse plan: " + "x" * 50, encoding="utf-8")
    (tmp_path / "notes" / ".env").write_text("SECRET=1", encoding="utf-8")
    (tmp_path / "notes" / "blob.bin").write_bytes(b"\x00\x01\x02\x03" * 10)
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir(exist_ok=True)
    (outside / "leak.txt").write_text("not yours", encoding="utf-8")
    monkeypatch.setenv("FILE_SENSE_ROOTS", str(tmp_path))
    return tmp_path


def test_no_roots_means_the_sense_does_not_exist(monkeypatch):
    monkeypatch.setenv("FILE_SENSE_ROOTS", "")
    with pytest.raises(ValueError, match="whitelisted no roots"):
        ListFolderAdapter().execute({"path": "C:/"})


def test_list_and_read_inside_the_root(root):
    listing = ListFolderAdapter().execute({"path": str(root / "notes")})
    names = {e["name"] for e in listing["entries"]}
    assert {"plan.txt", ".env", "blob.bin"} <= names
    result = ReadFileAdapter().execute({"path": str(root / "notes" / "plan.txt")})
    assert "lighthouse" in result["text"]
    assert "private data" in result["note"]


def test_reads_are_capped_and_pageable(root, monkeypatch):
    monkeypatch.setenv("FILE_SENSE_MAX_CHARS", "500")
    big = root / "notes" / "big.txt"
    big.write_text("A" * 400 + "B" * 400, encoding="utf-8")
    first = ReadFileAdapter().execute({"path": str(big)})
    assert len(first["text"]) == 500 and first["truncated"]
    second = ReadFileAdapter().execute({"path": str(big), "start": 500})
    assert second["text"] == "B" * 300 and not second["truncated"]


def test_outside_the_roots_does_not_exist(root):
    outside = root.parent / f"{root.name}-outside" / "leak.txt"
    with pytest.raises(ValueError, match="outside the operator's whitelisted roots"):
        ReadFileAdapter().execute({"path": str(outside)})
    # traversal dies at resolution
    with pytest.raises(ValueError, match="outside|cannot be resolved|does not exist"):
        ReadFileAdapter().execute({"path": str(root / "notes" / ".." / ".." / f"{root.name}-outside" / "leak.txt")})


def test_the_senses_never_read_the_houses_keys(root):
    with pytest.raises(ValueError, match="credential-shaped"):
        ReadFileAdapter().execute({"path": str(root / "notes" / ".env")})


def test_binary_is_reported_never_dumped(root):
    result = ReadFileAdapter().execute({"path": str(root / "notes" / "blob.bin")})
    assert result["binary"] is True and "text" not in result


def test_registered_as_direct_commands_and_runs_through_the_console(client, root):
    r = client.post("/system/commands/list_folder", json={"arguments": {"path": str(root / "notes")}})
    assert r.status_code == 200, r.text
    entry = r.json()["command"]
    assert entry["gate"] == "direct" and entry["status"] == "executed"
    assert any(e["name"] == "plan.txt" for e in entry["outcome"]["output"]["entries"])
