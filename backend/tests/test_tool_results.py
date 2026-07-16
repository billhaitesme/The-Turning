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
        candidates = tool_result_to_evidence_candidates(result)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["kind"], "observed_failure")
        self.assertEqual(candidates[0]["request_id"], "toolreq-123")
        self.assertEqual(candidates[0]["adapter_name"], "local_adapter")

    def test_verified_evidence_candidates_preserve_provenance(self):
        result = create_tool_result(
            request_id="toolreq-456",
            tool_name="backend_health_check",
            status="completed",
            success=True,
            started_at="2026-07-16T00:00:00+00:00",
            completed_at="2026-07-16T00:00:00+00:00",
            duration_ms=4.0,
            output={"checked": True},
            evidence_candidates=[],
            side_effects_observed=[],
            execution_mode="live",
        )
        candidates = tool_result_to_evidence_candidates(result)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["request_id"], "toolreq-456")
        self.assertEqual(candidates[0]["adapter_name"], "local_adapter")


if __name__ == "__main__":
    unittest.main()
