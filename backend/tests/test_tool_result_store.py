import tempfile
import unittest
from pathlib import Path

from services.tool_contracts import build_tool_request
from services.tool_result_store import (
    append_tool_result,
    empty_tool_result_store,
    get_tool_result,
    list_tool_results,
    load_tool_result_store,
    save_tool_result_store,
)
from services.tool_results import create_tool_result


class ToolResultStoreTests(unittest.TestCase):
    def test_malformed_store_returns_empty_valid_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tool_results.json"
            path.write_text("{not-json", encoding="utf-8")
            store = load_tool_result_store(path)
            self.assertEqual(store, empty_tool_result_store())

    def test_append_tool_result_is_append_only(self):
        store = empty_tool_result_store()
        result = create_tool_result(
            request_id="toolreq-1",
            tool_name="backend_health_check",
            status="completed",
            success=True,
            started_at="2026-07-16T00:00:00+00:00",
            completed_at="2026-07-16T00:00:01+00:00",
            duration_ms=12.0,
            output={"checked_url": "http://127.0.0.1:8001/health"},
            error=None,
            evidence_candidates=[],
            side_effects_observed=[],
        )
        append_tool_result(result, store=store)
        append_tool_result({**result, "completed_at": "2026-07-16T00:00:02+00:00"}, store=store)
        self.assertEqual(len(list_tool_results(store)), 2)
        self.assertEqual(get_tool_result("toolreq-1", store=store)["completed_at"], "2026-07-16T00:00:02+00:00")

    def test_save_and_reload_result_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tool_results.json"
            store = empty_tool_result_store()
            result = create_tool_result(
                request_id="toolreq-2",
                tool_name="backend_health_check",
                status="completed",
                success=False,
                started_at="2026-07-16T00:00:00+00:00",
                completed_at="2026-07-16T00:00:01+00:00",
                duration_ms=20.0,
                output={"checked_url": "http://127.0.0.1:8001/health", "error": "connection refused"},
                error=None,
                evidence_candidates=[],
                side_effects_observed=[],
            )
            append_tool_result(result, store=store)
            save_tool_result_store(store, path)
            reloaded = load_tool_result_store(path)
            self.assertEqual(list_tool_results(reloaded)[0]["request_id"], "toolreq-2")


if __name__ == "__main__":
    unittest.main()
