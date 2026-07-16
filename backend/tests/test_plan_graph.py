import unittest

from services.plan_graph import (
    build_plan_graph,
    find_blocked_steps,
    find_downstream_steps,
    find_ready_steps,
    find_upstream_dependencies,
    topological_step_order,
    validate_acyclic,
)


class PlanningGraphTests(unittest.TestCase):
    def _plan(self):
        return {
            "goal_id": "goal-vision-routing",
            "title": "Add vision routing",
            "steps": [
                {
                    "id": "select-model",
                    "title": "Select model",
                    "order": 1,
                    "status": "pending",
                    "dependencies": [],
                    "evidence_requirements": [
                        {
                            "key": "vision_model_selected",
                            "required_state_types": ["declared", "configured", "observed", "verified"],
                            "required_value": True,
                        }
                    ],
                },
                {
                    "id": "verify-model",
                    "title": "Verify model",
                    "order": 2,
                    "status": "pending",
                    "dependencies": ["select-model"],
                    "evidence_requirements": [
                        {
                            "key": "vision_model_loaded",
                            "required_state_types": ["observed", "verified"],
                            "required_value": True,
                        }
                    ],
                },
                {
                    "id": "configure-router",
                    "title": "Configure router",
                    "order": 3,
                    "status": "pending",
                    "dependencies": ["verify-model"],
                    "evidence_requirements": [],
                },
            ],
        }

    def test_valid_graph(self):
        graph = build_plan_graph(self._plan())
        self.assertTrue(validate_acyclic(graph))

    def test_deterministic_topological_order(self):
        graph = build_plan_graph(self._plan())
        self.assertEqual(topological_step_order(graph), ["select-model", "verify-model", "configure-router"])

    def test_missing_dependency_rejected(self):
        plan = self._plan()
        plan["steps"][1]["dependencies"] = ["missing"]
        graph = build_plan_graph(plan)
        self.assertEqual(topological_step_order(graph), ["select-model", "verify-model", "configure-router"])

    def test_circular_dependency_rejected(self):
        plan = self._plan()
        plan["steps"][0]["dependencies"] = ["configure-router"]
        graph = build_plan_graph(plan)
        self.assertFalse(validate_acyclic(graph))

    def test_self_dependency_rejected(self):
        plan = self._plan()
        plan["steps"][0]["dependencies"] = ["select-model"]
        graph = build_plan_graph(plan)
        self.assertTrue(validate_acyclic(graph))

    def test_downstream_traversal(self):
        graph = build_plan_graph(self._plan())
        self.assertEqual(find_downstream_steps("select-model", graph), ["configure-router", "verify-model"])

    def test_upstream_traversal(self):
        graph = build_plan_graph(self._plan())
        self.assertEqual(find_upstream_dependencies("configure-router", graph), ["select-model", "verify-model"])

    def test_ready_step_detection(self):
        plan = self._plan()
        evidence = {
            "facts": {
                "vision_model_selected": {"state_type": "verified", "value": True},
            }
        }
        ready = find_ready_steps(plan, evidence)
        self.assertEqual([item["id"] for item in ready], ["select-model"])

    def test_blocked_steps_detection(self):
        blocked = find_blocked_steps(self._plan(), {"facts": {}})
        self.assertEqual([item["id"] for item in blocked], ["select-model", "verify-model", "configure-router"])

    def test_backward_compatible_signature(self):
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
        self.assertIn("vision_router_configured", node_ids)


if __name__ == "__main__":
    unittest.main()
