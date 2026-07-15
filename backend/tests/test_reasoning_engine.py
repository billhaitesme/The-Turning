import unittest

from services.reasoning_engine import (
    build_reasoning_prompt_context,
    empty_reasoning_result,
    resolve_evidence_record,
    resolve_evidence_store,
)


class ReasoningEngineTests(unittest.TestCase):
    def test_missing_evidence_resolves_unknown(self):
        record = resolve_evidence_record("backend_health", None)
        self.assertEqual(record["status"], "unknown")
        self.assertEqual(record["reason"], "No evidence exists.")

    def test_configured_evidence_resolves_configured(self):
        record = resolve_evidence_record("backend_port", {"value": 8002, "state_type": "configured", "source": "user", "confidence": 1.0})
        self.assertEqual(record["status"], "resolved")
        self.assertEqual(record["state_type"], "configured")
        self.assertEqual(record["value"], 8002)

    def test_expired_evidence_resolves_stale(self):
        record = resolve_evidence_record("backend_health", {"value": True, "state_type": "expired", "source": "health_check"})
        self.assertEqual(record["status"], "stale")
        self.assertEqual(record["state_type"], "expired")

    def test_invalidated_evidence_resolves_invalidated(self):
        record = resolve_evidence_record("backend_health", {"value": True, "state_type": "invalidated", "source": "health_check", "notes": "Port changed after verification."})
        self.assertEqual(record["status"], "invalidated")
        self.assertIn("Port changed", record["reason"])

    def test_verified_evidence_resolves_verified(self):
        record = resolve_evidence_record("backend_health", {"value": True, "state_type": "verified", "source": "health_check", "confidence": 1.0})
        self.assertEqual(record["status"], "resolved")
        self.assertEqual(record["state_type"], "verified")

    def test_prompt_context_mentions_uncertainty(self):
        reasoning = empty_reasoning_result()
        reasoning["resolved_beliefs"] = [
            {"key": "backend_port", "value": 8002, "status": "resolved", "state_type": "configured", "reason": "Resolved from the strongest current evidence."}
        ]
        reasoning["uncertainties"] = [
            {"key": "backend_health", "status": "unknown", "reason": "Current health is unknown."}
        ]
        text = build_reasoning_prompt_context(reasoning)
        self.assertIn("Resolved:", text)
        self.assertIn("Unknown:", text)
        self.assertIn("backend health", text.lower())

    def test_resolve_store_supports_records_shape(self):
        store = {"version": 1, "records": {"backend_port": {"value": 8002, "state_type": "configured", "source": "user"}}}
        resolved = resolve_evidence_store(store)
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0]["key"], "backend_port")


if __name__ == "__main__":
    unittest.main()
