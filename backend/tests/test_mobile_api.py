import importlib
import sqlite3

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient


def build_client(monkeypatch, tmp_path):
    monkeypatch.setenv("MOBILE_AUTH_TOKEN", "test-secret")
    monkeypatch.setenv("RUNTIME_VERSION", "0.2.0")
    monkeypatch.setenv("REQUIRED_MOBILE_VERSION", "0.2.0")
    monkeypatch.setenv("MOBILE_API_VERSION", "1")
    monkeypatch.setenv("CHRONICLE_PATH", str(tmp_path / "missing.json"))

    import routes.mobile as mobile
    importlib.reload(mobile)

    database = tmp_path / "mobile.db"
    conn = sqlite3.connect(database)
    conn.execute(
        "CREATE TABLE conversations (id TEXT PRIMARY KEY, title TEXT, updated_at TEXT)"
    )
    conn.execute(
        "INSERT INTO conversations VALUES ('active', 'Desktop', '2026-07-22T20:00:00Z')"
    )
    conn.commit()
    conn.close()

    messages = [{
        "role": "assistant",
        "content": "Core Runtime online.",
        "created_at": "2026-07-22T20:00:00Z",
    }]

    def get_db():
        connection = sqlite3.connect(database)
        connection.row_factory = sqlite3.Row
        return connection

    def stream_chat(message, conversation_id):
        return StreamingResponse(
            iter([b'data: {"type":"delta","text":"online"}\n\n', b'data: {"type":"end"}\n\n']),
            media_type="text/event-stream",
        )

    mobile.configure_mobile_runtime(
        create_conversation=lambda **kwargs: "active",
        conversation_exists=lambda value: value == "active",
        get_full_messages=lambda value: messages,
        get_conversation_meta=lambda value: {"id": value},
        get_db=get_db,
        stream_chat=stream_chat,
    )
    app = FastAPI()
    app.include_router(mobile.router)
    return TestClient(app)


def auth():
    return {"Authorization": "Bearer test-secret"}


def test_authentication_is_required(monkeypatch, tmp_path):
    response = build_client(monkeypatch, tmp_path).get("/api/mobile/v1/status")
    assert response.status_code == 401
    assert "test-secret" not in response.text


def test_missing_server_token_fails_closed(monkeypatch, tmp_path):
    client = build_client(monkeypatch, tmp_path)
    monkeypatch.delenv("MOBILE_AUTH_TOKEN")
    response = client.get("/api/mobile/v1/status", headers=auth())
    assert response.status_code == 503


def test_compatibility_exposes_all_versions(monkeypatch, tmp_path):
    response = build_client(monkeypatch, tmp_path).get(
        "/api/mobile/v1/compatibility", headers=auth()
    )
    assert response.status_code == 200
    assert response.json() == {
        "runtime_version": "0.2.0",
        "required_mobile_version": "0.2.0",
        "api_version": "1",
    }


def test_status_preserves_model_lock(monkeypatch, tmp_path):
    response = build_client(monkeypatch, tmp_path).get(
        "/api/mobile/v1/status", headers=auth()
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["model_lock"] is True
    assert payload["current_model"]
    assert payload["online"] is True


def test_active_conversation_maps_runtime_roles(monkeypatch, tmp_path):
    response = build_client(monkeypatch, tmp_path).get(
        "/api/mobile/v1/conversations/active", headers=auth()
    )
    assert response.status_code == 200
    assert response.json()["id"] == "active"
    assert response.json()["messages"][0]["role"] == "runtime"


def test_evidence_diagnostic_tracks_facts(monkeypatch, tmp_path):
    client = build_client(monkeypatch, tmp_path)
    import routes.mobile as mobile

    monkeypatch.setattr(mobile, "load_evidence_store", lambda *a, **k: {"version": 1, "facts": {}})
    empty = client.get("/api/mobile/v1/diagnostics", headers=auth()).json()
    assert empty["evidence"]["state"] == "inactive"

    # Regression: records live under "facts"; the diagnostic previously checked a
    # non-existent "evidence" key and could never report healthy.
    monkeypatch.setattr(
        mobile, "load_evidence_store", lambda *a, **k: {"version": 1, "facts": {"f1": {"claim": "x"}}}
    )
    loaded = client.get("/api/mobile/v1/diagnostics", headers=auth()).json()
    assert loaded["evidence"]["state"] == "healthy"


def test_deliberation_diagnostic_tracks_approvals(monkeypatch, tmp_path):
    client = build_client(monkeypatch, tmp_path)
    import routes.mobile as mobile

    # Regression: the store dict is always non-empty (version/approvals keys), so
    # bool(store) reported healthy even with zero approvals. Empty must be inactive.
    monkeypatch.setattr(mobile, "load_approval_store", lambda *a, **k: {"version": 1, "approvals": {}})
    empty = client.get("/api/mobile/v1/diagnostics", headers=auth()).json()
    assert empty["deliberation"]["state"] == "inactive"

    monkeypatch.setattr(
        mobile, "load_approval_store", lambda *a, **k: {"version": 1, "approvals": {"a1": {"status": "pending"}}}
    )
    loaded = client.get("/api/mobile/v1/diagnostics", headers=auth()).json()
    assert loaded["deliberation"]["state"] == "healthy"


def test_status_includes_available_models(monkeypatch, tmp_path):
    response = build_client(monkeypatch, tmp_path).get("/api/mobile/v1/status", headers=auth())
    assert response.status_code == 200
    models = response.json()["available_models"]
    assert isinstance(models, list) and "dolphin-mixtral:8x7b" in models


def test_model_selector_switches_within_allowlist(monkeypatch, tmp_path):
    client = build_client(monkeypatch, tmp_path)
    import services.model_control as mc

    try:
        response = client.post("/api/mobile/v1/model", headers=auth(), json={"model": "llama3.1:8b"})
        assert response.status_code == 200
        assert response.json()["current_model"] == "llama3.1:8b"

        # A model outside the allowlist is rejected — Model Lock's controlled set.
        rejected = client.post("/api/mobile/v1/model", headers=auth(), json={"model": "gemma3:1b"})
        assert rejected.status_code == 422
    finally:
        # Restore the default so the shared model_control singleton doesn't leak state.
        mc.model_control.set_active_model("dolphin-mixtral:8x7b")


def test_stream_reuses_authoritative_runtime_stream(monkeypatch, tmp_path):
    response = build_client(monkeypatch, tmp_path).post(
        "/api/mobile/v1/conversations/active/messages",
        headers=auth(),
        json={"content": "Report status", "client_message_id": "client-1"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert '"type":"delta"' in response.text
    assert '"type":"end"' in response.text
