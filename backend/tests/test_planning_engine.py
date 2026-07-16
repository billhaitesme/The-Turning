import unittest

from services.planning_engine import build_plan


class PlanningEngineTests(unittest.TestCase):
    def test_empty_goal_list_returns_no_plans(self):
        plans = build_plan([], {"version": 1, "facts": {}}, {})
        self.assertEqual(plans, [])

    def test_single_goal_generates_ordered_steps(self):
        plans = build_plan(
            [
                {
                    "id": "goal-vision-routing",
                    "title": "Add vision routing",
                    "status": "active",
                    "dependencies": [
                        "vision_model_selected",
                        "vision_model_loaded",
                        "vision_router_configured",
                        "vision_routing_verified",
                    ],
                }
            ],
            {
                "version": 1,
                "facts": {
                    "vision_model_selected": {
                        "state_type": "verified",
                        "value": True,
                    }
                },
            },
            {},
        )

        self.assertEqual(len(plans), 1)
        first_plan = plans[0]
        self.assertEqual(first_plan.goal, "Add vision routing")
        self.assertEqual(first_plan.status, "blocked")
        self.assertEqual(
            [step.id for step in first_plan.steps],
            ["vision_model_loaded", "vision_router_configured", "vision_routing_verified"],
        )

    def test_multiple_goals_are_supported(self):
        plans = build_plan(
            [
                {
                    "id": "goal-b",
                    "title": "B goal",
                    "status": "active",
                    "dependencies": ["b_dependency"],
                },
                {
                    "id": "goal-a",
                    "title": "A goal",
                    "status": "active",
                    "dependencies": ["a_dependency"],
                },
            ],
            {"version": 1, "facts": {}},
            {},
        )

        self.assertEqual([plan.goal for plan in plans], ["A goal", "B goal"])

    def test_blocker_detection_uses_verified_readiness(self):
        plans = build_plan(
            [
                {
                    "id": "goal-vision-routing",
                    "title": "Add vision routing",
                    "status": "active",
                    "dependencies": ["vision_model_loaded"],
                }
            ],
            {
                "version": 1,
                "facts": {
                    "vision_model_loaded": {
                        "state_type": "declared",
                        "value": True,
                    }
                },
            },
            {},
        )

        self.assertEqual(plans[0].status, "blocked")
        self.assertTrue(any("not verified runtime evidence" in blocker for blocker in plans[0].blockers))

    def test_completed_steps_are_removed(self):
        plans = build_plan(
            [
                {
                    "id": "goal-vision-routing",
                    "title": "Add vision routing",
                    "status": "active",
                    "dependencies": [
                        "vision_model_selected",
                        "vision_model_loaded",
                    ],
                }
            ],
            {
                "version": 1,
                "facts": {
                    "vision_model_selected": {
                        "state_type": "verified",
                        "value": True,
                    },
                    "vision_model_loaded": {
                        "state_type": "verified",
                        "value": True,
                    },
                },
            },
            {},
        )

        self.assertEqual(plans[0].steps, [])
        self.assertEqual(plans[0].status, "complete")

    def test_confidence_is_deterministic(self):
        plans_a = build_plan(
            [
                {
                    "id": "goal-a",
                    "title": "A goal",
                    "status": "active",
                    "dependencies": ["dep-a", "dep-b"],
                }
            ],
            {"version": 1, "facts": {"dep-a": {"state_type": "verified", "value": True}}},
            {},
        )
        plans_b = build_plan(
            [
                {
                    "id": "goal-a",
                    "title": "A goal",
                    "status": "active",
                    "dependencies": ["dep-a", "dep-b"],
                }
            ],
            {"version": 1, "facts": {"dep-a": {"state_type": "verified", "value": True}}},
            {},
        )
        self.assertEqual(plans_a[0].confidence, plans_b[0].confidence)


if __name__ == "__main__":
    unittest.main()
