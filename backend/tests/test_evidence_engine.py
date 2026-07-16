import unittest
from datetime import datetime, timedelta, timezone

from services.evidence_engine import (
    extract_durable_evidence_store,
    extract_session_scoped_evidence_store,
    empty_evidence_record,
    invalidate_dependent_evidence,
    is_evidence_fresh,
    merge_evidence_stores,
    normalize_evidence_record,
    record_health_check_result,
    render_evidence_for_prompt,
    rank_state_type,
    set_evidence,
    should_replace_evidence,
)


class EvidenceEngineTests(unittest.TestCase):
    def test_configured_port_does_not_imply_online(self):
        record = normalize_evidence_record({"value": 8001, "state_type": "configured", "source": "user"})
        self.assertEqual(record["state_type"], "configured")
        self.assertNotEqual(record["state_type"], "verified")

    def test_installed_model_does_not_imply_ready(self):
        record = normalize_evidence_record({"value": True, "state_type": "declared", "source": "user"})
        self.assertEqual(record["state_type"], "declared")

    def test_configured_database_does_not_imply_connected(self):
        record = normalize_evidence_record({"value": True, "state_type": "configured", "source": "config"})
        self.assertEqual(record["state_type"], "configured")

    def test_declared_test_result_does_not_equal_verified_result(self):
        declared = normalize_evidence_record({"value": "passed", "state_type": "declared", "source": "user"})
        verified = normalize_evidence_record({"value": "passed", "state_type": "verified", "source": "health_check"})
        self.assertNotEqual(declared["state_type"], verified["state_type"])

    def test_changing_dependency_invalidates_prior_verification(self):
        store = {"facts": {"backend_health": {"value": True, "state_type": "verified", "scope": "backend_url", "expires_at": None}}}
        updated = invalidate_dependent_evidence(store, dependency_key="backend_url")
        self.assertEqual(updated["facts"]["backend_health"]["state_type"], "unknown")

    def test_stale_observation_becomes_unknown(self):
        stale = normalize_evidence_record({"value": True, "state_type": "observed", "expires_at": (datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat()})
        self.assertFalse(is_evidence_fresh(stale))

    def test_verified_evidence_out_ranks_inference(self):
        self.assertTrue(should_replace_evidence({"state_type": "inferred", "confidence": 0.6}, {"state_type": "verified", "confidence": 0.9}))

    def test_explicit_correction_replaces_older_configured_value(self):
        store = {"facts": {}}
        store = set_evidence(store, key="backend_port", record={"value": 8001, "state_type": "configured", "source": "user", "confidence": 1.0})
        store = set_evidence(store, key="backend_port", record={"value": 8002, "state_type": "configured", "source": "user", "confidence": 1.0})
        self.assertEqual(store["facts"]["backend_port"]["value"], 8002)

    def test_unknown_remains_unknown(self):
        self.assertEqual(normalize_evidence_record(None)["state_type"], "unknown")

    def test_prompts_preserve_evidence_labels(self):
        store = {"facts": {"backend_port": {"value": 8001, "state_type": "configured", "source": "user"}}}
        self.assertIn("configured as 8001", render_evidence_for_prompt(store, key="backend_port"))

    def test_trusted_health_check_record_creates_verified_runtime_evidence(self):
        record = record_health_check_result(
            target="backend",
            url="http://127.0.0.1:8002",
            success=True,
            checked_at="2026-07-15T00:00:00+00:00",
            source="health_check",
        )
        self.assertEqual(record["key"], "backend_health")
        self.assertEqual(record["value"], "online")
        self.assertEqual(record["state_type"], "verified")
        self.assertEqual(record["source"], "health_check")
        self.assertEqual(record["checked_url"], "http://127.0.0.1:8002")
        self.assertEqual(record["checked_at"], "2026-07-15T00:00:00+00:00")

    def test_new_session_does_not_inherit_user_declared_online_state(self):
        durable = {
            "version": 1,
            "facts": {
                "backend_port": {"value": 8002, "state_type": "configured", "source": "user"},
            },
        }
        session_a = {
            "version": 1,
            "facts": {
                "backend_health": {"value": "online", "state_type": "declared", "source": "user"},
            },
        }
        merged_session_b = merge_evidence_stores(durable, {"version": 1, "facts": {}})
        self.assertEqual(merged_session_b["facts"]["backend_port"]["value"], 8002)
        self.assertNotIn("backend_health", merged_session_b["facts"])

        merged_session_a = merge_evidence_stores(durable, session_a)
        self.assertEqual(merged_session_a["facts"]["backend_health"]["state_type"], "declared")

    def test_extractors_split_durable_and_session_scoped_facts(self):
        combined = {
            "version": 1,
            "facts": {
                "backend_port": {"value": 8002, "state_type": "configured", "source": "user"},
                "backend_health": {"value": "online", "state_type": "declared", "source": "user"},
            },
        }
        durable = extract_durable_evidence_store(combined)
        session = extract_session_scoped_evidence_store(combined)

        self.assertIn("backend_port", durable["facts"])
        self.assertNotIn("backend_health", durable["facts"])
        self.assertIn("backend_health", session["facts"])
        self.assertNotIn("backend_port", session["facts"])


if __name__ == "__main__":
    unittest.main()
