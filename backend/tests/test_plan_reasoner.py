import unittest

from services.plan_reasoner import evaluate_plan, evaluate_step


class PlanReasonerTests(unittest.TestCase):
    def _plan(self):
        return {
            "id": "plan-a",
            "goal_id": "goal-a",
            "title": "Plan A",
            "status": "active",
            "steps": [
                {
                    "id": "configure",
                    "title": "Configure",
                    "status": "pending",
                    "order": 1,
                    "required": True,
                    "dependencies": [],
                    "evidence_requirements": [
                        {
                            "key": "router_configured",
                            "required_state_types": ["configured", "verified"],
                            "required_value": True,
                        }
                    ],
                    "completion_evidence": [],
                    "blockers": [],
                },
                {
                    "id": "runtime-check",
                    "title": "Runtime check",
                    "status": "pending",
                    "order": 2,
                    "required": True,
                    "dependencies": ["configure"],
                    "evidence_requirements": [
                        {
                            "key": "router_online",
                            "required_state_types": ["observed", "verified"],
                            "required_value": True,
                        }
                    ],
                    "completion_evidence": [],
                    "blockers": [],
                },
            ],
        }

    def test_configured_evidence_satisfies_configuration_requirement(self):
        step = self._plan()["steps"][0]
        result = evaluate_step(
            step=step,
            plan=self._plan(),
            evidence_store={"facts": {"router_configured": {"state_type": "configured", "value": True}}},
            reasoning_result={},
        )
        self.assertEqual(result["status"], "completed")

    def test_declaration_does_not_satisfy_verified_runtime_requirement(self):
        step = self._plan()["steps"][1]
        plan = self._plan()
        plan["steps"][0]["status"] = "completed"
        result = evaluate_step(
            step=step,
            plan=plan,
            evidence_store={"facts": {"router_online": {"state_type": "declared", "value": True}}},
            reasoning_result={},
        )
        self.assertEqual(result["status"], "blocked")

    def test_verified_evidence_completes_step(self):
        step = self._plan()["steps"][0]
        result = evaluate_step(
            step=step,
            plan=self._plan(),
            evidence_store={"facts": {"router_configured": {"state_type": "verified", "value": True}}},
            reasoning_result={},
        )
        self.assertEqual(result["status"], "completed")

    def test_expired_evidence_does_not_complete_step(self):
        step = self._plan()["steps"][0]
        result = evaluate_step(
            step=step,
            plan=self._plan(),
            evidence_store={"facts": {"router_configured": {"state_type": "expired", "value": True}}},
            reasoning_result={},
        )
        self.assertEqual(result["status"], "blocked")

    def test_invalidated_evidence_reopens_step(self):
        plan = self._plan()
        plan["steps"][0]["status"] = "completed"
        plan["steps"][0]["completion_evidence"] = [{"key": "router_configured"}]
        result = evaluate_plan(
            plan=plan,
            evidence_store={"facts": {"router_configured": {"state_type": "invalidated", "value": True}}},
            reasoning_result={},
        )
        step = next(item for item in result["plan"]["steps"] if item["id"] == "configure")
        self.assertEqual(step["status"], "blocked")

    def test_one_ready_step_becomes_active(self):
        plan = self._plan()
        plan["steps"][1]["evidence_requirements"] = []
        result = evaluate_plan(
            plan=plan,
            evidence_store={"facts": {"router_configured": {"state_type": "verified", "value": True}}},
            reasoning_result={},
        )
        self.assertEqual(result["next_step"]["id"], "runtime-check")
        runtime_step = next(item for item in result["plan"]["steps"] if item["id"] == "runtime-check")
        self.assertEqual(runtime_step["status"], "active")

    def test_blocked_dependencies_are_listed(self):
        result = evaluate_plan(plan=self._plan(), evidence_store={"facts": {}}, reasoning_result={})
        self.assertTrue(result["blocked_steps"])

    def test_completed_plan_requires_all_required_steps_complete(self):
        plan = self._plan()
        result = evaluate_plan(
            plan=plan,
            evidence_store={
                "facts": {
                    "router_configured": {"state_type": "verified", "value": True},
                    "router_online": {"state_type": "verified", "value": True},
                }
            },
            reasoning_result={},
        )
        self.assertEqual(result["plan"]["status"], "completed")


if __name__ == "__main__":
    unittest.main()
