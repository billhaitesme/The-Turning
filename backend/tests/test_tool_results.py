import unittest

from services.tool_results import create_tool_result, tool_result_to_evidence_candidates


class ToolResultTests(unittest.TestCase):
    def test_result_contains_timestamps_and_duration(self):
        result = create_tool_result(
            request_id="toolreq-123",
            tool_name="backend_health_check",
            status="completed",
            success=True,
            started_at="2026-07-16T00:00:00+00:00",
            completed_at="2026-07-16T00:00:00+00:00",
            duration_ms=12.3,
            output={"safe": True},
            evidence_candidates=[],
            side_effects_observed=[],
        )
        self.assertEqual(result["started_at"], "2026-07-16T00:00:00+00:00")
        self.assertEqual(result["duration_ms"], 12.3)

    def test_dry_run_never_creates_verified_evidence(self):
        result = create_tool_result(
            request_id="toolreq-123",
            tool_name="backend_health_check",
            status="completed",
            success=True,
            started_at="2026-07-16T00:00:00+00:00",
            completed_at="2026-07-16T00:00:00+00:00",
            duration_ms=1.0,
            output={"would_check": "http://127.0.0.1:8001/health", "safe": True},
            evidence_candidates=[],
            side_effects_observed=[],
            execution_mode="dry_run",
        )
        self.assertEqual(tool_result_to_evidence_candidates(result), [])

    def test_failed_result_is_structured_and_emits_observed_failure_candidate(self):
        result = create_tool_result(
            request_id="toolreq-123",
            tool_name="backend_health_check",
            status="failed",
            success=False,
            started_at="2026-07-16T00:00:00+00:00",
            completed_at="2026-07-16T00:00:00+00:00",
            duration_ms=3.0,
            output={},
            error={"code": "not_implemented", "message": "stubbed"},
            evidence_candidates=[],
            side_effects_observed=[],
        )
        self.assertFalse(result["success"])
        self.assertEqual(tool_result_to_evidence_candidates(result), [])

    def test_completed_health_check_can_yield_verified_evidence(self):
        result = create_tool_result(
            request_id="toolreq-456",
            tool_name="backend_health_check",
            status="completed",
            success=True,
            started_at="2026-07-16T00:00:00+00:00",
            completed_at="2026-07-16T00:00:00+00:00",
            duration_ms=4.0,
            output={"checked_url": "http://127.0.0.1:8001/health", "checked_at": "2026-07-16T00:00:00+00:00", "status_code": 200},
            evidence_candidates=[],
            side_effects_observed=[],
            execution_mode="live",
        )
        candidates = tool_result_to_evidence_candidates(result)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["key"], "backend_health")
        self.assertEqual(candidates[0]["value"], "online")
        self.assertEqual(candidates[0]["metadata"]["request_id"], "toolreq-456")

    def test_completed_offline_health_check_yields_verified_offline_evidence(self):
        result = create_tool_result(
            request_id="toolreq-789",
            tool_name="backend_health_check",
            status="completed",
            success=False,
            started_at="2026-07-16T00:00:00+00:00",
            completed_at="2026-07-16T00:00:01+00:00",
            duration_ms=4.0,
            output={"checked_url": "http://127.0.0.1:8001/health", "error": "connection refused"},
            evidence_candidates=[],
            side_effects_observed=[],
            execution_mode="live",
        )
        candidates = tool_result_to_evidence_candidates(result)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["value"], "offline")
        self.assertEqual(candidates[0]["metadata"]["error"], "connection refused")


if __name__ == "__main__":
    unittest.main()
