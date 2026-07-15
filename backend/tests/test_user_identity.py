import unittest

from services.user_identity import (
    age_group_from_age,
    build_user_identity_prompt,
    empty_identity_profile,
    extract_explicit_age,
    normalize_identity_profile,
    set_fact,
)


class UserIdentityTests(unittest.TestCase):
    def test_extract_explicit_age(self):
        self.assertEqual(
            extract_explicit_age("I am actually 40 years old"),
            40,
        )

    def test_short_message_does_not_infer_age(self):
        self.assertIsNone(
            extract_explicit_age("Who am I?")
        )

    def test_age_group_is_derived(self):
        self.assertEqual(
            age_group_from_age(40),
            "adult",
        )

    def test_explicit_fact_replaces_inference(self):
        profile = empty_identity_profile()

        profile = set_fact(
            profile,
            key="age",
            value=15,
            source="inferred",
            confidence=0.5,
        )

        profile = set_fact(
            profile,
            key="age",
            value=40,
            source="explicit_user_statement",
            confidence=1.0,
        )

        fact = profile["facts"]["age"]

        self.assertEqual(fact["value"], 40)
        self.assertEqual(
            fact["source"],
            "explicit_user_statement",
        )

    def test_inference_cannot_replace_explicit_fact(self):
        profile = empty_identity_profile()

        profile = set_fact(
            profile,
            key="age",
            value=40,
            source="explicit_user_statement",
            confidence=1.0,
        )

        profile = set_fact(
            profile,
            key="age",
            value=15,
            source="inferred",
            confidence=0.9,
        )

        self.assertEqual(
            profile["facts"]["age"]["value"],
            40,
        )

    def test_legacy_profile_is_normalized(self):
        profile = normalize_identity_profile(
            {
                "age": 40,
                "age_group": "young",
                "age_source": "explicit_user_statement",
            }
        )

        self.assertEqual(
            profile["facts"]["age"]["value"],
            40,
        )

    def test_unknown_age_is_never_described_as_young(self):
        prompt = build_user_identity_prompt({"facts": {}})
        self.assertIn("Do not guess the user's age", prompt)
        self.assertIn("Never describe the user as young", prompt)

    def test_explicit_age_remains_authoritative(self):
        prompt = build_user_identity_prompt(
            {
                "facts": {
                    "age": {
                        "value": 40,
                        "source": "explicit_user_statement",
                    }
                }
            }
        )
        self.assertIn("Reported age: 40", prompt)
        self.assertIn("Derived age group: adult", prompt)


if __name__ == "__main__":
    unittest.main()
