import unittest

from services.assumption_engine import create_assumption, upsert_assumption
from services.deliberation_engine import deliberate_plan_selection


class DeliberationEngineTests(unittest.TestCase):
    def _plans(self):
        return [
            {
                "id": "plan-a",
                "goal_id": "goal-1",
                "title": "Use LLaVA",
                "steps": [
                    {"id": "s1", "dependencies": [], "evidence_requirements": [{"key": "vision_model_selected"}]},
                    {"id": "s2", "dependencies": ["s1"], "evidence_requirements": [{"key": "vision_model_loaded"}]},
                ],
                "metadata": {"confidence": 0.8},
            },
            {
                "id": "plan-b",
                "goal_id": "goal-1",
                "title": "Use Qwen2.5-VL",
                "steps": [
                    {"id": "s1", "dependencies": ["x", "y", "z"], "evidence_requirements": [{"key": "vision_model_selected"}]},
                ],
                "metadata": {"confidence": 0.55},
            },
        ]

    def test_recommendation_selection_is_deterministic(self):
        assumption_store = {"version": 1, "assumptions": []}
        assumption_store = upsert_assumption(
            assumption_store,
            create_assumption(
                assumption_id="assumption_gpu_memory",
                statement="GPU memory is sufficient for the selected model.",
                status="assumed",
                plan_id="plan-a",
            ),
        )

        result = deliberate_plan_selection(
            candidate_plans=self._plans(),
            evidence_store={"version": 1, "facts": {"vision_model_installed": {"state_type": "configured", "value": True}}},
            assumption_store=assumption_store,
        )
        self.assertTrue(result["candidate_plans"])
        self.assertIn(result["recommendation"]["status"], {"recommended", "proposed"})
        self.assertFalse(result["execution"]["enabled"])


if __name__ == "__main__":
    unittest.main()
