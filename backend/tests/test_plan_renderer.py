import unittest

from services.plan_renderer import (
    render_decision,
    render_next_action,
    render_plan,
    render_plan_summary,
)


class PlanRendererTests(unittest.TestCase):
    def _plan(self):
        return {
            "id": "plan-a",
            "title": "Add vision routing",
            "status": "active",
            "steps": [
                {"id": "s1", "title": "Select model", "status": "completed"},
                {"id": "s2", "title": "Verify load", "status": "active"},
                {"id": "s3", "title": "Configure route", "status": "pending"},
                {"id": "s4", "title": "Run e2e", "status": "blocked"},
            ],
            "blockers": ["No verified endpoint"],
        }

    def test_human_readable_headings(self):
        text = render_plan(self._plan())
        self.assertIn("Current plan:", text)
        self.assertIn("Completed:", text)

    def test_no_raw_json(self):
        text = render_plan(self._plan())
        self.assertNotIn("{", text)

    def test_no_snake_case_keys(self):
        text = render_plan_summary(self._plan())
        self.assertNotIn("goal_id", text)

    def test_completed_active_pending_blocked_sections(self):
        text = render_plan(self._plan())
        self.assertIn("Completed:", text)
        self.assertIn("Active:", text)
        self.assertIn("Pending:", text)
        self.assertIn("Blocked:", text)

    def test_next_action_shown(self):
        text = render_next_action({"next_actions": [{"title": "Verify load"}]})
        self.assertIn("Verify load", text)

    def test_empty_sections_omitted_cleanly(self):
        text = render_plan({"title": "Empty", "steps": []})
        self.assertIn("Current plan: Empty", text)

    def test_decisions_rendered_with_provenance(self):
        text = render_decision(
            {
                "title": "Use LLaVA",
                "status": "active",
                "decision": "Use llava:7b",
                "reason": "Installed locally.",
                "alternatives": [{"value": "qwen2.5-vl", "reason_not_selected": "Not installed."}],
            }
        )
        self.assertIn("Reason: Installed locally.", text)


if __name__ == "__main__":
    unittest.main()
