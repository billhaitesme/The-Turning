import unittest

from services.evidence_engine import normalize_evidence_record, set_evidence
from services.runtime_declarations import extract_runtime_declarations


class RuntimeDeclarationTests(unittest.TestCase):
    def test_user_reported_health_check_success_stays_declared(self):
        records = extract_runtime_declarations("A health check against the backend on port 8002 succeeded.")
        backend = next(item for item in records if item["key"] == "backend_health")
        self.assertEqual(backend["value"], "online")
        self.assertEqual(backend["state_type"], "declared")
        self.assertEqual(backend["source"], "user")
        self.assertEqual(backend["confidence"], 1.0)
        self.assertEqual(backend["notes"], "User reports successful health check.")
        self.assertIsNone(backend.get("checked_at"))
        self.assertIsNone(backend.get("checked_url"))

    def test_user_says_vision_model_installed_declared_true_only(self):
        records = extract_runtime_declarations("The vision model is installed.")
        record = next(item for item in records if item["key"] == "vision_model_installed")
        self.assertEqual(record["state_type"], "declared")
        self.assertEqual(record["source"], "user")
        self.assertTrue(record["value"])
        self.assertFalse(any(item["key"] == "vision_model_available" for item in records))
        self.assertFalse(any(item["key"] == "vision_model_loaded" for item in records))
        self.assertFalse(any(item["key"] == "vision_model_healthy" for item in records))

    def test_user_says_service_online_declared_not_verified(self):
        records = extract_runtime_declarations("The backend is online.")
        backend = next(item for item in records if item["key"] == "backend_health")
        self.assertEqual(backend["state_type"], "declared")
        self.assertEqual(backend["source"], "user")
        self.assertEqual(backend["value"], "online")

    def test_user_says_database_connected_declared_not_verified(self):
        records = extract_runtime_declarations("The database is connected.")
        record = next(item for item in records if item["key"] == "database_connected")
        self.assertEqual(record["state_type"], "declared")
        self.assertEqual(record["source"], "user")
        self.assertEqual(record["value"], "connected")

    def test_user_says_model_ready_declared_not_verified(self):
        records = extract_runtime_declarations("The model is ready.")
        record = next(item for item in records if item["key"] == "model_ready")
        self.assertEqual(record["state_type"], "declared")
        self.assertEqual(record["source"], "user")
        self.assertEqual(record["value"], "ready")

    def test_user_says_file_readable_declared_not_verified(self):
        records = extract_runtime_declarations("The file is readable.")
        record = next(item for item in records if item["key"] == "file_readable")
        self.assertEqual(record["state_type"], "declared")
        self.assertEqual(record["source"], "user")
        self.assertEqual(record["value"], "readable")

    def test_actual_system_check_may_promote_declared_to_verified(self):
        store = {"version": 1, "facts": {}}
        declared = extract_runtime_declarations("The backend is online.")[0]
        store = set_evidence(store, key="backend_health", record=declared)
        store = set_evidence(
            store,
            key="backend_health",
            record={
                "key": "backend_health",
                "value": "online",
                "state_type": "verified",
                "source": "health_check",
                "confidence": 1.0,
                "observed_at": "2026-07-15T00:00:00+00:00",
            },
        )
        record = normalize_evidence_record(store["facts"]["backend_health"])
        self.assertEqual(record["state_type"], "verified")
        self.assertEqual(record["source"], "health_check")

    def test_no_checked_at_timestamp_created_from_user_speech(self):
        record = extract_runtime_declarations("The backend is online.")[0]
        self.assertIsNone(record.get("observed_at"))
        self.assertNotIn("checked_at", record)

    def test_no_health_check_source_created_from_user_speech(self):
        record = extract_runtime_declarations("The backend is online.")[0]
        self.assertNotEqual(record.get("source"), "health_check")


if __name__ == "__main__":
    unittest.main()
