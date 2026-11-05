"""Voice + vision slice (2026-11-05) — the ears, the mouth, and the eyes.

All local: Whisper STT and Kokoro TTS run on CPU with no network; vision is a bounded tool
(look_at_image) that shows a STORED operator-attached image to the local vision seat — a sense,
not a seat swap. The seat never carries raw image bytes; it gets image_ids and must look.
"""
from __future__ import annotations

import base64

import pytest
from fastapi.testclient import TestClient

import app as app_module
from app import app
from routes import voice as voice_routes
from services import agent_loop, image_store
from services.tool_registry import TOOL_REGISTRY

PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("COMMAND_EXECUTION", "true")
    with TestClient(app) as c:
        yield c


# --------------------------------------------------------------------------- the retina
def test_image_store_roundtrip_and_caps():
    data_url = "data:image/png;base64," + base64.b64encode(PNG_1PX).decode()
    entry = image_store.save_image(data_url, conversation_id="conv-1")
    assert entry["image_id"].startswith("img-") and entry["ext"] == "png"
    assert image_store.get_image_b64(entry["image_id"]) == base64.b64encode(PNG_1PX).decode()
    assert image_store.get_image_b64("img-nope") is None
    with pytest.raises(ValueError, match="base64"):
        image_store.save_image("data:image/png;base64,@@@not-base64@@@", conversation_id="c")
    with pytest.raises(ValueError, match="empty"):
        image_store.save_image("", conversation_id="c")


# --------------------------------------------------------------------------- the eyes
def test_look_at_image_shows_the_stored_image_to_the_vision_seat(client):
    entry = image_store.save_image(base64.b64encode(PNG_1PX).decode(), conversation_id="conv-2")
    seen = {}

    def fake_vision(question, image_b64):
        seen["question"], seen["image_b64"] = question, image_b64
        return {"model": "vision-test", "description": "A single dark pixel on nothing."}

    TOOL_REGISTRY["look_at_image"]["adapter"]._vision_fn = fake_vision
    r = client.post("/system/commands/look_at_image",
                    json={"arguments": {"image_id": entry["image_id"], "question": "what is it?"}})
    assert r.status_code == 200, r.text
    output = r.json()["command"]["outcome"]["output"]
    assert output["model"] == "vision-test" and "pixel" in output["description"]
    assert seen["image_b64"] == base64.b64encode(PNG_1PX).decode()  # the real stored bytes
    assert seen["question"] == "what is it?"


def test_look_at_image_refuses_a_missing_image(client):
    r = client.post("/system/commands/look_at_image",
                    json={"arguments": {"image_id": "img-gone"}})
    assert r.status_code == 422 and "No stored image" in r.json()["detail"]


def test_attached_images_are_announced_to_the_seat(monkeypatch):
    captured = {}

    def fake_iter(**kwargs):
        captured["messages"] = kwargs["messages"]
        yield {"event": "final", "reply": "ok", "hops": [], "seat_supports_tools": True,
               "eval_count": 1}

    monkeypatch.setattr(agent_loop, "iter_agent_loop", fake_iter)
    list(app_module.run_agent_loop_events(history=[], user_message="look at this",
                                          user_profile={}, memories=[], conversation_id="c",
                                          image_ids=["img-abc123"]))
    notes = [m for m in captured["messages"] if m.get("role") == "system" and "img-abc123" in m.get("content", "")]
    assert notes and "look_at_image" in notes[0]["content"]
    assert "never" in notes[0]["content"].lower()  # never guess at an image's contents


# --------------------------------------------------------------------------- the ears
def test_transcribe_returns_the_heard_text(client, monkeypatch):
    class FakeSegment:
        text = " hello omega "

    class FakeInfo:
        language = "en"
        duration = 1.25

    class FakeWhisper:
        def transcribe(self, *_args, **_kwargs):
            return [FakeSegment()], FakeInfo()

    monkeypatch.setattr(voice_routes, "_get_whisper", lambda: FakeWhisper())
    r = client.post("/voice/transcribe", content=b"\x00" * 4000)
    assert r.status_code == 200, r.text
    assert r.json()["text"] == "hello omega"
    assert client.post("/voice/transcribe", content=b"").status_code == 422


# --------------------------------------------------------------------------- the mouth
def test_speak_returns_wav_audio(client, monkeypatch):
    import numpy as np

    class FakeKokoro:
        def create(self, text, voice, speed, lang):
            assert voice == "bm_fable"  # the house voice family
            return np.zeros(2400, dtype="float32"), 24000

    monkeypatch.setattr(voice_routes, "_get_kokoro", lambda: FakeKokoro())
    r = client.post("/voice/speak", json={"text": "The runtime speaks."})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("audio/wav")
    assert r.content[:4] == b"RIFF"
    assert client.post("/voice/speak", json={"text": ""}).status_code == 422


def test_voice_status_reports_the_local_engines(client):
    data = client.get("/voice/status").json()
    assert data["local_only"] is True
    assert data["tts_voice"] == "bm_fable"
