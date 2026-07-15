import unittest

from services.reasoning_pipeline import run_reasoning_pipeline


class ReasoningPipelineTests(unittest.TestCase):
    def test_vertical_slice(self):
        evidence_store = {
            "version": 1,
            "records": {
                "backend_port": {
                    "key": "backend_port",
                    "value": 8002,
                    "state_type": "configured",
                    "source": "user",
                    "confidence": 1.0,
                    "dependencies": [],
                },
                "backend_health": {
                    "key": "backend_health",
                    "value": None,
                    "state_type": "invalidated",
                    "source": "health_check",
                    "confidence": 0.0,
                    "dependencies": [
                        "backend_port",
                    ],
                    "notes": "Port changed after last verification.",
                },
            },
        }

        reasoning = run_reasoning_pipeline(
            evidence_store=evidence_store,
            goal_store={"version": 1, "goals": []},
            previous_evidence_store={"version": 1, "records": {}},
            dependency_map={"backend_port": ["backend_health", "backend_url"]},
        )

        backend_port = next(item for item in reasoning["resolved_beliefs"] if item["key"] == "backend_port")
        backend_health = next(item for item in reasoning["resolved_beliefs"] if item["key"] == "backend_health")

        self.assertEqual(backend_port["value"], 8002)
        self.assertIn(backend_health["status"], {"unknown", "invalidated"})
        self.assertTrue(any(action["action"] == "run_health_check" for action in reasoning["recommended_actions"]))
        self.assertTrue(all(action["action"] != "execute_action" for action in reasoning["recommended_actions"]))


if __name__ == "__main__":
    unittest.main()
