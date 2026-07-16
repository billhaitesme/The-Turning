import unittest

from services.planning_pipeline import run_planning_pipeline


class PlanningPipelineTests(unittest.TestCase):
    def test_bypasses_for_normal_qa(self):
        result = run_planning_pipeline(
            user_message="What is FastAPI?",
            goal_store={"version": 1, "goals": []},
            evidence_store={"version": 1, "facts": {}},
            reasoning_result={},
            enabled=True,
        )

        self.assertFalse(result["used"])
        self.assertEqual(result["plans"], [])

    def test_runs_for_planning_intent(self):
        result = run_planning_pipeline(
            user_message="Can you propose a plan for vision routing?",
            goal_store={
                "version": 1,
                "goals": [
                    {
                        "id": "goal-vision-routing",
                        "title": "Add vision routing",
                        "status": "active",
                        "dependencies": [
                            "vision_model_selected",
                            "vision_model_loaded",
                            "vision_router_configured",
                        ],
                    }
                ],
            },
            evidence_store={
                "version": 1,
                "facts": {
                    "vision_model_selected": {
                        "state_type": "verified",
                        "value": True,
                    }
                },
            },
            reasoning_result={},
            enabled=True,
        )

        self.assertTrue(result["used"])
        self.assertEqual(len(result["plans"]), 1)
        self.assertIn("Current Goal", result["response"])
        self.assertIn("Current Blockers", result["response"])
        self.assertIn("Confidence", result["response"])

    def test_deterministic_output(self):
        kwargs = {
            "user_message": "show planning blockers",
            "goal_store": {
                "version": 1,
                "goals": [
                    {
                        "id": "goal-a",
                        "title": "A goal",
                        "status": "active",
                        "dependencies": ["dep-a"],
                    }
                ],
            },
            "evidence_store": {"version": 1, "facts": {}},
            "reasoning_result": {},
            "enabled": True,
        }
        result_a = run_planning_pipeline(**kwargs)
        result_b = run_planning_pipeline(**kwargs)
        self.assertEqual(result_a, result_b)


if __name__ == "__main__":
    unittest.main()
