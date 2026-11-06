"""The host's clock, for the consoles (2026-11-06).

Bill works watches and reads times as 24-hour HH:MM. The web console printed times in the
BROWSER's locale (12-hour, and in the browser's zone — wrong when a phone opens the console over
Tailscale from elsewhere). The consoles now format every time in the HOST's zone, 24-hour.

Browsers need an IANA zone name (e.g. America/New_York) to get daylight-saving right. Windows
reports its own names ("Eastern Standard Time"), so they are mapped here (CLDR's primary zone for
each). An unmapped zone still yields the host's current UTC offset, which the console falls back
to.
"""
from __future__ import annotations

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Windows zone (standard name) -> IANA, per CLDR windowsZones primary territory "001".
WINDOWS_TO_IANA = {
    "Eastern Standard Time": "America/New_York",
    "Central Standard Time": "America/Chicago",
    "Mountain Standard Time": "America/Denver",
    "US Mountain Standard Time": "America/Phoenix",
    "Pacific Standard Time": "America/Los_Angeles",
    "Alaskan Standard Time": "America/Anchorage",
    "Hawaiian Standard Time": "Pacific/Honolulu",
    "Atlantic Standard Time": "America/Halifax",
    "Newfoundland Standard Time": "America/St_Johns",
    "GMT Standard Time": "Europe/London",
    "Greenwich Standard Time": "Atlantic/Reykjavik",
    "W. Europe Standard Time": "Europe/Berlin",  # also Oslo's rules
    "Romance Standard Time": "Europe/Paris",
    "Central Europe Standard Time": "Europe/Budapest",
    "Central European Standard Time": "Europe/Warsaw",
    "FLE Standard Time": "Europe/Kiev",
    "GTB Standard Time": "Europe/Bucharest",
    "UTC": "Etc/UTC",
    "Coordinated Universal Time": "Etc/UTC",
    "Tokyo Standard Time": "Asia/Tokyo",
    "China Standard Time": "Asia/Shanghai",
    "India Standard Time": "Asia/Calcutta",
    "AUS Eastern Standard Time": "Australia/Sydney",
}


def _posix_zone() -> Optional[str]:
    tz = os.getenv("TZ", "").strip().lstrip(":")
    if "/" in tz:
        return tz
    try:
        target = str(Path("/etc/localtime").resolve())
    except OSError:
        return None
    marker = "zoneinfo/"
    return target.split(marker, 1)[1] if marker in target else None


def _windows_live_zone() -> Optional[Dict[str, Any]]:
    """Read the zone LIVE from the registry. Python caches the zone at process start, so after
    Bill changed Windows from Eastern (PairVPN's auto-detect) to Central on 2026-11-06 the running
    backend kept reporting Eastern until a restart. ActiveTimeBias is the current bias in minutes
    (UTC = local + bias), daylight saving included."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SYSTEM\CurrentControlSet\Control\TimeZoneInformation") as key:
            name = str(winreg.QueryValueEx(key, "TimeZoneKeyName")[0]).strip("\x00 ")
            bias = int(winreg.QueryValueEx(key, "ActiveTimeBias")[0])
    except (ImportError, OSError, ValueError):
        return None
    if bias >= 2 ** 31:  # REG_DWORD holds a signed value
        bias -= 2 ** 32
    return {"iana": WINDOWS_TO_IANA.get(name), "name": name, "utc_offset_minutes": -bias}


def host_clock() -> Dict[str, Any]:
    if os.name == "nt":
        live = _windows_live_zone()
        if live is not None:
            return live
    now = datetime.now().astimezone()
    offset = now.utcoffset()
    standard_name = time.tzname[0] if time.tzname else ""
    iana = WINDOWS_TO_IANA.get(standard_name) if os.name == "nt" else _posix_zone()
    return {
        "iana": iana,                       # None when unmapped: the console uses the offset
        "name": now.tzname(),               # e.g. "Eastern Standard Time"
        "utc_offset_minutes": int(offset.total_seconds() // 60) if offset is not None else 0,
    }
