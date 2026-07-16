import unittest

from services.plan_graph import build_plan_graph


class PlanningGraphTests(unittest.TestCase):
    def test_builds_linear_graph_with_goal_completion_node(self):
        graph = build_plan_graph(
            goal_id="goal-vision-routing",
            goal_title="Add vision routing",
            steps=[
                {"id": "vision_model_selected", "title": "Select a vision model"},
                {"id": "vision_model_loaded", "title": "Verify the model loads correctly"},
                {"id": "vision_router_configured", "title": "Configure the routing pipeline"},
            ],
        )

        node_ids = [node["id"] for node in graph["nodes"]]
        self.assertIn("vision_model_selected", node_ids)
        self.assertIn("goal-vision-routing:complete", node_ids)

        self.assertEqual(
            graph["edges"],
            [
                {"from": "vision_model_selected", "to": "vision_model_loaded"},
                {"from": "vision_model_loaded", "to": "vision_router_configured"},
                {"from": "vision_router_configured", "to": "goal-vision-routing:complete"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
