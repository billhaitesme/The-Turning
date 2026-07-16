import unittest

from services.curiosity_engine import (
    apply_curiosity_to_response,
    choose_curiosity_question,
)


class CuriosityEngineTests(unittest.TestCase):
    def test_active_project_produces_permission_question(self):
        result = choose_curiosity_question(
            user_message="I am building OMEGA-ARC.",
            cognition_result={
                "knowledge_candidates": [
                    {"key": "active_project", "value": "OMEGA-ARC"}
                ]
            },
        )

        self.assertIsNotNone(result)
        self.assertEqual(result["kind"], "curiosity")

    def test_simple_api_question_produces_no_question(self):
        result = choose_curiosity_question(
            user_message="What is an API?",
            cognition_result={"knowledge_candidates": []},
        )

        self.assertIsNone(result)

    def test_only_one_question_is_returned(self):
        result = choose_curiosity_question(
            user_message="I am building OMEGA-ARC.",
            cognition_result={"knowledge_candidates": [{"key": "active_project", "value": "OMEGA-ARC"}]},
        )

        self.assertIsNotNone(result)
        self.assertEqual(len([result]), 1)

    def test_missing_identity_profile_does_not_crash(self):
        result = choose_curiosity_question(
            user_message="Call me Alex.",
            cognition_result={"knowledge_candidates": []},
            identity_profile=None,
        )

        self.assertIsNotNone(result)

    def test_declarative_project_statement_produces_no_question_when_curiosity_is_disabled(self):
        response = apply_curiosity_to_response(
            response="Understood. OMEGA-ARC is now recognized as an active project.",
            curiosity_candidate={
                "kind": "curiosity",
                "question": "Would you like me to remember OMEGA-ARC as one of your active projects?",
            },
            enabled=False,
        )

        self.assertNotIn("Would you like", response)

    def test_goal_statement_produces_no_question_when_curiosity_is_disabled(self):
        response = apply_curiosity_to_response(
            response="Understood. I’ve identified vision routing as an active project goal.",
            curiosity_candidate={
                "kind": "curiosity",
                "question": "Would you like me to remember vision routing as an active goal?",
            },
            enabled=False,
        )

        self.assertNotIn("Would you like", response)

    def test_configuration_statement_produces_no_question_when_curiosity_is_disabled(self):
        response = apply_curiosity_to_response(
            response="Understood. I’ll treat 8001 as the configured backend port.",
            curiosity_candidate={
                "kind": "curiosity",
                "question": "Would you like me to remember 8001 as the backend port?",
            },
            enabled=False,
        )

        self.assertNotIn("Would you like", response)

    def test_health_check_offer_is_not_appended_when_curiosity_is_disabled(self):
        response = apply_curiosity_to_response(
            response="The backend is configured for port 8001. Its current runtime health has not been verified.",
            curiosity_candidate={
                "kind": "curiosity",
                "question": "Would you like me to attempt a health check?",
            },
            enabled=False,
        )

        self.assertNotIn("Would you like me to attempt a health check?", response)
        self.assertNotIn("health check?", response)

    def test_vision_readiness_follow_up_is_not_appended_when_curiosity_is_disabled(self):
        response = apply_curiosity_to_response(
            response="Vision routing readiness is not verified. Installed status alone is not enough.",
            curiosity_candidate={
                "kind": "curiosity",
                "question": "Would you like me to run a routing verification now?",
            },
            enabled=False,
        )

        self.assertNotIn("Would you like me to run a routing verification now?", response)

    def test_curiosity_enabled_mode_appends_no_more_than_one_question(self):
        response = apply_curiosity_to_response(
            response="Understood. I’ll treat 8001 as the configured backend port.",
            curiosity_candidate={
                "kind": "curiosity",
                "question": "Would you like me to remember 8001 as the backend port?",
            },
            enabled=True,
        )

        self.assertEqual(response.count("?"), 1)


if __name__ == "__main__":
    unittest.main()
