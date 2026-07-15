import unittest

from services.cognition_pipeline import process_completed_turn


class CognitionPipelineTests(unittest.TestCase):
    def test_pipeline_collects_goals_and_knowledge(self):
        result = process_completed_turn(
            user_message=(
                "I am building OMEGA-ARC. "
                "The backend runs on port 8001."
            ),
            assistant_response="Understood.",
            persist=False,
        )

        self.assertTrue(
            any(
                candidate.get("key") == "active_project"
                for candidate in result["cognition"]["knowledge_candidates"]
            )
        )
        self.assertTrue(
            any(
                candidate.get("key") == "backend_port"
                for candidate in result["cognition"]["knowledge_candidates"]
            )
        )
        self.assertTrue(
            any(
                candidate.get("kind") == "goal"
                for candidate in result["cognition"]["goal_candidates"]
            )
        )
        self.assertIsNotNone(result["curiosity"])


if __name__ == "__main__":
    unittest.main()
