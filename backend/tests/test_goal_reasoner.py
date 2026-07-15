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
        self.assertEqual(blockers[0]["blockers"][0]["key"], "vision_model_ready")

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
        self.assertEqual(blockers[0]["blockers"][0]["reason"], "Configured-only readiness does not satisfy runtime requirement.")

    def test_progress_one_does_not_imply_verified_completion(self):
        result = evaluate_goal_completion(
            {"id": "goal-vision", "title": "Add vision routing", "progress": 1.0, "status": "active"},
            {"version": 1, "records": {}},
        )
        self.assertEqual(result["status"], "completion_unverified")


if __name__ == "__main__":
    unittest.main()
