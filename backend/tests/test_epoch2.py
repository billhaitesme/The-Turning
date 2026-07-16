import unittest
from awareness_engine import AwarenessSnapshot, awareness_prompt

class Tests(unittest.TestCase):
    def test_awareness_prompt(self):
        snapshot = AwarenessSnapshot(
            True, False, "offline",
            "llama2-uncensored:7b", "llava:7b",
            "embeddinggemma:latest", "gemma3:1b",
            "TEST GPU", {"vision": True}
        )
        text = awareness_prompt(snapshot)
        self.assertIn("TEST GPU", text)
        self.assertIn("offline", text)

if __name__ == "__main__":
    unittest.main()