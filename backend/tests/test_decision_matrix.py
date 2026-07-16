import unittest

from services.decision_matrix import build_decision_matrix


class DecisionMatrixTests(unittest.TestCase):
    def test_decision_matrix_is_deterministic_and_explainable(self):
        comparison = {
            "comparison": [
                {
                    "plan_id": "plan-a",
                    "title": "Plan A",
                    "criteria": {
                        "installation_state": "strong",
                        "dependency_count": 2,
                        "evidence_completeness": "strong",
                        "implementation_complexity": "medium",
                        "estimated_risk": "low",
                        "confidence": "high",
                    },
                },
                {
                    "plan_id": "plan-b",
                    "title": "Plan B",
                    "criteria": {
                        "installation_state": "weak",
                        "dependency_count": 6,
                        "evidence_completeness": "moderate",
                        "implementation_complexity": "high",
                        "estimated_risk": "high",
                        "confidence": "medium",
                    },
                },
            ],
            "selected_plan_id": "plan-a",
        }
        matrix = build_decision_matrix(comparison)
        self.assertTrue(matrix["rows"])
        first_row = matrix["rows"][0]
        self.assertIn("criterion", first_row)
        self.assertIn("weight", first_row)
        self.assertIn("scores", first_row)
        self.assertEqual(matrix["selected_plan_id"], "plan-a")


if __name__ == "__main__":
    unittest.main()
