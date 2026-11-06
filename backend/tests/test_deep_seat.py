"""The deep rung's seat (2026-11-06): the operator picks which model is deep_think's LOCAL rung
from a console; OMEGA only picks local vs frontier."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import app
from services import agent_loop, command_registry, deep_seat
from services.adapters import deep_think

EIGHT, THIRTY = deep_seat.CHOICES[0]["model"], deep_seat.CHOICES[1]["model"]


@pytest.fixture(autouse=True)
def clean(monkeypatch):
    deep_seat._path().unlink(missing_ok=True)
    monkeypatch.delenv("DEEP_LOCAL_MODEL", raising=False)
    yield
    deep_seat._path().unlink(missing_ok=True)


def test_default_is_the_light_8b_and_env_is_honoured_only_if_it_names_a_choice(monkeypatch):
    assert deep_seat.local_model() == EIGHT
    monkeypatch.setenv("DEEP_LOCAL_MODEL", THIRTY)
    assert deep_seat.local_model() == THIRTY
    monkeypatch.setenv("DEEP_LOCAL_MODEL", "some/other:70b")
    assert deep_seat.local_model() == EIGHT


def test_the_console_switch_is_recorded_and_drives_the_local_rung(monkeypatch):
    client = TestClient(app)
    r = client.post("/system/deep-seat", json={"model": THIRTY, "changed_by": "desktop-console"})
    assert r.status_code == 200 and r.json()["model"] == THIRTY
    got = client.get("/system/deep-seat").json()
    assert got["model"] == THIRTY and got["history"][0]["by"] == "operator:desktop-console"
    assert [c["label"] for c in got["choices"]] == ["8B", "30B"]

    sent = {}

    class Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"message": {"content": "answer"}}

    monkeypatch.setattr(deep_think.httpx, "post", lambda url, json, timeout: sent.update(json) or Resp())
    model, answer = deep_think._local_think("task")
    assert model == THIRTY and sent["model"] == THIRTY and sent["think"] is True


def test_only_the_listed_models_can_be_chosen():
    r = TestClient(app).post("/system/deep-seat", json={"model": "evil/model:1b"})
    assert r.status_code == 422 and deep_seat.local_model() == EIGHT


def test_the_model_has_no_path_to_the_switch_and_judges_the_task_not_the_words():
    names = {c["name"] for c in command_registry.list_commands()}
    assert not any("deep_seat" in n or "deep-seat" in n for n in names)
    addendum = agent_loop.AGENT_SYSTEM_ADDENDUM
    assert 'the operator says "think deeper"' not in addendum  # the literal trigger is gone
    assert "Judge the TASK, not the" in addendum
