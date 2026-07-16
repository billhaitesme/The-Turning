import unittest

from services.deliberation_pipeline import run_deliberation_pipeline
from services.planning_pipeline import run_planning_pipeline


class DeliberationPipelineTests(unittest.TestCase):
    def _goal_store(self):
        return {
            "version": 1,
            "goals": [
                {
                    "id": "goal-add-vision-routing",
                    "title": "Add vision routing",
                    "status": "active",
                    "priority": "high",
                }
            ],
        }

    def test_alternative_generation_and_comparison(self):
        planning = run_planning_pipeline(
            goal_store=self._goal_store(),
            evidence_store={"version": 1, "facts": {}},
            reasoning_result={},
            plan_store={"version": 1, "plans": []},
            decision_store={"version": 1, "decisions": []},
            persist=False,
        )
        result = run_deliberation_pipeline(
            goal_store=self._goal_store(),
            planning_result=planning,
            evidence_store={"version": 1, "facts": {}},
            user_message="Show me another approach.",
            decision_store={"version": 1, "decisions": []},
            persist=False,
        )
        self.assertGreaterEqual(len(result["candidate_plans"]), 3)
        self.assertTrue(result["deliberation"]["decision_matrix"]["rows"])
        self.assertFalse(result["execution_enabled"])

    def test_user_approval_records_decision_without_execution(self):
        planning = run_planning_pipeline(
            goal_store=self._goal_store(),
            evidence_store={"version": 1, "facts": {}},
            reasoning_result={},
            plan_store={"version": 1, "plans": []},
            decision_store={"version": 1, "decisions": []},
            persist=False,
        )
        result = run_deliberation_pipeline(
            goal_store=self._goal_store(),
            planning_result=planning,
            evidence_store={"version": 1, "facts": {}},
            user_message="I approve this recommendation.",
            decision_store={"version": 1, "decisions": []},
            persist=False,
        )
        self.assertIsNotNone(result["approval"])
        self.assertEqual(result["approval"]["status"], "approved")
        self.assertFalse(result["execution_enabled"])

    def test_regression_existing_planning_behavior_remains(self):
        result = run_planning_pipeline(
            goal_store=self._goal_store(),
            evidence_store={"version": 1, "facts": {}},
            reasoning_result={},
            plan_store={"version": 1, "plans": []},
            decision_store={"version": 1, "decisions": []},
            user_message="What is my current plan?",
            persist=False,
        )
        self.assertTrue(result["plans"])

    def test_assumption_invalidation_intent_marks_assumption_invalidated(self):
        planning = run_planning_pipeline(
            goal_store=self._goal_store(),
            evidence_store={"version": 1, "facts": {}},
            reasoning_result={},
            plan_store={"version": 1, "plans": []},
            decision_store={"version": 1, "decisions": []},
            persist=False,
        )
        result = run_deliberation_pipeline(
            goal_store=self._goal_store(),
            planning_result=planning,
            evidence_store={"version": 1, "facts": {}},
            user_message="The GPU memory assumption was wrong.",
            decision_store={"version": 1, "decisions": []},
            persist=False,
        )
        assumptions = ((result.get("deliberation") or {}).get("assumptions") or {}).get("all") or []
        invalidated = [item for item in assumptions if str(item.get("status") or "") == "invalidated"]
        self.assertTrue(invalidated)

    def test_approval_supersedes_prior_active_decision(self):
        planning = run_planning_pipeline(
            goal_store=self._goal_store(),
            evidence_store={"version": 1, "facts": {}},
            reasoning_result={},
            plan_store={"version": 1, "plans": []},
            decision_store={"version": 1, "decisions": []},
            persist=False,
        )
        first = run_deliberation_pipeline(
            goal_store=self._goal_store(),
            planning_result=planning,
            evidence_store={"version": 1, "facts": {}},
            user_message="I approve this recommendation.",
            decision_store={"version": 1, "decisions": []},
            persist=False,
        )
        existing_decision = first.get("decision")
        decision_store = {"version": 1, "decisions": [existing_decision]} if isinstance(existing_decision, dict) else {"version": 1, "decisions": []}

        second = run_deliberation_pipeline(
            goal_store=self._goal_store(),
            planning_result={
                **planning,
                "selected_plan": {
                    **planning.get("selected_plan", {}),
                    "id": "plan-add-vision-routing-alt-qwen",
                },
            },
            evidence_store={"version": 1, "facts": {}},
            user_message="I approve this recommendation.",
            decision_store=decision_store,
            persist=False,
        )
        self.assertIsNotNone(second.get("decision"))


if __name__ == "__main__":
    unittest.main()
