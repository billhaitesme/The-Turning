"""Recents (XIII side-work): conversations persist the moment they exist; /conversations lists
them newest-activity-first so any console — PC or phone — can resume any of them."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app as app_module
from app import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_recents_lists_newest_activity_first_with_previews(client):
    first = client.post("/conversations", json={"user_id": "demo", "title": "older"}).json()["conversation_id"]
    second = client.post("/conversations", json={"user_id": "demo", "title": "newer"}).json()["conversation_id"]
    # activity in the OLDER conversation moves it back to the top — ordering is by activity,
    # not creation (add_message touches the conversation, exactly as the chat routes do)
    app_module.add_message(first, "user", "remember the lighthouse plan")
    data = client.get("/conversations?limit=100").json()
    ids = [c["id"] for c in data["conversations"]]
    assert first in ids and second in ids
    assert ids.index(first) < ids.index(second)
    entry = next(c for c in data["conversations"] if c["id"] == first)
    assert entry["message_count"] >= 1
    assert "lighthouse" in entry["preview"]
    assert len(entry["preview"]) <= 80


def test_recents_limit_is_bounded(client):
    data = client.get("/conversations?limit=1").json()
    assert len(data["conversations"]) == 1
