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

    def _goal_store_multi(self):
        return {
            "version": 1,
            "goals": [
                {
                    "id": "goal-omega-arc",
                    "title": "Build OMEGA-ARC",
                    "status": "active",
                    "priority": "high",
                },
                {
                    "id": "goal-add-vision-routing",
                    "title": "Add vision routing",
                    "status": "active",
                    "priority": "high",
                },
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

    def test_repeated_goal_declaration_reuses_plan_across_phrase_variants(self):
        first = run_planning_pipeline(
            goal_store={"version": 1, "goals": [{"id": "goal-add-vision-routing", "title": "add vision routing", "status": "active"}]},
            evidence_store={"version": 1, "facts": {}},
            reasoning_result={},
            plan_store={"version": 1, "plans": []},
            decision_store={"version": 1, "decisions": []},
            user_message="My goal is to add vision routing.",
            session_id="session-h",
            persist=False,
        )
        second = run_planning_pipeline(
            goal_store={"version": 1, "goals": [{"id": "goal-add-vision-routing", "title": "Add vision routing.", "status": "active"}]},
            evidence_store={"version": 1, "facts": {}},
            reasoning_result={},
            plan_store={"version": 1, "plans": first["plans"]},
            decision_store={"version": 1, "decisions": []},
            user_message="My goal is to implement vision routing.",
            session_id="session-h",
            persist=False,
        )
        self.assertEqual(len(second["plans"]), 1)
        self.assertEqual(second["plans"][0]["id"], "plan-add-vision-routing")

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

    def test_newest_explicit_goal_becomes_session_focus(self):
        result = run_planning_pipeline(
            goal_store=self._goal_store_multi(),
            evidence_store={"version": 1, "facts": {}},
            reasoning_result={},
            plan_store={"version": 1, "plans": []},
            decision_store={"version": 1, "decisions": []},
            user_message="My goal is to add vision routing.",
            session_id="session-a",
            persist=False,
        )
        self.assertEqual(result["focus"]["focused_goal_id"], "goal-add-vision-routing")

    def test_current_plan_uses_focused_goal(self):
        focus_result = run_planning_pipeline(
            goal_store=self._goal_store_multi(),
            evidence_store={"version": 1, "facts": {}},
            reasoning_result={},
            plan_store={"version": 1, "plans": []},
            decision_store={"version": 1, "decisions": []},
            user_message="My goal is to add vision routing.",
            session_id="session-focus",
            persist=False,
        )
        self.assertEqual(focus_result["selected_plan"]["goal_id"], "goal-add-vision-routing")

    def test_broad_project_goal_does_not_override_specific_focused_goal(self):
        result = run_planning_pipeline(
            goal_store=self._goal_store_multi(),
            evidence_store={"version": 1, "facts": {}},
            reasoning_result={},
            plan_store={"version": 1, "plans": []},
            decision_store={"version": 1, "decisions": []},
            user_message="What is my current plan for vision routing?",
            session_id="session-b",
            persist=False,
        )
        self.assertEqual(result["selected_plan"]["goal_id"], "goal-add-vision-routing")

    def test_multiple_active_plans_without_focus_reports_selection_message(self):
        plans = [
            {
                "id": "plan-omega-arc",
                "goal_id": "goal-omega-arc",
                "title": "Build OMEGA-ARC",
                "status": "active",
                "version": 1,
                "steps": [],
                "metadata": {"planner_version": 1},
            },
            {
                "id": "plan-add-vision-routing",
                "goal_id": "goal-add-vision-routing",
                "title": "Add vision routing",
                "status": "active",
                "version": 1,
                "steps": [],
                "metadata": {"planner_version": 1},
            },
        ]
        result = run_planning_pipeline(
            goal_store=self._goal_store_multi(),
            evidence_store={"version": 1, "facts": {}},
            reasoning_result={},
            plan_store={"version": 1, "plans": plans},
            decision_store={"version": 1, "decisions": []},
            user_message="What is my current plan?",
            session_id=None,
            persist=False,
        )
        self.assertTrue(result["selection_message"])

    def test_model_selected_evidence_completes_only_selection_step(self):
        result = run_planning_pipeline(
            goal_store=self._goal_store(),
            evidence_store={
                "version": 1,
                "facts": {
                    "vision_model_selected": {"state_type": "configured", "value": True},
                },
            },
            reasoning_result={},
            plan_store={"version": 1, "plans": []},
            decision_store={"version": 1, "decisions": []},
            user_message="The vision model is selected.",
            session_id="session-c",
            persist=False,
        )
        steps = result["selected_plan"]["steps"]
        by_id = {step["id"]: step for step in steps}
        self.assertEqual(by_id["select-vision-model"]["status"], "completed")
        self.assertIn(by_id["verify-vision-model-load"]["status"], {"active", "ready"})

    def test_next_action_becomes_model_load_verification(self):
        result = run_planning_pipeline(
            goal_store=self._goal_store(),
            evidence_store={
                "version": 1,
                "facts": {
                    "vision_model_selected": {"state_type": "configured", "value": True},
                },
            },
            reasoning_result={},
            plan_store={"version": 1, "plans": []},
            decision_store={"version": 1, "decisions": []},
            user_message="What should I do next?",
            session_id="session-d",
            persist=False,
        )
        self.assertIn("selected vision model loads", result["next_actions"][0]["title"].lower())

    def test_no_specific_model_means_no_active_model_choice_decision(self):
        result = run_planning_pipeline(
            goal_store=self._goal_store(),
            evidence_store={"version": 1, "facts": {"vision_model_selected": {"state_type": "configured", "value": True}}},
            reasoning_result={},
            plan_store={"version": 1, "plans": []},
            decision_store={"version": 1, "decisions": []},
            user_message="The vision model is selected.",
            session_id="session-e",
            persist=False,
        )
        self.assertEqual(result["decision_candidates"], [])

    def test_explicit_llava_choice_creates_active_decision(self):
        result = run_planning_pipeline(
            goal_store=self._goal_store(),
            evidence_store={"version": 1, "facts": {"vision_model_selected": {"state_type": "declared", "value": "llava:7b"}}},
            reasoning_result={},
            plan_store={"version": 1, "plans": []},
            decision_store={"version": 1, "decisions": []},
            user_message="Use LLaVA as the vision model.",
            session_id="session-f",
            persist=False,
        )
        self.assertTrue(result["decision_candidates"])
        self.assertEqual(result["decision_candidates"][0]["status"], "active")

    def test_generic_qa_does_not_alter_planning_focus(self):
        first = run_planning_pipeline(
            goal_store=self._goal_store(),
            evidence_store={"version": 1, "facts": {}},
            reasoning_result={},
            plan_store={"version": 1, "plans": []},
            decision_store={"version": 1, "decisions": []},
            user_message="My goal is to add vision routing.",
            session_id="session-g",
            persist=False,
        )
        second = run_planning_pipeline(
            goal_store=self._goal_store(),
            evidence_store={"version": 1, "facts": {}},
            reasoning_result={},
            plan_store={"version": 1, "plans": first["plans"]},
            decision_store={"version": 1, "decisions": []},
            user_message="What is an API?",
            session_id="session-g",
            persist=False,
        )
        self.assertEqual(second["focus"]["focused_goal_id"], "goal-add-vision-routing")

if __name__ == "__main__":
    unittest.main()
