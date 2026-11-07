"""Self-knowledge (2026-11-06): asked about its own voice, the seat guessed, claimed to see the
operator's screen, and listed shelf tools as available. These pin the fixes."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import app, console_note
from services import command_console, repeat_guard, voice_setting

pytestmark = pytest.mark.skipif(not voice_setting.installed_voices(),
                                reason="Kokoro voice files not present on this machine")


@pytest.fixture(autouse=True)
def clean():
    voice_setting._path().unlink(missing_ok=True)
    yield
    voice_setting._path().unlink(missing_ok=True)


def test_installed_voices_come_from_the_voice_file():
    voices = {v["id"]: v["label"] for v in voice_setting.installed_voices()}
    assert len(voices) == 28  # the English voices in voices-v1.0.bin (54 in all)
    assert voices["bm_fable"] == "Fable (British male)" and voices["af_heart"] == "Heart (American female)"
    assert voice_setting.current_voice() == "bm_fable"


def test_omega_can_list_and_change_its_own_voice_through_the_console():
    listed = command_console.initiate_command("list_voices", requested_by="model:agent-seat",
                                              channel="chat")
    assert listed["status"] == "executed" and len(listed["outcome"]["voices"]) == 28
    changed = command_console.initiate_command("set_voice", requested_by="model:agent-seat",
                                               channel="chat", arguments={"voice": "bm_george"})
    assert changed["status"] == "executed" and voice_setting.current_voice() == "bm_george"
    with pytest.raises(command_console.CommandError):
        command_console.initiate_command("set_voice", requested_by="model:agent-seat",
                                         channel="chat", arguments={"voice": "xx_nobody"})
    assert voice_setting.current_voice() == "bm_george"


def test_the_console_picker_routes():
    client = TestClient(app)
    assert client.get("/voice/voices").json()["current"] == "bm_fable"
    r = client.post("/voice/voice", json={"voice": "bf_emma"})
    assert r.status_code == 200 and r.json()["current"] == "bf_emma"
    assert client.post("/voice/voice", json={"voice": "nope"}).status_code == 422


def test_describe_self_reports_the_real_body():
    me = command_console.initiate_command("describe_self", requested_by="model:agent-seat",
                                          channel="chat")["outcome"]
    assert me["voice"]["speaking_voice_now"].startswith("bm_fable")
    assert me["voice"]["installed_english_voices"] == 28
    assert "set_voice" in me["voice"]["how_to_change"]
    assert "cannot see the operator's screen" in me["sight"]


def test_the_console_tells_the_seat_whether_read_aloud_is_on():
    assert "read-aloud is ON" in console_note({"voice_out": True})
    assert "bm_fable" in console_note({"voice_out": True})
    assert "read-aloud is OFF" in console_note({"voice_out": False})
    assert console_note(None) is None and console_note({}) is None  # phones send nothing


def test_installed_and_shelf_are_separate_and_self_describing():
    out = command_console.initiate_command("check_capability_requests",
                                           requested_by="model:agent-seat", channel="chat")["outcome"]
    installed = set(out["installed_tools_usable_now"])
    shelf = {s["name"]: s["status"] for s in out["shelf_NOT_installed"]}
    assert not installed & set(shelf)
    assert all(status.startswith("NOT INSTALLED") for status in shelf.values())


def test_relisting_this_turns_tool_output_is_not_a_copy():
    tool_list = ("geocode_place turns a place name into coordinates. marine_conditions gives the "
                 "current sea state. exchange_rate gives the latest rate between two currencies. "
                 "weather_forecast gives a three day forecast with sunrise and sunset times. "
                 "world_time shows the local time for a timezone. define_word gives definitions.")
    earlier_reply = "The available tools in your setup: " + tool_list
    guard = repeat_guard.RepeatGuard([earlier_reply], "examine yourself")
    assert guard.copying(earlier_reply)  # with no fresh tool output, it IS a copy
    guard.saw_tool_result(tool_list)     # a fresh status check returned the same list this turn
    assert not guard.copying("Here is what the status check returned: " + tool_list)


def test_switch_to_a_non_model_never_changes_the_chat_model(monkeypatch):
    """'Switch to George.' (a voice) set the chat model to 'George.' and broke chat (2026-11-06)."""
    from services.model_control import model_control
    before = model_control.select_chat_model()
    assert not model_control.is_selectable("George.")
    assert model_control.is_selectable(before) or not model_control.status()["available_models"]
    seen = {}

    def fake_loop(**kwargs):
        seen["message"] = kwargs["user_message"]
        yield {"event": "final", "reply": "Switching to George now.", "hops": [],
               "seat_supports_tools": True, "eval_count": 1}

    import app as app_module
    monkeypatch.setattr(app_module, "run_agent_loop_events", fake_loop)
    monkeypatch.setattr(app_module.agent_loop, "agent_loop_enabled", lambda: True)
    with TestClient(app) as client:
        cid = client.post("/conversations", json={"title": "t", "scope": "test"}).json()["conversation_id"]
        r = client.post("/chat", json={"message": "Switch to George.", "conversation_id": cid})
    assert r.status_code == 200, r.text
    assert model_control.select_chat_model() == before          # chat model untouched
    assert seen.get("message") == "Switch to George."           # the seat got the request
    assert "Active conversational model" not in r.json()["reply"]
