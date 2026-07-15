import unittest

from services.conflict_engine import detect_dependency_conflicts, detect_value_conflicts


class ConflictEngineTests(unittest.TestCase):
    def test_conflicting_current_values_detected(self):
        conflicts = detect_value_conflicts(
            [
                {"key": "backend_port", "value": 8001, "state_type": "configured"},
                {"key": "backend_port", "value": 8002, "state_type": "configured"},
            ]
        )
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["type"], "conflicting_current_values")

    def test_identical_values_produce_no_conflict(self):
        conflicts = detect_value_conflicts(
            [
                {"key": "backend_port", "value": 8002, "state_type": "configured"},
                {"key": "backend_port", "value": 8002, "state_type": "configured"},
            ]
        )
        self.assertEqual(conflicts, [])

    def test_invalidated_records_ignored(self):
        conflicts = detect_value_conflicts(
            [
                {"key": "backend_port", "value": 8001, "state_type": "invalidated"},
                {"key": "backend_port", "value": 8002, "state_type": "configured"},
            ]
        )
        self.assertEqual(conflicts, [])

    def test_expired_records_ignored(self):
        conflicts = detect_value_conflicts(
            [
                {"key": "backend_port", "value": 8001, "state_type": "expired"},
                {"key": "backend_port", "value": 8002, "state_type": "configured"},
            ]
        )
        self.assertEqual(conflicts, [])

    def test_dependency_mismatch_detected(self):
        conflicts = detect_dependency_conflicts(
            {
                "version": 1,
                "records": {
                    "backend_port": {"key": "backend_port", "value": 8002, "state_type": "configured", "dependencies": []},
                    "backend_health": {
                        "key": "backend_health",
                        "value": None,
                        "state_type": "invalidated",
                        "dependencies": ["backend_port"],
                        "notes": "Port changed after last verification.",
                    },
                },
            }
        )
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["type"], "verification_dependency_mismatch")


if __name__ == "__main__":
    unittest.main()
