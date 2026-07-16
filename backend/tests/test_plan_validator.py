import unittest

from services.plan_validator import validate_plan


class PlanValidatorTests(unittest.TestCase):
    def _base_plan(self):
        return {
            "id": "plan-a",
            "goal_id": "goal-a",
            "title": "Plan A",
            "status": "active",
            "created_at": "2026-07-15T00:00:00Z",
            "updated_at": "2026-07-15T00:00:00Z",
            "steps": [
                {
                    "id": "step-1",
                    "title": "Step 1",
                    "status": "pending",
                    "required": True,
                    "dependencies": [],
                    "evidence_requirements": [
                        {
                            "key": "k1",
                            "required_state_types": ["verified"],
                            "required_value": True,
                        }
                    ],
                    "completion_evidence": [],
                    "blockers": [],
                }
            ],
        }

    def test_valid_plan_passes(self):
        result = validate_plan(self._base_plan())
        self.assertTrue(result["valid"])

    def test_duplicate_steps_fail(self):
        plan = self._base_plan()
        plan["steps"].append(dict(plan["steps"][0]))
        result = validate_plan(plan)
        self.assertFalse(result["valid"])

    def test_missing_goal_id_fails(self):
        plan = self._base_plan()
        plan["goal_id"] = ""
        result = validate_plan(plan)
        self.assertFalse(result["valid"])

    def test_invalid_status_fails(self):
        plan = self._base_plan()
        plan["status"] = "unknown"
        result = validate_plan(plan)
        self.assertFalse(result["valid"])

    def test_completed_step_without_evidence_fails(self):
        plan = self._base_plan()
        plan["steps"][0]["status"] = "completed"
        result = validate_plan(plan)
        self.assertFalse(result["valid"])

    def test_completed_plan_with_incomplete_required_step_fails(self):
        plan = self._base_plan()
        plan["status"] = "completed"
        result = validate_plan(plan)
        self.assertFalse(result["valid"])

    def test_blocked_step_without_blocker_fails(self):
        plan = self._base_plan()
        plan["steps"][0]["status"] = "blocked"
        plan["steps"][0]["blockers"] = []
        result = validate_plan(plan)
        self.assertFalse(result["valid"])


if __name__ == "__main__":
    unittest.main()
