import unittest
from identity_engine import classify_identity_intent

class Tests(unittest.TestCase):
    def test_identity(self):
        self.assertEqual(classify_identity_intent("Who are you?").intent, "identity")
    def test_user_identity(self):
        self.assertEqual(classify_identity_intent("Who am I?").intent, "user_identity")
    def test_general(self):
        self.assertEqual(classify_identity_intent("What is an API?").intent, "general")

if __name__ == "__main__":
    unittest.main()