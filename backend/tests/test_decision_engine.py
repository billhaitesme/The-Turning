import unittest

from services.decision_engine import (
    create_decision,
    explain_decision,
    find_decisions_for_goal,
    find_decisions_for_plan,
    supersede_decision,
    validate_decision,
)


class DecisionEngineTests(unittest.TestCase):
    def test_explicit_choice_creates_active_decision(self):
        decision = create_decision(
            decision_id="decision-llava",
            title="Use LLaVA",
            decision_text="Use llava:7b",
            reason="Already installed locally.",
            explicit_choice=True,
            source="explicit_user_choice",
        )
        self.assertEqual(decision["status"], "active")

    def test_planner_suggestion_creates_proposed_decision_only(self):
        decision = create_decision(
            decision_id="decision-candidate",
            title="Candidate",
            decision_text="Use model A",
            reason="Candidate only.",
            source="deterministic_planner",
        )
        self.assertEqual(decision["status"], "proposed")

    def test_decision_has_evidence_provenance(self):
        decision = create_decision(
            decision_id="decision-a",
            title="Decision A",
            decision_text="Use A",
            reason="Evidence available.",
            evidence_keys=["vision_model_selected"],
        )
        self.assertIn("vision_model_selected", decision["evidence_keys"])

    def test_alternatives_preserved(self):
        decision = create_decision(
            decision_id="decision-a",
            title="Decision A",
            decision_text="Use A",
            reason="Evidence available.",
            alternatives=[{"value": "B", "reason_not_selected": "Not installed."}],
        )
        self.assertEqual(decision["alternatives"][0]["value"], "B")

    def test_decision_can_be_superseded_and_historical(self):
        decision = create_decision(
            decision_id="decision-a",
            title="Decision A",
            decision_text="Use A",
            reason="Evidence available.",
            explicit_choice=True,
            source="explicit_user_choice",
        )
        superseded = supersede_decision(decision, "decision-b")
        self.assertEqual(superseded["status"], "superseded")
        self.assertEqual(superseded["superseded_by"], "decision-b")

    def test_explanation_contains_concise_reason(self):
        decision = create_decision(
            decision_id="decision-a",
            title="Decision A",
            decision_text="Use A",
            reason="Installed locally.",
            alternatives=[{"value": "B", "reason_not_selected": "Not installed."}],
        )
        explanation = explain_decision(decision)
        self.assertIn("Reason: Installed locally.", explanation)

    def test_explanation_does_not_expose_hidden_reasoning(self):
        decision = create_decision(
            decision_id="decision-a",
            title="Decision A",
            decision_text="Use A",
            reason="Installed locally.",
        )
        explanation = explain_decision(decision)
        self.assertNotIn("chain-of-thought", explanation.lower())

    def test_explanation_for_explicit_selection_without_additional_rationale(self):
        decision = create_decision(
            decision_id="decision-llava",
            title="Use LLaVA for vision routing",
            decision_text="Use llava:7b as the initial vision model.",
            reason="LLaVA was explicitly selected, but no additional rationale has been recorded.",
            explicit_choice=True,
            source="explicit_user_choice",
        )
        explanation = explain_decision(decision)
        self.assertIn("explicitly selected", explanation.lower())

    def test_validate_decision(self):
        decision = create_decision(
            decision_id="decision-a",
            title="Decision A",
            decision_text="Use A",
            reason="Installed locally.",
        )
        self.assertTrue(validate_decision(decision)["valid"])

    def test_find_decisions_for_goal_and_plan(self):
        decisions = [
            {"id": "d1", "goal_id": "g1", "plan_id": "p1"},
            {"id": "d2", "goal_id": "g2", "plan_id": "p1"},
        ]
        self.assertEqual(len(find_decisions_for_goal(decisions, "g1")), 1)
        self.assertEqual(len(find_decisions_for_plan(decisions, "p1")), 2)


if __name__ == "__main__":
    unittest.main()
