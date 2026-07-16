import unittest

from services.reasoning_engine import (
    build_reasoning_prompt_context,
    empty_reasoning_result,
    render_backend_state_for_prompt,
    sanitize_prompt_messages,
    sanitize_prompt_text,
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

    def test_user_declared_online_renders_declared_not_verified(self):
        store = {
            "version": 1,
            "facts": {
                "backend_port": {"value": 8001, "state_type": "configured", "source": "user"},
                "backend_health": {"value": "online", "state_type": "declared", "source": "user"},
            },
        }
        text = render_backend_state_for_prompt(store, {})
        self.assertIn("Reported health: online", text)
        self.assertIn("Source: user declaration", text)
        self.assertIn("Verification: not independently verified", text)

    def test_user_declared_online_not_overwritten_by_legacy_false(self):
        store = {
            "version": 1,
            "facts": {
                "backend_port": {"value": 8001, "state_type": "configured", "source": "user"},
                "backend_health": {"value": "online", "state_type": "declared", "source": "user", "notes": "legacy false exists elsewhere"},
            },
        }
        text = render_backend_state_for_prompt(store, {"resolved_beliefs": []})
        self.assertIn("Reported health: online", text)
        self.assertNotIn("Runtime health: unknown", text)

    def test_user_declared_offline_renders_declared_not_verified(self):
        store = {
            "version": 1,
            "facts": {
                "backend_port": {"value": 8001, "state_type": "configured", "source": "user"},
                "backend_health": {"value": "offline", "state_type": "declared", "source": "user"},
            },
        }
        text = render_backend_state_for_prompt(store, {})
        self.assertIn("Reported health: offline", text)
        self.assertIn("Verification: not independently verified", text)

    def test_matching_health_check_renders_verified(self):
        store = {
            "version": 1,
            "facts": {
                "backend_port": {"value": 8001, "state_type": "configured", "source": "user"},
                "backend_health": {
                    "value": "online",
                    "state_type": "verified",
                    "source": "health_check",
                    "checked_url": "http://127.0.0.1:8001",
                    "observed_at": "2026-07-15T00:00:00+00:00",
                },
            },
        }
        text = render_backend_state_for_prompt(store, {})
        self.assertIn("Runtime health: online", text)
        self.assertIn("Verification: current", text)
        self.assertIn("Checked endpoint: http://127.0.0.1:8001", text)

    def test_mismatched_endpoint_verification_renders_unknown(self):
        store = {
            "version": 1,
            "facts": {
                "backend_port": {"value": 8002, "state_type": "configured", "source": "user"},
                "backend_health": {"value": "online", "state_type": "verified", "source": "health_check"},
            },
        }
        reasoning = {
            "resolved_beliefs": [
                {"key": "backend_health", "status": "unknown", "value": None},
            ]
        }
        text = render_backend_state_for_prompt(store, reasoning)
        self.assertIn("Runtime health: unknown", text)
        self.assertIn("Verification: none", text)

    def test_prompt_sanitization_removes_legacy_backend_online_booleans(self):
        self.assertNotIn("Backend online: False", sanitize_prompt_text("Backend online: False"))
        self.assertNotIn("Backend online: True", sanitize_prompt_text("Backend online: True"))

    def test_prompt_message_sanitization_removes_legacy_backend_online_booleans(self):
        messages = [{"role": "system", "content": "Backend online: False\nBackend online: True"}]
        sanitized = sanitize_prompt_messages(messages)
        self.assertNotIn("Backend online: False", sanitized[0]["content"])
        self.assertNotIn("Backend online: True", sanitized[0]["content"])


if __name__ == "__main__":
    unittest.main()
