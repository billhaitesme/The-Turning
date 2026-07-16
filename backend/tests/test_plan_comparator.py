import unittest

from services.plan_comparator import compare_candidate_plans


class PlanComparatorTests(unittest.TestCase):
    def test_multiple_candidate_plans_are_ranked(self):
        plans = [
            {
                "id": "plan-a",
                "title": "Use LLaVA",
                "steps": [{"id": "s1", "dependencies": []}],
                "metadata": {"confidence": 0.8},
            },
            {
                "id": "plan-b",
                "title": "Use Qwen2.5-VL",
                "steps": [{"id": "s1", "dependencies": ["x", "y", "z"]}],
                "metadata": {"confidence": 0.5},
            },
        ]
        comparison = compare_candidate_plans(
            candidate_plans=plans,
            evidence_store={"version": 1, "facts": {"vision_model_installed": {"state_type": "configured", "value": True}}},
            risk_by_plan={
                "plan-a": {"overall_risk": "low"},
                "plan-b": {"overall_risk": "high"},
            },
        )
        self.assertEqual(len(comparison["comparison"]), 2)
        self.assertEqual(comparison["selected_plan_id"], "plan-a")


if __name__ == "__main__":
    unittest.main()
