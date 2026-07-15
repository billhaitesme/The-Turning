import unittest
from datetime import datetime, timedelta, timezone

from services.evidence_engine import (
    empty_evidence_record,
    invalidate_dependent_evidence,
    is_evidence_fresh,
    normalize_evidence_record,
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


if __name__ == "__main__":
    unittest.main()
