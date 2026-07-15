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
    request_timeout_seconds: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "180"))
    enable_cognition_pipeline: bool = os.getenv("ENABLE_COGNITION_PIPELINE", "true").lower() == "true"
    enable_cognition_context: bool = os.getenv("ENABLE_COGNITION_CONTEXT", "false").lower() == "true"
    enable_curiosity_suggestions: bool = os.getenv("ENABLE_CURIOSITY_SUGGESTIONS", "false").lower() == "true"

settings = Settings()
