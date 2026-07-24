import unittest

from services.model_control import ConversationTelemetry, ModelControl


class ModelControlTests(unittest.TestCase):
    def test_model_remains_locked_across_topics(self):
        control = ModelControl("dolphin-mixtral:8x7b")
        self.assertEqual(control.select_chat_model(), "dolphin-mixtral:8x7b")
        self.assertEqual(control.select_chat_model(), "dolphin-mixtral:8x7b")

    def test_only_explicit_switch_commands_are_parsed(self):
        control = ModelControl("dolphin-mixtral:8x7b")
        self.assertEqual(control.parse_explicit_switch("Switch to llama3.1:8b"), "llama3.1:8b")
        self.assertEqual(control.parse_explicit_switch("Use llava"), "llava")
        self.assertIsNone(control.parse_explicit_switch("Should I use llama3.1:8b?"))

    def test_telemetry_records_fallback_state(self):
        control = ModelControl("dolphin-mixtral:8x7b")
        payload = control.record(ConversationTelemetry(
            requested_model="dolphin-mixtral:8x7b",
            selected_model="dolphin-mixtral:8x7b",
            actual_model="dolphin-mixtral:8x7b",
            response_time=0.25,
            tokens=12,
            fallback_used=False,
        ))
        self.assertFalse(payload["fallback_used"])
        self.assertEqual(control.status()["latest_request"]["actual_model"], "dolphin-mixtral:8x7b")


if __name__ == "__main__":
    unittest.main()
