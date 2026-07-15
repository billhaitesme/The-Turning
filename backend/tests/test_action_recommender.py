import unittest

from services.action_recommender import recommend_actions


class ActionRecommenderTests(unittest.TestCase):
    def test_unknown_health_recommends_health_check(self):
        actions = recommend_actions(
            resolved_beliefs=[],
            conflicts=[],
            uncertainties=[{"key": "backend_health", "status": "unknown", "reason": "Current health is unknown."}],
            blocked_goals=[],
        )
        self.assertEqual(actions[0]["action"], "run_health_check")
        self.assertTrue(actions[0]["requires_confirmation"])

    def test_stale_evidence_recommends_refresh(self):
        actions = recommend_actions(
            resolved_beliefs=[],
            conflicts=[],
            uncertainties=[{"key": "backend_health", "status": "stale", "reason": "Health check is stale."}],
            blocked_goals=[],
        )
        self.assertEqual(actions[0]["action"], "refresh_evidence")

    def test_conflict_recommends_review(self):
        actions = recommend_actions(
            resolved_beliefs=[],
            conflicts=[{"key": "backend_port", "reason": "Two current configured values conflict."}],
            uncertainties=[],
            blocked_goals=[],
        )
        self.assertEqual(actions[0]["action"], "review_conflict")

    def test_blocked_goal_recommends_resolving_blocker(self):
        actions = recommend_actions(
            resolved_beliefs=[],
            conflicts=[],
            uncertainties=[],
            blocked_goals=[{"goal_id": "goal-vision", "title": "Add vision routing", "blockers": [{"key": "vision_model_ready", "reason": "Current readiness is unknown."}]}],
        )
        self.assertEqual(actions[0]["action"], "resolve_goal_blocker")

    def test_no_duplicate_recommendations(self):
        actions = recommend_actions(
            resolved_beliefs=[],
            conflicts=[],
            uncertainties=[
                {"key": "backend_health", "status": "unknown", "reason": "Current health is unknown."},
                {"key": "backend_health", "status": "unknown", "reason": "Current health is unknown."},
            ],
            blocked_goals=[],
        )
        self.assertEqual(len(actions), 1)

    def test_all_recommendations_require_confirmation(self):
        actions = recommend_actions(
            resolved_beliefs=[],
            conflicts=[{"key": "backend_port", "reason": "Two current configured values conflict."}],
            uncertainties=[{"key": "backend_health", "status": "unknown", "reason": "Current health is unknown."}],
            blocked_goals=[{"goal_id": "goal-vision", "title": "Add vision routing", "blockers": [{"key": "vision_model_ready", "reason": "Current readiness is unknown."}]}],
        )
        self.assertTrue(all(action["requires_confirmation"] for action in actions))


if __name__ == "__main__":
    unittest.main()
