import unittest

from services.plan_reviser import revise_plan


class PlanReviserTests(unittest.TestCase):
    def _plan(self):
        return {
            "id": "plan-add-vision-routing",
            "goal_id": "goal-add-vision-routing",
            "title": "Add vision routing",
            "status": "active",
            "version": 1,
            "metadata": {
                "selected_model": "llava:7b",
                "backend_port": 8001,
            },
            "steps": [
                {"id": "select-vision-model", "status": "completed", "completion_evidence": [{"key": "vision_model_selected"}]},
                {"id": "verify-vision-model-load", "status": "completed", "completion_evidence": [{"key": "vision_model_loaded"}]},
                {"id": "verify-vision-model-response", "status": "completed", "completion_evidence": [{"key": "vision_model_responding"}]},
                {"id": "run-end-to-end-routing-test", "status": "completed", "completion_evidence": [{"key": "vision_routing_verified"}], "endpoint_bound": True},
            ],
        }

    def test_changed_model_invalidates_readiness_steps(self):
        result = revise_plan(
            plan=self._plan(),
            evidence_store={"facts": {"vision_model_selected": {"value": "qwen2.5-vl"}}},
            reasoning_result={},
        )
        self.assertTrue(result["changed"])
        self.assertIn("verify-vision-model-load", result["invalidated_steps"])

    def test_changed_endpoint_invalidates_endpoint_bound_verification(self):
        result = revise_plan(
            plan=self._plan(),
            evidence_store={"facts": {"backend_port": {"value": 8002}}},
            reasoning_result={},
        )
        self.assertTrue(result["changed"])
        self.assertIn("run-end-to-end-routing-test", result["invalidated_steps"])

    def test_plan_version_increments(self):
        result = revise_plan(
            plan=self._plan(),
            evidence_store={"facts": {"backend_port": {"value": 8002}}},
            reasoning_result={},
        )
        self.assertEqual(result["plan"]["version"], 2)

    def test_unchanged_evidence_creates_no_revision(self):
        result = revise_plan(
            plan=self._plan(),
            evidence_store={"facts": {"vision_model_selected": {"value": "llava:7b"}, "backend_port": {"value": 8001}}},
            reasoning_result={},
        )
        self.assertFalse(result["changed"])

    def test_routine_revision_preserves_plan_id(self):
        result = revise_plan(
            plan=self._plan(),
            evidence_store={"facts": {"backend_port": {"value": 8002}}},
            reasoning_result={},
        )
        self.assertEqual(result["plan"]["id"], "plan-add-vision-routing")

    def test_structural_replacement_supersedes_old_plan(self):
        plan = self._plan()
        plan["metadata"]["structurally_unusable"] = True
        result = revise_plan(
            plan=plan,
            evidence_store={"facts": {}},
            reasoning_result={},
        )
        self.assertTrue(result["changed"])
        self.assertEqual(result["old_plan"]["status"], "superseded")
        self.assertEqual(result["replacement_plan"]["supersedes"], "plan-add-vision-routing")


if __name__ == "__main__":
    unittest.main()
