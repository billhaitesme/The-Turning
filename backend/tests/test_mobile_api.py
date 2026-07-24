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
