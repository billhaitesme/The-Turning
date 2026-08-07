import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import app
from fastapi.testclient import TestClient


class _Response:
    def __init__(self, *, model="dolphin-mixtral:8x7b", content="verbatim output", tokens=5):
        self.model = model
        self.content = content
        self.tokens = tokens

    def raise_for_status(self):
        return None

    def json(self):
        return {
            "model": self.model,
            "message": {"content": self.content},
            "eval_count": self.tokens,
        }


class _Client:
    response = _Response()
    error = None
    last_payload = None

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, *args, **kwargs):
        type(self).last_payload = kwargs["json"]
        if type(self).error:
            raise type(self).error
        return type(self).response


class _FallbackClient(_Client):
    models = []

    def post(self, *args, **kwargs):
        model = kwargs["json"]["model"]
        type(self).models.append(model)
        if len(type(self).models) == 1:
            raise RuntimeError("primary unavailable")
        return _Response(model=model, content="explicit fallback output")


class _PartialStreamResponse:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def raise_for_status(self):
        return None

    def iter_lines(self):
        yield json.dumps({
            "model": "dolphin-mixtral:8x7b",
            "message": {"content": "partial"},
            "done": False,
        })
        raise RuntimeError("stream broke")


class _PartialStreamClient(_Client):
    models = []

    def stream(self, *args, **kwargs):
        type(self).models.append(kwargs["json"]["model"])
        return _PartialStreamResponse()


class ModelInferenceControlTests(unittest.TestCase):
    def setUp(self):
        app.model_control.set_active_model("dolphin-mixtral:8x7b")
        _Client.response = _Response()
        _Client.error = None
        _Client.last_payload = None
        self.settings = SimpleNamespace(
            allow_automatic_model_fallback=False,
            automatic_model_fallback_model="llama3.1:8b",
        )

    def _generate(self):
        with (
            patch.object(app, "settings", self.settings),
            patch.object(app.httpx, "Client", _Client),
            patch.object(
                app,
                "build_ollama_messages",
                return_value=[{"role": "user", "content": "exact input"}],
            ),
        ):
            return app.generate_response_text(
                history=[],
                user_message="exact input",
                user_profile={"preferences": {}},
                memories=[],
            )

    def test_selected_model_receives_input_and_output_is_unmodified(self):
        self.assertEqual(self._generate(), "verbatim output")
        self.assertEqual(_Client.last_payload["model"], "dolphin-mixtral:8x7b")
        self.assertEqual(_Client.last_payload["messages"][-1]["content"], "exact input")
        latest = app.model_control.status()["latest_request"]
        self.assertEqual(latest["requested_model"], "dolphin-mixtral:8x7b")
        self.assertEqual(latest["actual_model"], "dolphin-mixtral:8x7b")
        self.assertFalse(latest["fallback_used"])

    def test_unavailable_model_does_not_fallback_by_default(self):
        _Client.error = RuntimeError("not installed")
        with self.assertRaisesRegex(app.ModelUnavailableError, "Automatic fallback is disabled"):
            self._generate()
        self.assertFalse(app.model_control.status()["latest_request"]["fallback_used"])

    def test_provider_model_substitution_is_rejected(self):
        _Client.response = _Response(model="gemma3:1b")
        with self.assertRaises(app.ModelUnavailableError):
            self._generate()

    def test_fallback_occurs_only_when_explicitly_enabled(self):
        self.settings.allow_automatic_model_fallback = True
        _FallbackClient.models = []
        with (
            patch.object(app, "settings", self.settings),
            patch.object(app.httpx, "Client", _FallbackClient),
            patch.object(app, "build_ollama_messages", return_value=[]),
        ):
            output = app.generate_response_text(
                history=[],
                user_message="exact input",
                user_profile={"preferences": {}},
                memories=[],
            )

        self.assertEqual(output, "explicit fallback output")
        self.assertEqual(_FallbackClient.models, ["dolphin-mixtral:8x7b", "llama3.1:8b"])
        latest = app.model_control.status()["latest_request"]
        self.assertEqual(latest["selected_model"], "dolphin-mixtral:8x7b")
        self.assertEqual(latest["actual_model"], "llama3.1:8b")
        self.assertTrue(latest["fallback_used"])

    def test_partial_stream_failure_is_audited_and_never_spliced(self):
        self.settings.allow_automatic_model_fallback = True
        _PartialStreamClient.models = []
        with (
            patch.object(app, "settings", self.settings),
            patch.object(app.httpx, "Client", _PartialStreamClient),
            patch.object(app, "build_ollama_messages", return_value=[]),
        ):
            with self.assertRaisesRegex(RuntimeError, "stream broke"):
                list(app.stream_response_text(
                    history=[],
                    user_message="exact input",
                    user_profile={"preferences": {}},
                    memories=[],
                ))

        self.assertEqual(_PartialStreamClient.models, ["dolphin-mixtral:8x7b"])
        latest = app.model_control.status()["latest_request"]
        self.assertEqual(latest["actual_model"], "dolphin-mixtral:8x7b")
        self.assertFalse(latest["fallback_used"])

    def test_model_control_http_contract_switches_and_reports_effective_policy(self):
        client = TestClient(app.app)
        response = client.post("/system/model-control", json={"model": "llama3.1:8b"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["active_model"], "llama3.1:8b")

        status = client.get("/system/status")
        self.assertEqual(status.status_code, 200)
        control = status.json()["model_control"]
        self.assertEqual(control["active_model"], "llama3.1:8b")
        self.assertFalse(control["topic_routing"])
        self.assertFalse(control["secondary_rewrite"])


if __name__ == "__main__":
    unittest.main()
