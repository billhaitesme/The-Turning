from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Settings:
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    chat_model: str = os.getenv("OLLAMA_CHAT_MODEL", "llama2-uncensored:7b")
    reasoning_model: str = os.getenv("OLLAMA_REASONING_MODEL", "llama3.1:8b")
    vision_model: str = os.getenv("OLLAMA_VISION_MODEL", "llava:7b")
    router_model: str = os.getenv("OLLAMA_ROUTER_MODEL", "gemma3:1b")
    embedding_model: str = os.getenv("OLLAMA_EMBED_MODEL", "embeddinggemma:latest")
    network_mode: str = os.getenv("NETWORK_MODE", "offline")
    personality_mode: str = os.getenv("ACTIVE_PERSONALITY_MODE", "default")
    enable_tool_framework: bool = os.getenv("ENABLE_TOOL_FRAMEWORK", "true").lower() == "true"
    enable_tool_execution: bool = os.getenv("ENABLE_TOOL_EXECUTION", "false").lower() == "true"
    enable_tool_dry_run: bool = os.getenv("ENABLE_TOOL_DRY_RUN", "true").lower() == "true"
    enable_critical_tools: bool = os.getenv("ENABLE_CRITICAL_TOOLS", "false").lower() == "true"
    tool_approval_ttl_seconds: int = int(os.getenv("TOOL_APPROVAL_TTL_SECONDS", "300"))
    request_timeout_seconds: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "180"))
    enable_cognition_pipeline: bool = os.getenv("ENABLE_COGNITION_PIPELINE", "true").lower() == "true"
    enable_cognition_context: bool = os.getenv("ENABLE_COGNITION_CONTEXT", "false").lower() == "true"
    enable_curiosity_suggestions: bool = os.getenv("ENABLE_CURIOSITY_SUGGESTIONS", "false").lower() == "true"
    enable_reasoning_pipeline: bool = os.getenv("ENABLE_REASONING_PIPELINE", "true").lower() == "true"
    enable_reasoning_context: bool = os.getenv("ENABLE_REASONING_CONTEXT", "false").lower() == "true"
    enable_action_recommendations: bool = os.getenv("ENABLE_ACTION_RECOMMENDATIONS", "true").lower() == "true"
    enable_planning_pipeline: bool = os.getenv("ENABLE_PLANNING_PIPELINE", "true").lower() == "true"
    enable_planning_context: bool = os.getenv("ENABLE_PLANNING_CONTEXT", "false").lower() == "true"
    enable_decision_records: bool = os.getenv("ENABLE_DECISION_RECORDS", "true").lower() == "true"
    enable_automatic_plan_revision: bool = os.getenv("ENABLE_AUTOMATIC_PLAN_REVISION", "true").lower() == "true"
    enable_deliberation_pipeline: bool = os.getenv("ENABLE_DELIBERATION_PIPELINE", "true").lower() == "true"
    enable_deliberation_context: bool = os.getenv("ENABLE_DELIBERATION_CONTEXT", "false").lower() == "true"
    enable_plan_execution: bool = os.getenv("ENABLE_PLAN_EXECUTION", "false").lower() == "true"

settings = Settings()
