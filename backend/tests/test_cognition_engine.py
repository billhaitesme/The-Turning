import unittest

from services.cognition_engine import (
    analyze_message,
    extract_explicit_backend_port,
    extract_explicit_goals,
    extract_explicit_projects,
    looks_like_correction,
    normalize_goal_title,
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

    def test_project_candidate_remains_project_knowledge(self):
        result = analyze_message(message="I am building OMEGA-ARC.")
        project_candidates = [
            candidate
            for candidate in result["knowledge_candidates"]
            if candidate.get("key") == "active_project"
        ]
        self.assertEqual(len(project_candidates), 1)
        self.assertEqual(project_candidates[0]["value"], "OMEGA-ARC")

    def test_generated_build_goal_is_normalized(self):
        result = analyze_message(message="I am building OMEGA-ARC.")
        build_candidates = [
            candidate
            for candidate in result["goal_candidates"]
            if candidate.get("key") == "build_project"
        ]
        self.assertEqual(len(build_candidates), 1)
        self.assertEqual(build_candidates[0]["value"], "Build OMEGA-ARC")

    def test_explicit_goal_candidate_is_normalized_title_case(self):
        result = analyze_message(message="My goal is to add vision routing.")
        explicit_candidates = [
            candidate
            for candidate in result["goal_candidates"]
            if candidate.get("key") == "explicit_goal"
        ]
        self.assertEqual(len(explicit_candidates), 1)
        self.assertEqual(explicit_candidates[0]["value"], "Add vision routing")

    def test_normalize_goal_title_capitalizes_first_character(self):
        self.assertEqual(normalize_goal_title("add vision routing"), "Add vision routing")


if __name__ == "__main__":
    unittest.main()
