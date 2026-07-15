import unittest

from services.cognition_engine import (
    analyze_message,
    extract_explicit_backend_port,
    extract_explicit_goals,
    extract_explicit_projects,
    looks_like_correction,
)


class CognitionEngineTests(unittest.TestCase):
    def test_detects_project(self):
        self.assertEqual(
            extract_explicit_projects(
                "I am building OMEGA-ARC."
            ),
            ["OMEGA-ARC"],
        )

    def test_detects_goal(self):
        goals = extract_explicit_goals(
            "My goal is to add vision routing."
        )

        self.assertEqual(
            goals,
            ["add vision routing"],
        )

    def test_detects_backend_port(self):
        self.assertEqual(
            extract_explicit_backend_port(
                "The backend runs on port 8001."
            ),
            8001,
        )

    def test_detects_correction(self):
        self.assertTrue(
            looks_like_correction(
                "I am actually 40 years old."
            )
        )

    def test_general_question_is_not_goal(self):
        result = analyze_message(
            message="What is an API?"
        )

        self.assertEqual(
            result["goal_candidates"],
            [],
        )


if __name__ == "__main__":
    unittest.main()
