import unittest

from services.evidence_engine import get_evidence
from services.reasoning_pipeline import rebuild_reasoning_after_evidence_ingestion
from services.tool_evidence_bridge import apply_tool_result_to_evidence_store, tool_result_to_evidence_candidates
from services.tool_results import create_tool_result


class ToolEvidenceBridgeTests(unittest.TestCase):
    def _online_result(self):
        return create_tool_result(
            request_id="toolreq-1",
            tool_name="backend_health_check",
            status="completed",
            success=True,
            started_at="2026-07-16T00:00:00+00:00",
            completed_at="2026-07-16T00:00:01+00:00",
            duration_ms=12.5,
            output={
                "target": "backend",
                "checked_url": "http://127.0.0.1:8001/health",
                "success": True,
                "status_code": 200,
                "latency_ms": 12.5,
                "checked_at": "2026-07-16T00:00:01+00:00",
                "error": None,
            },
            error=None,
            evidence_candidates=[],
            side_effects_observed=[],
            execution_mode="live",
        )

    def _offline_result(self):
        return create_tool_result(
            request_id="toolreq-2",
            tool_name="backend_health_check",
            status="completed",
            success=False,
            started_at="2026-07-16T00:00:00+00:00",
            completed_at="2026-07-16T00:00:01+00:00",
            duration_ms=3000.0,
            output={
                "target": "backend",
                "checked_url": "http://127.0.0.1:8001/health",
                "success": False,
                "status_code": None,
                "latency_ms": 3000.0,
                "checked_at": "2026-07-16T00:00:01+00:00",
                "error": "connection refused",
            },
            error=None,
            evidence_candidates=[],
            side_effects_observed=[],
            execution_mode="live",
        )

    def test_verified_online_candidate_is_trusted(self):
        candidates = tool_result_to_evidence_candidates(self._online_result())
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["value"], "online")
        self.assertEqual(candidates[0]["metadata"]["status_code"], 200)

    def test_endpoint_mismatch_blocks_verified_evidence(self):
        store = {"version": 1, "facts": {"backend_port": {"key": "backend_port", "value": 8002, "state_type": "configured", "source": "user", "confidence": 1.0, "dependencies": [], "scope": "durable"}}}
        updated_store, candidates = apply_tool_result_to_evidence_store(store, self._online_result(), configured_backend_port=8002)
        self.assertEqual(candidates, [])
        self.assertEqual(get_evidence(updated_store, "backend_health")["state_type"], "unknown")

    def test_reasoning_updates_after_evidence_ingestion(self):
        store = {"version": 1, "facts": {"backend_port": {"key": "backend_port", "value": 8001, "state_type": "configured", "source": "user", "confidence": 1.0, "dependencies": [], "scope": "durable"}}}
        updated_store, _ = apply_tool_result_to_evidence_store(store, self._online_result(), configured_backend_port=8001)
        reasoning = rebuild_reasoning_after_evidence_ingestion(evidence_store=updated_store, goal_store={"goals": []}, previous_evidence_store=store)
        beliefs = {item["key"]: item for item in reasoning["resolved_beliefs"]}
        self.assertEqual(beliefs["backend_health"]["status"], "resolved")
        self.assertEqual(beliefs["backend_health"]["state_type"], "verified")

    def test_offline_candidate_is_verified(self):
        candidates = tool_result_to_evidence_candidates(self._offline_result())
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["value"], "offline")
        self.assertEqual(candidates[0]["metadata"]["error"], "connection refused")


if __name__ == "__main__":
    unittest.main()
