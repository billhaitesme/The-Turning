import unittest

from services.reflection_engine import reflect_on_turn


class ReflectionEngineTests(unittest.TestCase):
    def test_correction_produces_reflection_signals(self):
        result = reflect_on_turn(
            user_message="Actually, the backend runs on port 8002.",
            assistant_response="Understood.",
            cognition_result={
                "knowledge_candidates": [
                    {
                        "kind": "knowledge",
                        "key": "backend_port",
                        "value": 8001,
                        "source": "explicit_user_statement",
                    }
                ],
                "corrections": [
                    {
                        "kind": "correction",
                        "key": "user_correction",
                        "value": "Actually, the backend runs on port 8002.",
                    }
                ],
            },
        )

        self.assertTrue(result["mistakes"])
        self.assertTrue(result["lessons"])
        self.assertTrue(result["recommended_actions"])


if __name__ == "__main__":
    unittest.main()
