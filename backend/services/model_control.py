from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass
import json
import logging
import re
from threading import RLock
from typing import Any, Deque, Dict, Optional

from core.config import settings


logger = logging.getLogger("omega_arc.model_control")
logger.setLevel(logging.INFO)

MODEL_NAME_PATTERN = r"[A-Za-z0-9][A-Za-z0-9._/-]*(?::[A-Za-z0-9][A-Za-z0-9._-]*)?"
MODEL_SWITCH_PATTERN = re.compile(
    rf"^\s*(?:switch\s+to|use|set\s+(?:the\s+)?active\s+model\s+to)\s+(?P<model>{MODEL_NAME_PATTERN})\s*[.!]?\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ConversationTelemetry:
    requested_model: str
    selected_model: str
    actual_model: str
    response_time: float
    tokens: Optional[int]
    fallback_used: bool
    reason: str = "User Selection"
    topic_routing: str = "Disabled"
    secondary_rewrite: str = "Disabled"


class ModelControl:
    """Thread-safe authority for conversational model selection and audit data."""

    def __init__(self, active_model: Optional[str] = None) -> None:
        self._lock = RLock()
        self._active_model = self._validate_model(active_model or settings.active_chat_model)
        # The configured default is an operator selection, even before a live switch.
        self._user_selected = True
        self._telemetry: Deque[ConversationTelemetry] = deque(maxlen=200)

    @staticmethod
    def _validate_model(model: str) -> str:
        candidate = str(model or "").strip()
        if not re.fullmatch(MODEL_NAME_PATTERN, candidate):
            raise ValueError("Model names may contain letters, numbers, '.', '_', '/', '-', and one optional ':tag'.")
        return candidate

    def select_chat_model(self) -> str:
        with self._lock:
            return self._active_model

    def set_active_model(self, model: str, *, user_selected: bool = True) -> str:
        candidate = self._validate_model(model)
        with self._lock:
            self._active_model = candidate
            self._user_selected = user_selected
            return self._active_model

    def parse_explicit_switch(self, message: str) -> Optional[str]:
        match = MODEL_SWITCH_PATTERN.fullmatch(str(message or ""))
        return self._validate_model(match.group("model")) if match else None

    def record(self, telemetry: ConversationTelemetry) -> Dict[str, Any]:
        with self._lock:
            self._telemetry.append(telemetry)
        payload = asdict(telemetry)
        logger.info("Conversation Request %s", json.dumps(payload, sort_keys=True))
        return payload

    def status(self) -> Dict[str, Any]:
        with self._lock:
            latest = asdict(self._telemetry[-1]) if self._telemetry else None
            return {
                "active_model": self._active_model,
                "model_lock": settings.model_lock,
                "topic_routing": settings.allow_topic_routing,
                "secondary_rewrite": settings.allow_secondary_rewrite,
                "automatic_fallback": settings.allow_automatic_model_fallback,
                "fallback_model": settings.automatic_model_fallback_model if settings.allow_automatic_model_fallback else None,
                "user_selected": self._user_selected,
                "latest_request": latest,
            }

    def telemetry(self) -> list[Dict[str, Any]]:
        with self._lock:
            return [asdict(item) for item in self._telemetry]


model_control = ModelControl()


def select_chat_model() -> str:
    """Return the operator-selected model without inspecting conversational content."""
    return model_control.select_chat_model()
