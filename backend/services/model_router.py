from core.config import settings
from models.routing import RouteDecision, TaskType
from services.model_control import select_chat_model

def choose_route(user_message, *, identity_intent="general", has_image=False, memory_requested=False):
    """Select deterministic subsystems without semantically routing chat models."""
    if has_image:
        return RouteDecision(TaskType.VISION, settings.vision_model, True, False, True, "An image was supplied.")
    return RouteDecision(TaskType.GENERAL, select_chat_model(), True, False, False, "User Selection")
