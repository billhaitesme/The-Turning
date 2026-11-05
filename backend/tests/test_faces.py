"""Faces slice (2026-11-05) — identification against the operator-enrolled gallery only.

Built on the PC before Ø2-02 so the dog onboards a known quantity. The engine is stubbed here:
tests exercise enrollment rules, gallery persistence, cosine matching and thresholds, the
unknown-stays-unknown law, and the seat-facing recognize_faces tool.
"""
from __future__ import annotations

import base64

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app import app
from services import face_engine, image_store
from services.tool_registry import TOOL_REGISTRY

PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


def _unit(vector):
    v = np.asarray(vector, dtype=np.float32)
    return v / np.linalg.norm(v)


BILL_VEC = _unit([1.0, 0.2, 0.0, 0.1])
STRANGER_VEC = _unit([-0.9, 0.4, 0.1, 0.0])


class StubEngine:
    """Returns pre-set faces regardless of pixels — the gallery math is what's under test."""

    def __init__(self, faces):
        self.faces = faces

    def faces_in(self, image_bytes):
        return [{"bbox": [0, 0, 10, 10], "det_score": 0.9, "embedding": np.asarray(e, dtype=np.float32)}
                for e in self.faces]


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("COMMAND_EXECUTION", "true")
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clean_gallery():
    face_engine.save_gallery({"version": 1, "people": []})
    yield
    face_engine.save_gallery({"version": 1, "people": []})


def test_enroll_requires_exactly_one_face_and_persists():
    with pytest.raises(ValueError, match="No face"):
        face_engine.enroll("Bill", b"x", engine=StubEngine([]))
    with pytest.raises(ValueError, match="exactly one"):
        face_engine.enroll("Bill", b"x", engine=StubEngine([BILL_VEC, STRANGER_VEC]))
    entry = face_engine.enroll("Bill", b"x", engine=StubEngine([BILL_VEC]))
    assert entry["name"] == "Bill" and entry["samples"] == 1
    # same name re-enrolls as another sample, not a duplicate person
    entry = face_engine.enroll("bill", b"x", engine=StubEngine([BILL_VEC]))
    assert entry["samples"] == 2
    assert len(face_engine.list_people()) == 1


def test_recognize_matches_enrolled_and_leaves_strangers_unknown():
    face_engine.enroll("Bill", b"x", engine=StubEngine([BILL_VEC]))
    results = face_engine.recognize(b"x", engine=StubEngine([BILL_VEC, STRANGER_VEC]))
    assert results[0]["name"] == "Bill" and results[0]["matched"]
    assert results[0]["similarity"] >= face_engine.MATCH_THRESHOLD
    assert results[1]["name"] == "unknown" and not results[1]["matched"]


def test_empty_gallery_means_everyone_is_unknown():
    results = face_engine.recognize(b"x", engine=StubEngine([BILL_VEC]))
    assert results[0]["name"] == "unknown" and results[0]["similarity"] is None


def test_recognize_faces_tool_reads_the_gallery_never_writes_it(client):
    face_engine.enroll("Bill", b"x", engine=StubEngine([BILL_VEC]))
    entry = image_store.save_image(base64.b64encode(PNG_1PX).decode(), conversation_id="conv-f")
    TOOL_REGISTRY["recognize_faces"]["adapter"]._recognize_fn = (
        lambda image_bytes: face_engine.recognize(image_bytes, engine=StubEngine([BILL_VEC])))
    r = client.post("/system/commands/recognize_faces",
                    json={"arguments": {"image_id": entry["image_id"]}})
    assert r.status_code == 200, r.text
    output = r.json()["command"]["outcome"]["output"]
    assert output["faces"][0]["name"] == "Bill"
    assert "never guess" in output["note"]
    # a missing image refuses plainly
    r = client.post("/system/commands/recognize_faces", json={"arguments": {"image_id": "img-x"}})
    assert r.status_code == 422


def test_faces_routes_enroll_list_and_remove(client, monkeypatch):
    monkeypatch.setattr(face_engine, "get_engine", lambda: StubEngine([BILL_VEC]))
    image = "data:image/png;base64," + base64.b64encode(PNG_1PX).decode()
    r = client.post("/system/faces/enroll", json={"name": "Bill", "image": image})
    assert r.status_code == 200, r.text
    person = r.json()["person"]
    listing = client.get("/system/faces").json()
    assert listing["people"][0]["name"] == "Bill"
    assert client.delete(f"/system/faces/{person['person_id']}").status_code == 200
    assert client.get("/system/faces").json()["people"] == []
    assert client.delete("/system/faces/face-nope").status_code == 404


def test_engine_unavailable_reports_plainly(client):
    TOOL_REGISTRY["recognize_faces"]["adapter"]._recognize_fn = (
        lambda image_bytes: (_ for _ in ()).throw(
            face_engine.FaceEngineUnavailable("models missing")))
    entry = image_store.save_image(base64.b64encode(PNG_1PX).decode(), conversation_id="conv-f2")
    r = client.post("/system/commands/recognize_faces",
                    json={"arguments": {"image_id": entry["image_id"]}})
    assert r.status_code == 422 and "not ready" in r.json()["detail"]
