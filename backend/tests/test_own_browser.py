import pytest

from services import command_registry
from services.adapters import own_browser
from services.tool_registry import get_tool, get_tool_adapter, register_default_tools, unregister_tool


class _Page:
    def goto(self, url, wait_until=None, timeout=None):
        self.url = url
        assert wait_until == "load"

    def title(self):
        return "Example"

    def content(self):
        return "<html><head><title>x</title></head><body><p>" + "a" * 7000 + "</p></body></html>"


class _Browser:
    def new_page(self):
        return _Page()

    def close(self):
        pass


class _Chromium:
    launched = None

    def launch(self, **kwargs):
        _Chromium.launched = kwargs
        return _Browser()


class _Playwright:
    chromium = _Chromium()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def stubbed(monkeypatch):
    log = []
    monkeypatch.setattr(own_browser, "_sync_playwright", lambda: _Playwright())
    monkeypatch.setattr(own_browser, "require_breaker_on", lambda: None)
    monkeypatch.setattr(own_browser, "_refuse_private_host", lambda url: None)
    monkeypatch.setattr(own_browser, "record_fetch", lambda *a, **k: log.append((a, k)))
    unregister_tool("own_browser_read")
    register_default_tools()
    return log


def test_tool_and_command_registered(stubbed):
    assert get_tool("own_browser_read") is not None
    assert get_tool_adapter("own_browser_read") is not None
    command = command_registry.get_command("own_browser_read")
    assert command["gate"] == "direct"
    assert command["risk"] == "low"
    assert command["category"] == "senses"
    assert command["tool_name"] == "own_browser_read"


def test_reads_title_and_caps_text(stubbed):
    adapter = get_tool_adapter("own_browser_read")
    result = adapter.execute({"url": "https://example.com/"})
    assert result["title"] == "Example"
    assert len(result["text"]) == own_browser.MAX_TEXT_CHARS
    assert result["truncated"] is True
    assert _Chromium.launched == {"headless": True, "channel": "chromium"}
    assert len(stubbed) == 1


def test_rejects_non_http(stubbed):
    adapter = get_tool_adapter("own_browser_read")
    with pytest.raises(ValueError):
        adapter.execute({"url": "file:///etc/passwd"})


def test_breaker_off_refuses(stubbed, monkeypatch):
    def _off():
        raise ValueError("breaker off")

    monkeypatch.setattr(own_browser, "require_breaker_on", _off)
    adapter = get_tool_adapter("own_browser_read")
    with pytest.raises(ValueError):
        adapter.execute({"url": "https://example.com/"})
