import unittest

from services.state_summary import (
    build_current_state_summary,
    detect_summary_intent,
    render_current_state_summary,
    select_summary_for_intent,
)


class StateSummaryTests(unittest.TestCase):
    def _sample_inputs(self):
        identity_profile = {"version": 1, "facts": {}}
        evidence_store = {
            "version": 1,
            "facts": {
                "backend_port": {
                    "key": "backend_port",
                    "value": 8002,
                    "state_type": "configured",
                    "source": "user",
                    "confidence": 1.0,
                },
                "backend_health": {
                    "key": "backend_health",
                    "value": None,
                    "state_type": "unknown",
                    "source": "system",
                    "confidence": 0.0,
                    "dependencies": ["backend_port"],
                },
                "vision_model_installed": {
                    "key": "vision_model_installed",
                    "value": True,
                    "state_type": "declared",
                    "source": "user",
                    "confidence": 1.0,
                },
            },
        }
        goal_store = {
            "version": 1,
            "goals": [
                {
                    "id": "goal-add-vision-routing",
                    "title": "Add vision routing",
                    "status": "active",
                    "dependencies": [
                        "vision_model_selected",
                        "vision_model_loaded",
                        "vision_model_healthy",
                        "vision_router_configured",
                        "vision_routing_verified",
                    ],
                    "completion_evidence_key": "vision_routing_ready",
                }
            ],
        }
        knowledge_graph = {
            "version": 1,
            "nodes": [
                {"id": "project:omega-arc", "type": "project", "label": "OMEGA-ARC"}
            ],
            "edges": [],
        }
        reasoning_result = {
            "resolved_beliefs": [
                {
                    "key": "backend_port",
                    "value": 8002,
                    "status": "resolved",
                    "state_type": "configured",
                    "reason": "Configured by user statement.",
                },
                {
                    "key": "backend_health",
                    "value": None,
                    "status": "unknown",
                    "state_type": "unknown",
                    "reason": "No matching verification evidence.",
                },
            ],
            "uncertainties": [
                {
                    "key": "backend_health",
                    "status": "unknown",
                    "state_type": "unknown",
                    "reason": "No matching verification evidence.",
                },
                {
                    "key": "vision_model_loaded",
                    "status": "unknown",
                    "state_type": "unknown",
                    "reason": "Missing runtime verification.",
                },
                {
                    "key": "vision_model_selected",
                    "status": "unknown",
                    "state_type": "unknown",
                    "reason": "No selected model has been verified.",
                },
                {
                    "key": "vision_router_configured",
                    "status": "unknown",
                    "state_type": "unknown",
                    "reason": "Routing path configuration is unverified.",
                },
                {
                    "key": "vision_routing_verified",
                    "status": "unknown",
                    "state_type": "unknown",
                    "reason": "Routing path has not been tested.",
                },
            ],
            "conflicts": [],
            "blocked_goals": [
                {
                    "goal_id": "goal-add-vision-routing",
                    "title": "Add vision routing",
                    "status": "blocked",
                    "completion": "unverified",
                    "blockers": [
                        {"key": "vision_model_loaded", "reason": "Missing readiness evidence for this dependency."},
                        {"key": "vision_routing_verified", "reason": "Missing readiness evidence for this dependency."},
                    ],
                }
            ],
            "recommended_actions": [
                {
                    "action": "resolve_goal_blocker",
                    "target": "vision_model_selected",
                    "reason": "Missing readiness evidence for this dependency.",
                }
            ],
        }
        return identity_profile, evidence_store, goal_store, knowledge_graph, reasoning_result

    def test_detect_summary_intent(self):
        self.assertEqual(detect_summary_intent("What do you currently know?"), "state_summary")
        self.assertEqual(detect_summary_intent("Summarize the current state."), "state_summary")
        self.assertEqual(detect_summary_intent("What remains uncertain?"), "uncertainty_summary")
        self.assertEqual(detect_summary_intent("What are your current uncertainties?"), "uncertainty_summary")

    def test_state_summary_includes_active_project(self):
        summary = build_current_state_summary(
            identity_profile=self._sample_inputs()[0],
            evidence_store=self._sample_inputs()[1],
            goal_store=self._sample_inputs()[2],
            knowledge_graph=self._sample_inputs()[3],
            reasoning_result=self._sample_inputs()[4],
        )
        rendered = render_current_state_summary(summary)
        self.assertIn("OMEGA-ARC is an active project.", rendered)

    def test_state_summary_includes_configured_backend_port(self):
        identity_profile, evidence_store, goal_store, knowledge_graph, reasoning_result = self._sample_inputs()
        summary = build_current_state_summary(
            identity_profile=identity_profile,
            evidence_store=evidence_store,
            goal_store=goal_store,
            knowledge_graph=knowledge_graph,
            reasoning_result=reasoning_result,
        )
        rendered = render_current_state_summary(summary)
        self.assertIn("configured to use port 8002", rendered)

    def test_configured_port_is_not_rendered_as_runtime_operation(self):
        identity_profile, evidence_store, goal_store, knowledge_graph, reasoning_result = self._sample_inputs()
        summary = build_current_state_summary(
            identity_profile=identity_profile,
            evidence_store=evidence_store,
            goal_store=goal_store,
            knowledge_graph=knowledge_graph,
            reasoning_result=reasoning_result,
        )
        rendered = render_current_state_summary(summary)
        self.assertNotIn("running on port 8002", rendered.lower())
        self.assertNotIn("verified as 8002", rendered.lower())

    def test_active_goal_appears_in_summary(self):
        identity_profile, evidence_store, goal_store, knowledge_graph, reasoning_result = self._sample_inputs()
        summary = build_current_state_summary(
            identity_profile=identity_profile,
            evidence_store=evidence_store,
            goal_store=goal_store,
            knowledge_graph=knowledge_graph,
            reasoning_result=reasoning_result,
        )
        rendered = render_current_state_summary(summary)
        self.assertIn("Add vision routing", rendered)

    def test_unknown_backend_health_appears_explicitly(self):
        identity_profile, evidence_store, goal_store, knowledge_graph, reasoning_result = self._sample_inputs()
        summary = build_current_state_summary(
            identity_profile=identity_profile,
            evidence_store=evidence_store,
            goal_store=goal_store,
            knowledge_graph=knowledge_graph,
            reasoning_result=reasoning_result,
        )
        rendered = render_current_state_summary(summary)
        self.assertIn("Backend current health is unknown", rendered)
        self.assertIn("Backend runtime health has not been independently verified.", rendered)

    def test_unverified_vision_readiness_appears_explicitly(self):
        identity_profile, evidence_store, goal_store, knowledge_graph, reasoning_result = self._sample_inputs()
        summary = build_current_state_summary(
            identity_profile=identity_profile,
            evidence_store=evidence_store,
            goal_store=goal_store,
            knowledge_graph=knowledge_graph,
            reasoning_result=reasoning_result,
        )
        rendered = render_current_state_summary(summary)
        self.assertIn("Vision-model runtime readiness has not been verified.", rendered)
        self.assertIn("Vision-routing readiness has not been verified.", rendered)

    def test_summary_does_not_replay_transcript(self):
        identity_profile, evidence_store, goal_store, knowledge_graph, reasoning_result = self._sample_inputs()
        summary = build_current_state_summary(
            identity_profile=identity_profile,
            evidence_store=evidence_store,
            goal_store=goal_store,
            knowledge_graph=knowledge_graph,
            reasoning_result=reasoning_result,
        )
        rendered = render_current_state_summary(summary)
        self.assertNotIn("I am building OMEGA-ARC", rendered)
        self.assertNotIn("My goal is", rendered)

    def test_summary_does_not_mention_turning(self):
        identity_profile, evidence_store, goal_store, knowledge_graph, reasoning_result = self._sample_inputs()
        summary = build_current_state_summary(
            identity_profile=identity_profile,
            evidence_store=evidence_store,
            goal_store=goal_store,
            knowledge_graph=knowledge_graph,
            reasoning_result=reasoning_result,
        )
        rendered = render_current_state_summary(summary)
        self.assertNotIn("Turning", rendered)

    def test_summary_does_not_ask_follow_up_question(self):
        identity_profile, evidence_store, goal_store, knowledge_graph, reasoning_result = self._sample_inputs()
        summary = build_current_state_summary(
            identity_profile=identity_profile,
            evidence_store=evidence_store,
            goal_store=goal_store,
            knowledge_graph=knowledge_graph,
            reasoning_result=reasoning_result,
        )
        rendered = render_current_state_summary(summary)
        self.assertNotIn("?", rendered)

    def test_uncertainty_only_intent_returns_only_unresolved_items(self):
        identity_profile, evidence_store, goal_store, knowledge_graph, reasoning_result = self._sample_inputs()
        summary = build_current_state_summary(
            identity_profile=identity_profile,
            evidence_store=evidence_store,
            goal_store=goal_store,
            knowledge_graph=knowledge_graph,
            reasoning_result=reasoning_result,
        )
        selected = select_summary_for_intent(summary, "uncertainty_summary")
        rendered = render_current_state_summary(selected)
        self.assertIn("Current uncertainties:", rendered)
        self.assertIn("Uncertainties:", rendered)
        self.assertNotIn("Project:", rendered)
        self.assertNotIn("Configuration:", rendered)
        self.assertNotIn("Goals:", rendered)

    def test_configured_backend_port_not_in_uncertainty_summary(self):
        identity_profile, evidence_store, goal_store, knowledge_graph, reasoning_result = self._sample_inputs()
        summary = build_current_state_summary(
            identity_profile=identity_profile,
            evidence_store=evidence_store,
            goal_store=goal_store,
            knowledge_graph=knowledge_graph,
            reasoning_result=reasoning_result,
        )
        selected = select_summary_for_intent(summary, "uncertainty_summary")
        rendered = render_current_state_summary(selected)
        self.assertNotIn("configured to use port 8002", rendered)

    def test_duplicate_vague_goal_matching_project_is_suppressed(self):
        identity_profile, evidence_store, goal_store, knowledge_graph, reasoning_result = self._sample_inputs()
        goal_store = {
            "version": 1,
            "goals": [
                {
                    "id": "goal-omega-arc",
                    "title": "OMEGA-ARC",
                    "status": "active",
                },
                {
                    "id": "goal-build-omega-arc",
                    "title": "Build OMEGA-ARC",
                    "status": "active",
                },
                {
                    "id": "goal-add-vision-routing",
                    "title": "Add vision routing",
                    "status": "active",
                },
            ],
        }
        summary = build_current_state_summary(
            identity_profile=identity_profile,
            evidence_store=evidence_store,
            goal_store=goal_store,
            knowledge_graph=knowledge_graph,
            reasoning_result=reasoning_result,
        )
        rendered = render_current_state_summary(summary)
        self.assertNotIn("- OMEGA-ARC.", rendered)
        self.assertIn("- Build OMEGA-ARC.", rendered)
        self.assertIn("- Add vision routing.", rendered)

    def test_recommended_actions_are_human_readable_and_limited(self):
        identity_profile, evidence_store, goal_store, knowledge_graph, reasoning_result = self._sample_inputs()
        summary = build_current_state_summary(
            identity_profile=identity_profile,
            evidence_store=evidence_store,
            goal_store=goal_store,
            knowledge_graph=knowledge_graph,
            reasoning_result=reasoning_result,
        )
        rendered = render_current_state_summary(summary)
        self.assertIn("Confirm which vision model will be used.", rendered)
        self.assertIn("Verify that the selected model loads successfully.", rendered)
        self.assertIn("Configure and test the complete vision-routing path.", rendered)
        self.assertNotIn("resolve_goal_blocker", rendered)
        self.assertNotIn("vision_model_selected", rendered)

    def test_missing_sections_are_omitted_cleanly(self):
        rendered = render_current_state_summary(
            {
                "identity": [],
                "projects": ["OMEGA-ARC is an active project."],
                "configuration": [],
                "runtime_state": [],
                "goals": [],
                "uncertainties": [],
                "conflicts": [],
                "recommended_actions": [],
            }
        )
        self.assertIn("Project:", rendered)
        self.assertNotIn("Configuration:", rendered)
        self.assertNotIn("Runtime state:", rendered)

    def test_no_unsupported_model_availability_claim(self):
        identity_profile, evidence_store, goal_store, knowledge_graph, reasoning_result = self._sample_inputs()
        summary = build_current_state_summary(
            identity_profile=identity_profile,
            evidence_store=evidence_store,
            goal_store=goal_store,
            knowledge_graph=knowledge_graph,
            reasoning_result=reasoning_result,
        )
        rendered = render_current_state_summary(summary)
        self.assertNotIn("models are available", rendered.lower())
        self.assertNotIn("model is available", rendered.lower())


if __name__ == "__main__":
    unittest.main()
