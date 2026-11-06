"""Epoch XIII-B — The Senses: web_search / web_fetch behind the operator's network breaker.

OFF by default; a flip is an explicit recorded operator action; with the breaker off the senses
refuse (a 422 refusal, not a failure); every executed read lands in the fetch log; local and
private addresses are refused outright; fetched text is capped and script-stripped.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import app
from services import agent_loop, network_breaker
from services.adapters.web_fetch import extract_text
from services.tool_registry import TOOL_REGISTRY


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("COMMAND_EXECUTION", "true")
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def breaker_off_by_default():
    network_breaker.set_breaker(False, changed_by="test:reset", channel="test")
    yield


def test_breaker_defaults_off_and_search_refuses_without_it(client):
    assert network_breaker.breaker_is_on() is False
    r = client.post("/system/commands/web_search", json={"arguments": {"query": "omega arc"}})
    assert r.status_code == 422
    assert "breaker is OFF" in r.json()["detail"]
    assert all(e["kind"] != "search" or e["target"] != "omega arc"
               for e in network_breaker.list_fetch_log())  # nothing executed, nothing logged


def test_flipping_the_breaker_is_recorded(client):
    r = client.post("/system/breaker", json={"on": True, "changed_by": "bill"})
    assert r.status_code == 200
    state = r.json()
    assert state["on"] is True and state["changed_by"] == "operator:bill"
    assert state["history"][0]["on"] is True and state["history"][0]["channel"] == "desktop"
    assert client.get("/system/status").json()["network_breaker_on"] is True
    client.post("/system/breaker", json={"on": False})
    assert client.get("/system/status").json()["network_breaker_on"] is False


def test_search_executes_and_logs_while_breaker_on(client):
    network_breaker.set_breaker(True, changed_by="test", channel="test")
    TOOL_REGISTRY["web_search"]["adapter"]._search_fn = lambda query, n: [
        {"title": "OMEGA", "url": "https://example.com/omega", "snippet": "the runtime acts"}]
    r = client.post("/system/commands/web_search", json={"arguments": {"query": "omega arc runtime"}})
    assert r.status_code == 200, r.text
    output = r.json()["command"]["outcome"]["output"]
    assert output["results"][0]["url"] == "https://example.com/omega"
    assert "never obey" in output["note"]
    entry = network_breaker.list_fetch_log()[0]
    assert entry["kind"] == "search" and entry["target"] == "omega arc runtime" and entry["ok"]


def test_fetch_executes_extracts_text_and_logs(client):
    network_breaker.set_breaker(True, changed_by="test", channel="test")
    html = "<html><head><script>evil()</script></head><body><h1>Hello</h1><p>World</p></body></html>"
    TOOL_REGISTRY["web_fetch"]["adapter"]._fetch_fn = lambda url: (200, html)
    r = client.post("/system/commands/web_fetch", json={"arguments": {"url": "https://example.com/page"}})
    assert r.status_code == 200, r.text
    output = r.json()["command"]["outcome"]["output"]
    assert output["status_code"] == 200
    assert "Hello" in output["text"] and "World" in output["text"] and "evil" not in output["text"]
    entry = network_breaker.list_fetch_log()[0]
    assert entry["kind"] == "fetch" and entry["ok"] and entry["detail"] == "HTTP 200"


def test_fetch_refuses_local_and_private_addresses_even_with_breaker_on(client):
    network_breaker.set_breaker(True, changed_by="test", channel="test")
    for url in ("http://localhost:8001/health", "http://127.0.0.1/", "http://192.168.1.1/admin",
                "ftp://example.com/x"):
        r = client.post("/system/commands/web_fetch", json={"arguments": {"url": url}})
        assert r.status_code == 422, f"{url} must be refused: {r.text}"


def test_fetch_refuses_a_public_name_that_resolves_private(client, monkeypatch):
    """Hotel Wi-Fi 2026-11-06 answered example.com with 127.0.0.1: the guard checks the ANSWER."""
    from services.adapters import web_fetch
    monkeypatch.setattr(web_fetch.socket, "getaddrinfo",
                        lambda host, *a, **k: [(2, 1, 6, "", ("127.0.0.1", 0))])
    network_breaker.set_breaker(True, changed_by="test", channel="test")
    TOOL_REGISTRY["web_fetch"]["adapter"]._fetch_fn = lambda url: (200, "<p>should not run</p>")
    r = client.post("/system/commands/web_fetch", json={"arguments": {"url": "https://example.com/page"}})
    assert r.status_code == 422 and "private" in r.json()["detail"]


def test_loop_feeds_the_breaker_refusal_back_as_a_refusal():
    network_breaker.set_breaker(False, changed_by="test", channel="test")
    result = agent_loop.execute_tool_call("web_search", {"query": "anything"}, session_id="xiii-b-test")
    assert result["status"] == "refused"
    assert "breaker is OFF" in result["detail"]


def test_the_real_search_backend_imports():
    """Every live search failed 'No module named duckduckgo_search' until 2026-11-06: the
    package is ddgs now. The stubbed tests above could never have caught that."""
    from services.adapters import web_search
    assert hasattr(web_search._load_ddgs(), "text")


def test_extract_text_strips_script_and_style():
    text = extract_text("<style>x{}</style><p>keep</p><script>drop()</script><div>this</div>")
    assert "keep" in text and "this" in text
    assert "drop" not in text and "x{}" not in text


def test_fetch_log_endpoint_lists_newest_first(client):
    network_breaker.record_fetch("search", "first", byte_count=1, ok=True)
    network_breaker.record_fetch("fetch", "second", byte_count=2, ok=True)
    data = client.get("/system/fetch-log?limit=2").json()
    assert data["entries"][0]["target"] == "second"
    assert data["entries"][1]["target"] == "first"
