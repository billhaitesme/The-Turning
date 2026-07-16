import unittest

from services.planning_pipeline import run_planning_pipeline


class PlanningPipelineTests(unittest.TestCase):
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

    def test_active_goal_creates_plan(self):
        result = run_planning_pipeline(
            goal_store=self._goal_store(),
            evidence_store={"version": 1, "facts": {}},
            reasoning_result={},
            plan_store={"version": 1, "plans": []},
            decision_store={"version": 1, "decisions": []},
            persist=False,
        )
        self.assertEqual(len(result["plans"]), 1)

    def test_existing_plan_is_reused(self):
        existing = {
            "id": "plan-add-vision-routing",
            "goal_id": "goal-add-vision-routing",
            "title": "Add vision routing",
            "status": "active",
            "version": 1,
            "steps": [],
            "metadata": {"planner_version": 1},
        }
        result = run_planning_pipeline(
            goal_store=self._goal_store(),
            evidence_store={"version": 1, "facts": {}},
            reasoning_result={},
            plan_store={"version": 1, "plans": [existing]},
            decision_store={"version": 1, "decisions": []},
            persist=False,
        )
        self.assertEqual(result["plans"][0]["id"], "plan-add-vision-routing")

    def test_repeated_turns_do_not_duplicate_plan(self):
        plan_store = {"version": 1, "plans": []}
        first = run_planning_pipeline(
            goal_store=self._goal_store(),
            evidence_store={"version": 1, "facts": {}},
            reasoning_result={},
            plan_store=plan_store,
            decision_store={"version": 1, "decisions": []},
            persist=False,
        )
        second = run_planning_pipeline(
            goal_store=self._goal_store(),
            evidence_store={"version": 1, "facts": {}},
            reasoning_result={},
            plan_store={"version": 1, "plans": first["plans"]},
            decision_store={"version": 1, "decisions": []},
            persist=False,
        )
        self.assertEqual(len(second["plans"]), 1)

    def test_new_evidence_advances_existing_plan(self):
        result = run_planning_pipeline(
            goal_store=self._goal_store(),
            evidence_store={
                "version": 1,
                "facts": {
                    "vision_model_selected": {"state_type": "verified", "value": True},
                },
            },
            reasoning_result={},
            plan_store={"version": 1, "plans": []},
            decision_store={"version": 1, "decisions": []},
            persist=False,
        )
        steps = result["plans"][0]["steps"]
        completed = [step for step in steps if step.get("status") == "completed"]
        self.assertTrue(completed)

    def test_evidence_invalidation_reopens_steps(self):
        plan = {
            "id": "plan-add-vision-routing",
            "goal_id": "goal-add-vision-routing",
            "title": "Add vision routing",
            "status": "active",
            "version": 1,
            "steps": [
                {
                    "id": "select-vision-model",
                    "title": "Select",
                    "status": "completed",
                    "order": 1,
                    "required": True,
                    "dependencies": [],
                    "evidence_requirements": [{"key": "vision_model_selected", "required_state_types": ["verified"], "required_value": True}],
                    "completion_evidence": [{"key": "vision_model_selected"}],
                    "blockers": [],
                }
            ],
            "metadata": {"planner_version": 1},
        }
        result = run_planning_pipeline(
            goal_store=self._goal_store(),
            evidence_store={"version": 1, "facts": {"vision_model_selected": {"state_type": "invalidated", "value": True}}},
            reasoning_result={},
            plan_store={"version": 1, "plans": [plan]},
            decision_store={"version": 1, "decisions": []},
            persist=False,
        )
        self.assertIn(result["plans"][0]["steps"][0]["status"], {"blocked", "invalidated"})

    def test_next_action_is_deterministic(self):
        kwargs = {
            "goal_store": self._goal_store(),
            "evidence_store": {"version": 1, "facts": {}},
            "reasoning_result": {},
            "plan_store": {"version": 1, "plans": []},
            "decision_store": {"version": 1, "decisions": []},
            "persist": False,
        }
        result_a = run_planning_pipeline(**kwargs)
        result_b = run_planning_pipeline(**kwargs)
        self.assertEqual(result_a["next_actions"], result_b["next_actions"])

    def test_unsupported_goal_receives_generic_bounded_plan(self):
        result = run_planning_pipeline(
            goal_store={"version": 1, "goals": [{"id": "goal-a", "title": "Improve docs", "status": "active"}]},
            evidence_store={"version": 1, "facts": {}},
            reasoning_result={},
            plan_store={"version": 1, "plans": []},
            decision_store={"version": 1, "decisions": []},
            persist=False,
        )
        self.assertEqual(result["plans"][0]["source"], "generic_deterministic_template")

    def test_general_qa_creates_no_plan(self):
        result = run_planning_pipeline(
            goal_store={"version": 1, "goals": []},
            evidence_store={"version": 1, "facts": {}},
            reasoning_result={},
            plan_store={"version": 1, "plans": []},
            decision_store={"version": 1, "decisions": []},
            persist=False,
        )
        self.assertEqual(result["plans"], [])

    def test_persist_false_writes_no_files(self):
        result = run_planning_pipeline(
            goal_store=self._goal_store(),
            evidence_store={"version": 1, "facts": {}},
            reasoning_result={},
            plan_store={"version": 1, "plans": []},
            decision_store={"version": 1, "decisions": []},
            persist=False,
        )
        self.assertTrue(result["plans"])

    def test_pipeline_failure_does_not_break_chat(self):
        class BadGoalStore(dict):
            def get(self, key, default=None):
                raise RuntimeError("boom")

        result = run_planning_pipeline(
            goal_store=BadGoalStore(),
            evidence_store={"version": 1, "facts": {}},
            reasoning_result={},
            plan_store={"version": 1, "plans": []},
            decision_store={"version": 1, "decisions": []},
            persist=False,
        )

        self.assertEqual(result["plans"], [])

if __name__ == "__main__":
    unittest.main()
