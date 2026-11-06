import unittest

from services.declarative_acknowledger import build_declarative_acknowledgement


class DeclarativeAcknowledgerTests(unittest.TestCase):
    def test_project_statement_acknowledges_active_project(self):
        text = build_declarative_acknowledgement("I am building OMEGA-ARC.")
        self.assertEqual(text, "OMEGA-ARC is now recognized as an active project.")

    def test_goal_statement_acknowledges_active_goal_without_follow_up(self):
        text = build_declarative_acknowledgement("My goal is to add vision routing.")
        self.assertEqual(text, "Vision routing is now tracked as an active goal.")
        self.assertNotIn("?", text)

    def test_casual_conversation_reaches_the_model_not_a_canned_goal(self):
        # Real operator lines from 2026-11-06 that were hijacked into "... tracked as an active goal".
        for line in (
            "absolutely! let's rerine them as much as you want",
            "sorry, that was a typo. I meant \"refine\"",
            "I want to hear a better joke",
            "we need to talk about your sense of humor",
            "I plan to sleep soon",
        ):
            with self.subTest(line=line):
                self.assertIsNone(build_declarative_acknowledgement(line))

    def test_long_message_mentioning_work_is_not_a_project_declaration(self):
        text = build_declarative_acknowledgement(
            "I'm working on my car tonight so tell me something funny while I wait for parts")
        self.assertIsNone(text)

    def test_configuration_statement_uses_configured_wording(self):
        text = build_declarative_acknowledgement("The backend runs on port 8002.")
        self.assertEqual(text, "The backend is configured to use port 8002.")
        self.assertNotIn("running on port", text.lower())

    def test_question_does_not_trigger_declarative_template(self):
        text = build_declarative_acknowledgement("What do you currently know?")
        self.assertIsNone(text)

    def test_user_reported_health_check_success_gets_unverified_ack(self):
        text = build_declarative_acknowledgement("A health check against the backend on port 8002 succeeded.")
        self.assertEqual(
            text,
            "Understood. You reported that a health check for port 8002 succeeded, but I have not independently verified that result.",
        )


if __name__ == "__main__":
    unittest.main()
