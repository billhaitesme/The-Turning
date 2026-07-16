import unittest

from services.goal_reasoner import evaluate_goal_blockers, evaluate_goal_completion


class GoalReasonerTests(unittest.TestCase):
    def test_goal_without_dependencies_is_not_blocked(self):
        blockers = evaluate_goal_blockers(
            {"goals": [{"id": "goal-1", "title": "General goal", "dependencies": []}]},
            [],
        )
        self.assertEqual(blockers, [])

    def test_missing_dependency_blocks_goal(self):
        blockers = evaluate_goal_blockers(
            {"goals": [{"id": "goal-vision", "title": "Add vision routing", "dependencies": ["vision_model_ready"]}]},
            [],
        )
        self.assertEqual(blockers[0]["status"], "blocked")
        self.assertEqual(blockers[0]["completion"], "unverified")
        self.assertEqual(blockers[0]["blockers"][0]["key"], "vision_model_ready")
        self.assertEqual(blockers[0]["blockers"][0]["reason"], "Missing readiness evidence for this dependency.")

    def test_unknown_dependency_blocks_goal(self):
        blockers = evaluate_goal_blockers(
            {"goals": [{"id": "goal-vision", "title": "Add vision routing", "dependencies": ["vision_model_ready"]}]},
            [{"key": "vision_model_ready", "status": "unknown", "state_type": "unknown", "value": None}],
        )
        self.assertEqual(blockers[0]["blockers"][0]["reason"], "Current evidence is unknown.")

    def test_verified_dependency_satisfies_goal(self):
        blockers = evaluate_goal_blockers(
            {"goals": [{"id": "goal-vision", "title": "Add vision routing", "dependencies": ["vision_model_ready"]}]},
            [{"key": "vision_model_ready", "status": "resolved", "state_type": "verified", "value": True}],
        )
        self.assertEqual(blockers, [])

    def test_configured_only_readiness_does_not_satisfy_runtime_requirement(self):
        blockers = evaluate_goal_blockers(
            {"goals": [{"id": "goal-vision", "title": "Add vision routing", "dependencies": ["vision_model_ready"]}]},
            [{"key": "vision_model_ready", "status": "resolved", "state_type": "configured", "value": True}],
        )
        self.assertEqual(blockers[0]["blockers"][0]["reason"], "Declared or configured evidence does not satisfy verified runtime readiness.")

    def test_installed_does_not_imply_available(self):
        blockers = evaluate_goal_blockers(
            {"goals": [{"id": "goal-vision", "title": "Add vision routing", "dependencies": ["vision_model_available"]}]},
            [{"key": "vision_model_installed", "status": "resolved", "state_type": "declared", "value": True}],
        )
        self.assertEqual(blockers[0]["blockers"][0]["key"], "vision_model_available")

    def test_available_does_not_imply_loaded(self):
        blockers = evaluate_goal_blockers(
            {"goals": [{"id": "goal-vision", "title": "Add vision routing", "dependencies": ["vision_model_loaded"]}]},
            [{"key": "vision_model_available", "status": "resolved", "state_type": "verified", "value": True}],
        )
        self.assertEqual(blockers[0]["blockers"][0]["key"], "vision_model_loaded")

    def test_loaded_does_not_imply_healthy(self):
        blockers = evaluate_goal_blockers(
            {"goals": [{"id": "goal-vision", "title": "Add vision routing", "dependencies": ["vision_model_healthy"]}]},
            [{"key": "vision_model_loaded", "status": "resolved", "state_type": "verified", "value": True}],
        )
        self.assertEqual(blockers[0]["blockers"][0]["key"], "vision_model_healthy")

    def test_healthy_does_not_imply_routing_verified(self):
        blockers = evaluate_goal_blockers(
            {"goals": [{"id": "goal-vision", "title": "Add vision routing", "dependencies": ["vision_routing_verified"]}]},
            [{"key": "vision_model_healthy", "status": "resolved", "state_type": "verified", "value": True}],
        )
        self.assertEqual(blockers[0]["blockers"][0]["key"], "vision_routing_verified")

    def test_missing_dependency_blocks_readiness(self):
        blockers = evaluate_goal_blockers(
            {
                "goals": [
                    {
                        "id": "goal-vision",
                        "title": "Add vision routing",
                        "dependencies": ["vision_model_loaded", "vision_model_healthy", "vision_router_configured", "vision_routing_verified"],
                    }
                ]
            },
            [
                {"key": "vision_model_loaded", "status": "resolved", "state_type": "verified", "value": True},
                {"key": "vision_model_healthy", "status": "resolved", "state_type": "verified", "value": True},
            ],
        )
        blocked_keys = {item["key"] for item in blockers[0]["blockers"]}
        self.assertIn("vision_router_configured", blocked_keys)
        self.assertIn("vision_routing_verified", blocked_keys)

    def test_all_verified_dependencies_allow_ready(self):
        blockers = evaluate_goal_blockers(
            {
                "goals": [
                    {
                        "id": "goal-vision",
                        "title": "Add vision routing",
                        "dependencies": ["vision_model_selected", "vision_model_loaded", "vision_model_healthy", "vision_router_configured", "vision_routing_verified"],
                    }
                ]
            },
            [
                {"key": "vision_model_selected", "status": "resolved", "state_type": "verified", "value": True},
                {"key": "vision_model_loaded", "status": "resolved", "state_type": "verified", "value": True},
                {"key": "vision_model_healthy", "status": "resolved", "state_type": "verified", "value": True},
                {"key": "vision_router_configured", "status": "resolved", "state_type": "verified", "value": True},
                {"key": "vision_routing_verified", "status": "resolved", "state_type": "verified", "value": True},
            ],
        )
        self.assertEqual(blockers, [])

    def test_progress_one_does_not_imply_verified_completion(self):
        result = evaluate_goal_completion(
            {"id": "goal-vision", "title": "Add vision routing", "progress": 1.0, "status": "active"},
            {"version": 1, "records": {}},
        )
        self.assertEqual(result["status"], "completion_unverified")


if __name__ == "__main__":
    unittest.main()
