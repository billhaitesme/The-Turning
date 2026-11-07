from services.command_console import _describe_self


def test_describe_self_includes_time_zone():
    info = _describe_self()
    assert "host_time_zone" in info
    assert isinstance(info["host_time_zone"], str) and info["host_time_zone"]
    assert "host_utc_offset_minutes" in info
    assert isinstance(info["host_utc_offset_minutes"], int)
