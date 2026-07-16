import unittest

from services.assumption_engine import create_assumption, upsert_assumption
from services.risk_engine import assess_plan_risks


class RiskEngineTests(unittest.TestCase):
    def _plan(self):
        return {
            "id": "plan-a",
            "goal_id": "goal-1",
            "title": "Plan A",
            "steps": [
                {"id": "s1", "dependencies": [], "evidence_requirements": [{"key": "vision_model_selected"}]},
                {"id": "s2", "dependencies": ["s1"], "evidence_requirements": [{"key": "vision_model_loaded"}]},
            ],
        }

    def test_deterministic_risk_generation(self):
        assumption_store = {"version": 1, "assumptions": []}
        result = assess_plan_risks(
            plan=self._plan(),
            evidence_store={
                "version": 1,
                "facts": {
                    "vision_model_selected": {"state_type": "declared", "value": True},
                },
            },
            assumption_store=assumption_store,
        )
        self.assertIn(result["overall_risk"], {"low", "medium", "high"})
        self.assertTrue(result["risks"])

    def test_assumed_statement_increases_risk(self):
        assumption_store = {"version": 1, "assumptions": []}
        assumption_store = upsert_assumption(
            assumption_store,
            create_assumption(
                assumption_id="assumption_gpu_memory",
                statement="GPU memory is sufficient.",
                status="assumed",
                plan_id="plan-a",
            ),
        )
        result = assess_plan_risks(
            plan=self._plan(),
            evidence_store={"version": 1, "facts": {}},
            assumption_store=assumption_store,
        )
        joined = "\n".join(item["risk"] for item in result["risks"])
        self.assertIn("Assumption remains unverified", joined)


if __name__ == "__main__":
    unittest.main()
