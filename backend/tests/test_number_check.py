"""Number grounding (2026-11-06): the seat said USD/NOK 9.2984 when the tool returned 9.4277.

The fixtures below are the real tool outputs and the real reply from that turn."""
from __future__ import annotations

import json

from services import agent_loop, number_check

FX_RESULT = {"status": "executed", "outcome": {
    "tool": "exchange_rate", "status_code": 200,
    "output": json.dumps({"amount": 1.0, "base": "USD", "date": "2026-11-06", "rates": {"NOK": 9.4277}})}}
WX_RESULT = {"status": "executed", "outcome": {
    "tool": "weather_forecast", "status_code": 200,
    "output": json.dumps({"time": ["2026-11-06", "2026-11-07", "2026-11-08"],
                          "temperature_2m_max": [3.2, 2.7, 4.0], "temperature_2m_min": [-0.1, -0.6, 0.3],
                          "wind_speed_10m_max": [7.2, 7.6, 6.1]})}}
REAL_REPLY = ("- **November 6**: Max temperature 3.2°C, Min temperature -0.1°C, Wind speed up to 7.2 m/s.\n"
              "- **November 7**: Max temperature 2.7°C, Min temperature -0.6°C, Wind speed up to 7.6 m/s.\n"
              "- **November 8**: Max temperature 4.0°C, Min temperature 0.3°C, Wind speed up to 6.1 m/s.\n"
              "As for the currency exchange rate, 1 USD is currently equivalent to **9.2984 NOK**.")


def test_the_real_misquote_is_caught_and_only_it():
    unverified, note = number_check.check_reply(
        REAL_REPLY, [("weather_forecast", WX_RESULT), ("exchange_rate", FX_RESULT)])
    assert unverified == ["9.2984"]
    assert "9.4277" in note and "exchange_rate" in note  # the true value is shown beside it


def test_faithful_reply_adds_nothing():
    reply = REAL_REPLY.replace("9.2984", "9.4277")
    assert number_check.check_reply(reply, [("weather_forecast", WX_RESULT),
                                            ("exchange_rate", FX_RESULT)]) == ([], "")


def test_rounding_and_truncation_are_grounded():
    for written in ("9.43", "9.42", "9.4", "9.428", "9.42770"):
        assert number_check.check_reply(f"About {written} NOK.", [("exchange_rate", FX_RESULT)])[0] == []
    assert number_check.check_reply("About 9.44 NOK.", [("exchange_rate", FX_RESULT)])[0] == ["9.44"]


def test_no_tool_this_turn_marks_readings_as_from_memory():
    # the real second failure: "use your tools now ... Bergen" -> no call, Oslo numbers re-served
    unverified, note = number_check.check_reply(
        "1 USD is currently 9.2984 NOK. Bergen max 3.2°C.", [],
        operator_message="Use your tools now: what is 1 USD in NOK right now?")
    assert unverified == ["9.2984", "3.2"]
    assert "no tool ran this turn" in note and "not a live lookup" in note
    pending = {"status": "awaiting_approval", "detail": "biometric"}
    assert "no tool ran" in number_check.check_reply("Rate 9.2984.", [("exchange_rate", pending)])[1]


def test_plain_chat_without_decimals_gets_no_note():
    assert number_check.check_reply("Morning, Bill. Three tools are live.", []) == ([], "")
    assert number_check.check_reply("You said 12.5 km.", [], operator_message="12.5 km run")[0] == []


def test_versions_integers_and_operator_numbers_are_not_flagged():
    reply = "Build 0.5.2 at 192.168.1.10 on 2026-11-06, 3 days. You said 12.5 km; rate 9.4277."
    assert number_check.check_reply(reply, [("exchange_rate", FX_RESULT)],
                                    operator_message="I walked 12.5 km")[0] == []


def test_loop_appends_the_note_to_stream_and_saved_reply(monkeypatch):
    monkeypatch.setattr(agent_loop, "execute_tool_call", lambda name, args, session_id: FX_RESULT)
    turns = [{"tool_calls": [{"function": {"name": "run_exchange_rate",
                                           "arguments": {"base": "USD", "target": "NOK"}}}]},
             {"content": "1 USD is currently 9.2984 NOK."}]
    remaining = list(turns)

    def seat(conversation, tools, model):
        turn = remaining.pop(0)
        if turn.get("content"):
            yield {"type": "delta", "text": turn["content"]}
        yield {"type": "message", "content": turn.get("content") or "",
               "tool_calls": turn.get("tool_calls") or []}

    events = list(agent_loop.iter_agent_loop(
        messages=[{"role": "user", "content": "USD to NOK?"}], model="t", session_id="c", seat_turn=seat))
    streamed = "".join(e["text"] for e in events if e["event"] == "delta")
    final = events[-1]
    assert final["event"] == "final" and final["unverified_numbers"] == ["9.2984"]
    assert streamed == final["reply"]  # streaming clients and the saved reply agree
    assert final["reply"].startswith("1 USD is currently 9.2984 NOK.")
    assert "Number check" in final["reply"] and "9.4277" in final["reply"]
