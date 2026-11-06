"""The consoles show 24-hour times in the HOST's zone; the status route tells them which zone."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app import app
from services import host_clock


def test_status_reports_the_host_clock():
    clock = TestClient(app).get("/system/status").json()["host_clock"]
    assert isinstance(clock["utc_offset_minutes"], int) and -14 * 60 <= clock["utc_offset_minutes"] <= 14 * 60
    assert clock["name"]


def test_windows_zone_names_map_to_iana(monkeypatch):
    monkeypatch.setattr(host_clock.os, "name", "nt")
    monkeypatch.setattr(host_clock.time, "tzname", ("Eastern Standard Time", "Eastern Daylight Time"))
    assert host_clock.host_clock()["iana"] == "America/New_York"
    monkeypatch.setattr(host_clock.time, "tzname", ("W. Europe Standard Time", "W. Europe Daylight Time"))
    assert host_clock.host_clock()["iana"] == "Europe/Berlin"  # Oslo's rules
    monkeypatch.setattr(host_clock.time, "tzname", ("Some Unmapped Time", ""))
    unmapped = host_clock.host_clock()
    assert unmapped["iana"] is None and isinstance(unmapped["utc_offset_minutes"], int)  # offset fallback
