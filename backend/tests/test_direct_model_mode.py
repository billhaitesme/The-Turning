import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import app
from fastapi.testclient import TestClient


class _UnavailableClient:
    models = []

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, *args, **kwargs):
        type(self).models.append(kwargs["json"]["model"])
        raise RuntimeError("unavailable")


class DirectModelModeTests(unittest.TestCase):
    def setUp(self):
        app.init_db()
        app.model_control.set_active_model("llama3.1:8b")
        self.client = TestClient(app.app)
        response = self.client.post("/conversations", json={"user_id": "direct-mode-test"})
        self.conversation_id = response.json()["conversation_id"]

    def test_direct_message_builder_preserves_only_raw_transcript(self):
        history = [
            {"role": "system", "content": "must be omitted"},
            {"role": "user", "content": "prior input"},
            {"role": "assistant", "content": "prior output"},
        ]

        messages = app.build_direct_model_messages(history=history, user_message="exact new input")

        self.assertEqual(messages, [
            {"role": "user", "content": "prior input"},
            {"role": "assistant", "content": "prior output"},
            {"role": "user", "content": "exact new input"},
        ])

    def test_direct_chat_pins_model_and_skips_runtime_processors(self):
        forbidden = AssertionError("runtime processor called in direct mode")
        with (
            patch.object(app, "generate_response_text", return_value="verbatim direct output") as generate,
            patch.object(app, "get_user_profile", side_effect=forbidden),
            patch.object(app, "search_memories", side_effect=forbidden),
            patch.object(app, "persist_learning", side_effect=forbidden),
            patch.object(app, "build_declarative_acknowledgement", side_effect=forbidden),
            patch.object(app, "run_reasoning_pipeline", side_effect=forbidden),
            patch.object(app, "run_planning_pipeline", side_effect=forbidden),
            patch.object(app, "run_deliberation_pipeline", side_effect=forbidden),
            patch.object(app, "process_completed_turn", side_effect=forbidden),
        ):
            response = self.client.post("/chat", json={
                "conversation_id": self.conversation_id,
                "user_id": "direct-mode-test",
                "message": "exact new input",
                "mode": "direct",
            })

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["reply"], "verbatim direct output")
        self.assertEqual(payload["learning"], {})
        self.assertEqual(payload["mode"], "direct")
        self.assertEqual(payload["model_control"]["active_model"], app.DIRECT_CHAT_MODEL)
        generate.assert_called_once_with(
            history=[],
            user_message="exact new input",
            user_profile={},
            memories=[],
            conversation_id=self.conversation_id,
            direct_mode=True,
        )

    def test_direct_mode_rejects_a_different_request_model(self):
        response = self.client.post("/chat", json={
            "conversation_id": self.conversation_id,
            "message": "hello",
            "mode": "direct",
            "model": "gemma3:1b",
        })

        self.assertEqual(response.status_code, 422)
        self.assertIn(app.DIRECT_CHAT_MODEL, response.json()["detail"])

    def test_direct_mode_never_uses_configured_fallback(self):
        _UnavailableClient.models = []
        settings = SimpleNamespace(
            allow_automatic_model_fallback=True,
            automatic_model_fallback_model="llama3.1:8b",
        )
        app.model_control.set_active_model(app.DIRECT_CHAT_MODEL)

        with (
            patch.object(app, "settings", settings),
            patch.object(app.httpx, "Client", _UnavailableClient),
            self.assertRaises(app.ModelUnavailableError),
        ):
            app.generate_response_text(
                history=[],
                user_message="exact input",
                user_profile={},
                memories=[],
                direct_mode=True,
            )

        self.assertEqual(_UnavailableClient.models, [app.DIRECT_CHAT_MODEL])

    def test_direct_stream_has_no_runtime_events_or_learning(self):
        def direct_stream(**kwargs):
            self.assertTrue(kwargs["direct_mode"])
            yield f"data: {json.dumps({'type': 'delta', 'text': 'raw stream'})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'text': 'raw stream'})}\n\n"

        forbidden = AssertionError("runtime processor called in direct mode")
        with (
            patch.object(app, "stream_response_text", side_effect=direct_stream),
            patch.object(app, "get_user_profile", side_effect=forbidden),
            patch.object(app, "search_memories", side_effect=forbidden),
            patch.object(app, "persist_learning", side_effect=forbidden),
            patch.object(app, "process_completed_turn", side_effect=forbidden),
        ):
            response = self.client.post("/chat/stream", json={
                "conversation_id": self.conversation_id,
                "message": "stream this",
                "mode": "direct",
            })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["x-conversation-mode"], "direct")
        self.assertIn('"type": "mode"', response.text)
        self.assertNotIn('"type": "learning"', response.text)
        self.assertNotIn('"type": "memory"', response.text)
        self.assertNotIn('"type": "phase"', response.text)


if __name__ == "__main__":
    unittest.main()
