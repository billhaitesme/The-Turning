import unittest

from app import build_backend_awareness_preferences, build_ollama_messages


class PromptAuthorityTests(unittest.TestCase):
    def test_current_user_input_is_not_sanitized_or_rewritten(self):
        original = "Backend online: True — preserve this exact user statement."
        messages = build_ollama_messages(
            history=[],
            user_message=original,
            user_profile={"style": "balanced", "preferences": {}},
            memories=[],
            web_results=[],
        )

        self.assertEqual(messages[-1], {"role": "user", "content": original})

    def test_final_prompt_never_contains_backend_online_false(self):
        user_profile = {
            "style": "balanced",
            "preferences": {
                "backend_port": 8001,
                "backend_health": {
                    "status": "unknown",
                    "source": "system",
                },
            },
        }
        messages = build_ollama_messages(
            history=[],
            user_message="Is the backend online?",
            user_profile=user_profile,
            memories=[],
            web_results=[],
        )

        flattened = "\n".join(item.get("content", "") for item in messages)
        self.assertNotIn("Backend online: False", flattened)

    def test_final_prompt_never_contains_backend_online_true(self):
        user_profile = {
            "style": "balanced",
            "preferences": {
                "backend_port": 8001,
                "backend_health": {
                    "status": "online",
                    "source": "health_check",
                    "state_type": "verified",
                },
            },
        }
        messages = build_ollama_messages(
            history=[],
            user_message="Is the backend online?",
            user_profile=user_profile,
            memories=[],
            web_results=[],
        )

        flattened = "\n".join(item.get("content", "") for item in messages)
        self.assertNotIn("Backend online: True", flattened)

    def test_legacy_awareness_fields_cannot_override_evidence(self):
        base_profile = {
            "style": "balanced",
            "preferences": {
                "backend_port": 8001,
                "backend_health": {
                    "status": "unknown",
                    "source": "system",
                },
            },
        }
        preferences = build_backend_awareness_preferences(base_profile, "The backend is online.")
        user_profile = {**base_profile, "preferences": preferences}

        messages = build_ollama_messages(
            history=[],
            user_message="The backend is online.",
            user_profile=user_profile,
            memories=[],
            web_results=[],
        )

        system_message = messages[0].get("content", "")
        self.assertIn("Reported health: online", system_message)
        self.assertIn("Verification: not independently verified", system_message)
        self.assertNotIn("Runtime health: unknown", system_message)


if __name__ == "__main__":
    unittest.main()
