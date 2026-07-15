from fastapi import APIRouter
from core.config import settings
from services.goal_engine import load_goal_store
from services.knowledge_graph import load_graph

router = APIRouter(prefix="/system", tags=["system"])

@router.get("/config")
def get_runtime_config():
    return {
        "chat_model": settings.chat_model,
        "reasoning_model": settings.reasoning_model,
        "vision_model": settings.vision_model,
        "router_model": settings.router_model,
        "embedding_model": settings.embedding_model,
        "network_mode": settings.network_mode,
        "personality_mode": settings.personality_mode,
    }


@router.get("/cognition")
def get_cognition_state():
    return {
        "goals": load_goal_store(),
        "knowledge_graph": load_graph(),
    }
