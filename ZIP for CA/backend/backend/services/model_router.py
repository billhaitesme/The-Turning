from core.config import settings
from models.routing import RouteDecision, TaskType

CURRENT_INFO_TERMS = {"today","latest","current","recent","news","price","weather","updated"}
TECHNICAL_TERMS = {"api","python","javascript","react","fastapi","database","network","code","debug","error","algorithm","embedding"}

def choose_route(user_message, *, identity_intent="general", has_image=False, memory_requested=False):
    text = " ".join(user_message.lower().split())
    if has_image:
        return RouteDecision(TaskType.VISION, settings.vision_model, True, False, True, "An image was supplied.")
    if identity_intent == "vow":
        return RouteDecision(TaskType.VOW, settings.chat_model, False, False, False, "The user requested the vow.")
    if identity_intent == "identity":
        return RouteDecision(TaskType.IDENTITY, settings.chat_model, True, False, False, "Assistant identity requested.")
    if identity_intent == "user_identity":
        return RouteDecision(TaskType.USER_IDENTITY, settings.chat_model, True, False, False, "User identity requested.")
    if any(term in text for term in CURRENT_INFO_TERMS):
        return RouteDecision(TaskType.CURRENT_INFO, settings.reasoning_model, True, settings.network_mode == "automatic", False, "Current information may be required.")
    if memory_requested:
        return RouteDecision(TaskType.MEMORY, settings.chat_model, True, False, False, "Memory request.")
    if any(term in text for term in TECHNICAL_TERMS):
        return RouteDecision(TaskType.TECHNICAL, settings.reasoning_model, True, False, False, "Technical request.")
    return RouteDecision(TaskType.GENERAL, settings.chat_model, True, False, False, "General request.")
