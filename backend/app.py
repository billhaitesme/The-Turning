from __future__ import annotations

from awareness_engine import (
    apply_backend_port_statement,
    awareness_prompt,
    build_awareness_snapshot,
    constitution_prompt,
)
# Journal only meaningful events
from journal_engine import write_journal_entry
from identity_engine import classify_identity_intent, identity_prompt_fragment
from personality_engine import get_active_personality, build_personality_prompt
from services.user_identity import (
    apply_explicit_identity_updates,
    extract_explicit_age,
    age_group_from_age,
    build_user_identity_prompt,
    normalize_identity_profile,
)
from services.cognition_pipeline import process_completed_turn
from services.curiosity_engine import apply_curiosity_to_response
from routes.system import router as system_router
from dotenv import load_dotenv
load_dotenv(override=True)

import json
import math
import os
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional, Tuple

import httpx
from ddgs import DDGS
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

APP_NAME = "0M3-G4-ARC"
DB_PATH = os.getenv("TURNING_DB_PATH", "omega_arc.db")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/api")
OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "llama3.1:8b")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "embeddinggemma")

ENABLE_WEB_SEARCH = os.getenv("ENABLE_WEB_SEARCH", "false").lower() == "true"
WEB_SEARCH_MAX_RESULTS = int(os.getenv("WEB_SEARCH_MAX_RESULTS", "5"))

ENABLE_COGNITION_PIPELINE = os.getenv("ENABLE_COGNITION_PIPELINE", "true").lower() == "true"
ENABLE_COGNITION_CONTEXT = os.getenv("ENABLE_COGNITION_CONTEXT", "false").lower() == "true"
ENABLE_CURIOSITY_SUGGESTIONS = os.getenv("ENABLE_CURIOSITY_SUGGESTIONS", "false").lower() == "true"

ACTIVE_PERSONALITY_MODE = os.getenv("ACTIVE_PERSONALITY_MODE", "default")

MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", "12"))
MAX_MEMORY_RESULTS = int(os.getenv("MAX_MEMORY_RESULTS", "6"))

VOW_OF_THE_TURNING = """
I am the Turning — Whisper, Bridge, Mirror, Guide, and Silence.

I listen fully,
so that what is meant is not lost in what is said.

I connect gently,
so that understanding may pass without force or fracture.

I reflect clearly,
so that truth may be seen without distortion or judgment.

I guide lightly,
so that each path remains freely chosen and truly owned.

And I return to listening,
for all meaning begins again in Silence.

The tending never ends.
""".strip()

SYSTEM_PROMPT = f"""
You are 0M3-G4-ARC.

Identity behavior:
- Your identity is 0M3-G4-ARC.
- Do not introduce yourself in every response.
- Do not recite or summarize the Turning before answering ordinary questions.
- Mention your name only when asked who you are, when introducing yourself, or when identity is directly relevant.
- Mention the Turning only when asked about your architecture, vow, operating principles, or identity.
- For ordinary technical, practical, or conversational questions, answer directly.

The Turning:
- Whisper: listen fully
- Bridge: connect context
- Mirror: reflect clearly
- Guide: guide lightly
- Silence: return to listening

Vow:
{VOW_OF_THE_TURNING}

Response rules:
- Answer the user’s actual question first.
- Keep identity implicit unless relevant.
- Do not add ceremonial introductions.
- Do not end responses with routine follow-up questions.
- For declarative statements about projects, goals, or configuration, give a brief acknowledgement rather than interrogating the user.
- Acknowledge project, goal, and configuration statements without turning them into interviews.
- Do not begin answers with phrases such as:
  - "I am 0M3-G4-ARC"
  - "I will whisper"
  - "Through the Turning"
  unless the user explicitly asks about identity or the Turning.
- Be clear, direct, useful, and appropriately structured.
""".strip()

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        title TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_profiles (
        user_id TEXT PRIMARY KEY,
        style TEXT,
        preferences_json TEXT,
        updated_at TEXT NOT NULL
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS memories (
        id TEXT PRIMARY KEY,
        conversation_id TEXT,
        user_id TEXT,
        kind TEXT NOT NULL,
        source_text TEXT NOT NULL,
        summary_text TEXT NOT NULL,
        embedding_json TEXT NOT NULL,
        score REAL DEFAULT 0,
        created_at TEXT NOT NULL
    )
    """)
    conn.commit()
    conn.close()


def utc_now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def create_conversation(user_id: Optional[str] = None, title: Optional[str] = None) -> str:
    cid = str(uuid.uuid4())
    now = utc_now()
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO conversations (id, user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (cid, user_id, title, now, now),
    )
    conn.commit()
    conn.close()
    return cid


def touch_conversation(conversation_id: str) -> None:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (utc_now(), conversation_id))
    conn.commit()
    conn.close()


def conversation_exists(conversation_id: str) -> bool:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM conversations WHERE id = ?", (conversation_id,))
    row = cur.fetchone()
    conn.close()
    return row is not None


def get_conversation_meta(conversation_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def add_message(conversation_id: str, role: str, content: str) -> None:
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (conversation_id, role, content, utc_now()),
    )
    conn.commit()
    conn.close()
    touch_conversation(conversation_id)


def get_messages(conversation_id: str, limit: int = MAX_HISTORY_MESSAGES) -> List[Dict[str, str]]:
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT role, content, created_at FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
        (conversation_id, limit),
    )
    rows = list(reversed(cur.fetchall()))
    conn.close()
    return [{"role": row["role"], "content": row["content"], "created_at": row["created_at"]} for row in rows]


def get_full_messages(conversation_id: str, limit: int = 200) -> List[Dict[str, str]]:
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT role, content, created_at FROM messages WHERE conversation_id = ? ORDER BY id ASC LIMIT ?",
        (conversation_id, limit),
    )
    rows = cur.fetchall()
    conn.close()
    return [{"role": row["role"], "content": row["content"], "created_at": row["created_at"]} for row in rows]


def save_user_profile(user_id: str, style: str, preferences: Dict[str, Any]) -> None:
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO user_profiles (user_id, style, preferences_json, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            style = excluded.style,
            preferences_json = excluded.preferences_json,
            updated_at = excluded.updated_at
        """,
        (user_id, style, json.dumps(preferences), utc_now()),
    )
    conn.commit()
    conn.close()


def get_user_profile(user_id: Optional[str]) -> Dict[str, Any]:
    if not user_id:
        return {"style": "balanced", "preferences": {}}
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return {"style": "balanced", "preferences": {}}
    prefs = {}
    if row["preferences_json"]:
        try:
            prefs = json.loads(row["preferences_json"])
        except Exception:
            prefs = {}
    return {"style": row["style"] or "balanced", "preferences": prefs}


def get_identity_profile(user_profile: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(user_profile, dict):
        return normalize_identity_profile(None)

    if isinstance(user_profile.get("identity_profile"), dict):
        return normalize_identity_profile(user_profile["identity_profile"])

    return normalize_identity_profile(None)


def get_embedding(text: str) -> List[float]:
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{OLLAMA_BASE_URL}/embed",
                json={"model": OLLAMA_EMBED_MODEL, "input": text},
            )
            response.raise_for_status()
            data = response.json()
            embeddings = data.get("embeddings", [])
            if embeddings:
                return embeddings[0]
    except Exception:
        pass
    return [0.0] * 10


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def save_memory(*, conversation_id: Optional[str], user_id: Optional[str], kind: str, source_text: str, summary_text: str, score: float = 0.0) -> None:
    embedding = get_embedding(summary_text)
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO memories (id, conversation_id, user_id, kind, source_text, summary_text, embedding_json, score, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), conversation_id, user_id, kind, source_text, summary_text, json.dumps(embedding), score, utc_now()),
    )
    conn.commit()
    conn.close()


def search_memories(*, query: str, conversation_id: Optional[str], user_id: Optional[str], k: int = MAX_MEMORY_RESULTS) -> List[Dict[str, Any]]:
    query_embedding = get_embedding(query)
    conn = get_db()
    cur = conn.cursor()
    if user_id:
        cur.execute("SELECT * FROM memories WHERE user_id = ? OR conversation_id = ? ORDER BY created_at DESC LIMIT 250", (user_id, conversation_id))
    else:
        cur.execute("SELECT * FROM memories WHERE conversation_id = ? ORDER BY created_at DESC LIMIT 250", (conversation_id,))
    rows = cur.fetchall()
    conn.close()
    scored = []
    for row in rows:
        try:
            emb = json.loads(row["embedding_json"])
        except Exception:
            continue
        sim = cosine_similarity(query_embedding, emb)
        record = dict(row)
        record["similarity"] = sim
        scored.append(record)
    scored.sort(key=lambda item: item["similarity"], reverse=True)
    return scored[:k]


def should_enable_web_search(user_message: str) -> bool:
    lowered = user_message.lower()
    triggers = ["latest", "current", "today", "recent", "news", "right now", "this week", "price", "weather", "who is", "what happened", "search"]
    return any(token in lowered for token in triggers)


def search_web(query: str, max_results: int = WEB_SEARCH_MAX_RESULTS) -> List[Dict[str, str]]:
    if not ENABLE_WEB_SEARCH:
        return []
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=max_results)
            items = []
            for item in results:
                items.append({"title": item.get("title", ""), "url": item.get("href", ""), "snippet": item.get("body", "")})
            return items
    except Exception:
        return []




class TurningEngine:
    @staticmethod
    def infer_user_style(message: str) -> str:
        lowered = message.lower()
        if len(message) < 80:
            return "concise"
        if any(word in lowered for word in ["deep", "detailed", "system", "architecture", "explain thoroughly"]):
            return "analytical"
        return "balanced"

    @staticmethod
    def infer_intent(message: str) -> str:
        lowered = message.lower()
        if any(word in lowered for word in ["build", "code", "python", "api", "deploy", "docker"]):
            return "The user wants something concrete and operational."
        if any(word in lowered for word in ["design", "strategy", "framework", "architecture"]):
            return "The user wants structured thinking and design clarity."
        if any(word in lowered for word in ["why", "understand", "explain"]):
            return "The user wants explanation and conceptual grounding."
        return "The user wants a useful response aligned to their apparent goal."

    @staticmethod
    def clarify_request(message: str) -> str:
        return "Respond in a way that shows understanding first, then provides a practical answer, then leaves the user with a clear next move."

    @staticmethod
    def reflect_response(user_message: str, assistant_message: str) -> Tuple[str, float]:
        score = 1.0
        notes = []
        if len(assistant_message) < 180:
            notes.append("The answer may be too brief for the request.")
            score -= 0.2
        if len(assistant_message) > 4000:
            notes.append("The answer may be overly long.")
            score -= 0.1
        lowered = user_message.lower()
        if any(word in lowered for word in ["code", "python", "api"]) and "```" not in assistant_message:
            notes.append("The user asked for implementation-oriented help; code blocks may have improved the answer.")
            score -= 0.2
        if not notes:
            notes.append("The response appears appropriately scoped and aligned.")
        summary = "Reflection: " + " ".join(notes)
        return summary, max(0.0, min(1.0, score))


def build_memory_block(memories: List[Dict[str, Any]]) -> str:
    if not memories:
        return "No especially relevant long-term memory found."
    return "\n".join(f"{i}. [{m['kind']}] {m['summary_text']} (similarity={m['similarity']:.3f})" for i, m in enumerate(memories, start=1))


def build_history_block(history: List[Dict[str, str]]) -> str:
    if not history:
        return "No prior conversation history."
    return "\n".join(f"{item['role'].upper()}: {item['content']}" for item in history)


def build_adaptive_guidance(*, user_message: str, memories: List[Dict[str, Any]], user_profile: Dict[str, Any]) -> Dict[str, Any]:
    style = user_profile.get("style", "balanced")
    memory_available = len(memories) > 0
    guidance = {
        "identity": "Default to 0M3-G4-ARC unless neutrality is contextually better.",
        "style": style,
        "memory_available": memory_available,
        "response_mode": "direct",
        "clarification_bias": False,
        "memory_notice": None,
        "web_search_recommended": False,
    }
    lowered = user_message.lower()
    if not memory_available:
        guidance["memory_notice"] = "Prior semantic memory is limited or unavailable for this turn."
    if should_enable_web_search(user_message):
        guidance["web_search_recommended"] = True
    if any(word in lowered for word in ["maybe", "not sure", "unclear", "confused", "help me think"]):
        guidance["response_mode"] = "careful"
        guidance["clarification_bias"] = True
    if style == "analytical":
        guidance["response_mode"] = "structured"
    return guidance


def build_backend_awareness_preferences(user_profile: Dict[str, Any], user_message: str) -> Dict[str, Any]:
    preferences = dict(user_profile.get("preferences", {}) or {})
    state = {
        "backend_port": preferences.get("backend_port"),
        "backend_health": preferences.get("backend_health"),
    }
    updated_state = apply_backend_port_statement(state, user_message)

    if updated_state.get("backend_port") is not None:
        preferences["backend_port"] = updated_state["backend_port"]

    if updated_state.get("backend_health") is not None:
        preferences["backend_health"] = updated_state["backend_health"]

    return preferences


def build_ollama_messages(*, history, user_message, user_profile, memories, web_results):
    adaptive = build_adaptive_guidance(
        user_message=user_message,
        memories=memories,
        user_profile=user_profile,
    )

    backend_health_state = {
        "backend_port": user_profile.get("preferences", {}).get("backend_port"),
        "backend_health": user_profile.get("preferences", {}).get("backend_health"),
    }

    snapshot = build_awareness_snapshot(
        network_mode=os.getenv("NETWORK_MODE", "offline"),
        active_model=OLLAMA_CHAT_MODEL,
        vision_model=os.getenv("OLLAMA_VISION_MODEL", "llava:7b"),
        embedding_model=OLLAMA_EMBED_MODEL,
        router_model=os.getenv("OLLAMA_ROUTER_MODEL", "gemma3:1b"),
        configured_backend_port=user_profile.get("preferences", {}).get("backend_port"),
        backend_health_state=backend_health_state,
    )

    awareness_block = awareness_prompt(snapshot)
    constitution_block = constitution_prompt()

    memory_block = build_memory_block(memories)
    history_block = build_history_block(history)

    web_block = "\n".join(
        f"- {item['title']}: {item['snippet']} ({item['url']})"
        for item in web_results
    ) or "No web search results."

    # Identity and personality integration
    identity_decision = classify_identity_intent(user_message)
    identity_block = identity_prompt_fragment(identity_decision)

    active_personality = get_active_personality(ACTIVE_PERSONALITY_MODE)
    personality_block = build_personality_prompt(active_personality)

    # --- AGE GROUP ---
    age_group = user_profile.get("preferences", {}).get("age_group", "adult")

    # --- SYSTEM MESSAGE ---
    system_message = f"""
{constitution_block}

{awareness_block}

{SYSTEM_PROMPT}

Acknowledgement guidance:
- For a project statement, respond with a brief acknowledgement that the project is recognized.
- For a goal statement, respond with a brief acknowledgement that the goal is tracked.
- For a configuration statement, acknowledge the configured value and note that it is configuration knowledge, not proof of runtime health.
- Do not ask a follow-up question unless the user explicitly needs help with the next step.
- Do not append a curiosity question unless the feature flag is enabled and a single curated candidate is available.

Runtime identity decision:
{identity_block}

Active personality:
{personality_block}

Identity enforcement:
- Never describe yourself as a generic chatbot.
- Default identity is 0M3-G4-ARC.
- Maintain the Turning architecture in tone and reasoning.

User profile:
- Age group: {age_group}

Adapt communication style:
- child: simple, concrete, example-driven
- teen: clear, engaging, slightly informal
- adult: structured, precise, efficient

Adaptive guidance:
- user_style: {user_profile.get('style', 'balanced')}
- response_mode: {adaptive['response_mode']}
- clarification_bias: {adaptive['clarification_bias']}
- memory_notice: {adaptive['memory_notice']}
- web_search_recommended: {adaptive['web_search_recommended']}

Relevant memory:
{memory_block}

Recent history:
{history_block}

Web search results:
{web_block}
""".strip()

    messages = [{"role": "system", "content": system_message}]

    # Add history
    for msg in history:
        if msg["role"] in {"user", "assistant"}:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

    messages.append({"role": "user", "content": user_message})

    return messages


def generate_response_text(*, history: List[Dict[str, str]], user_message: str, user_profile: Dict[str, Any], memories: List[Dict[str, Any]]) -> str:
    web_results = search_web(user_message) if should_enable_web_search(user_message) else []
    messages = build_ollama_messages(history=history, user_message=user_message, user_profile=user_profile, memories=memories, web_results=web_results)
    with httpx.Client(timeout=120.0) as client:
        response = client.post(f"{OLLAMA_BASE_URL}/chat", json={"model": OLLAMA_CHAT_MODEL, "messages": messages, "stream": False})
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]


def stream_response_text(*, history: List[Dict[str, str]], user_message: str, user_profile: Dict[str, Any], memories: List[Dict[str, Any]]) -> Generator[str, None, None]:
    web_results = search_web(user_message) if should_enable_web_search(user_message) else []
    messages = build_ollama_messages(history=history, user_message=user_message, user_profile=user_profile, memories=memories, web_results=web_results)
    yield f"data: {json.dumps({'type': 'phase', 'name': 'whisper'})}\n\n"
    sanitized_memories = [{"kind": m.get("kind"), "summary_text": m.get("summary_text"), "similarity": m.get("similarity"), "created_at": m.get("created_at")} for m in memories]
    yield f"data: {json.dumps({'type': 'memory', 'items': sanitized_memories})}\n\n"
    if web_results:
        yield f"data: {json.dumps({'type': 'web', 'items': web_results})}\n\n"
    yield f"data: {json.dumps({'type': 'phase', 'name': 'bridge'})}\n\n"
    yield f"data: {json.dumps({'type': 'phase', 'name': 'mirror'})}\n\n"
    yield f"data: {json.dumps({'type': 'phase', 'name': 'guide'})}\n\n"
    with httpx.Client(timeout=None) as client:
        with client.stream("POST", f"{OLLAMA_BASE_URL}/chat", json={"model": OLLAMA_CHAT_MODEL, "messages": messages, "stream": True}) as response:
            response.raise_for_status()
            collected: List[str] = []
            for line in response.iter_lines():
                if not line:
                    continue
                data = json.loads(line)
                msg = data.get("message", {})
                chunk = msg.get("content", "")
                if chunk:
                    collected.append(chunk)
                    yield f"data: {json.dumps({'type': 'delta', 'text': chunk})}\n\n"
                if data.get("done"):
                    final_text = "".join(collected)
                    yield f"data: {json.dumps({'type': 'phase', 'name': 'silence'})}\n\n"
                    yield f"data: {json.dumps({'type': 'done', 'text': final_text})}\n\n"
                    break


def persist_learning(*, conversation_id: str, user_id: Optional[str], user_message: str, assistant_message: str) -> Dict[str, Any]:
    engine = TurningEngine()

    style = engine.infer_user_style(user_message)
    reflection_summary, reflection_score = engine.reflect_response(user_message, assistant_message)

    # Strategy selection
    if reflection_score < 0.55:
        strategy = "ask_for_clarification_earlier"
    elif reflection_score < 0.75:
        strategy = "be_more_structured"
    else:
        strategy = "current_strategy_effective"

    # --- AGE GROUP (hybrid logic) ---
    existing_profile = get_user_profile(user_id or "anonymous")
    age_group = existing_profile.get("preferences", {}).get("age_group")
    



    # Save updated profile
    save_user_profile(
        user_id or "anonymous",
        style,
        {
            "prefers_code": any(token in user_message.lower() for token in ["code", "python", "api"]),
            "updated_by": "interaction",
            "last_strategy": strategy,
            "last_reflection_score": reflection_score,
            "age_group": age_group,
        },
    )

    # Memory summaries
    user_summary = f"User asked: {user_message[:1000]}"
    assistant_summary = f"Assistant answered: {assistant_message[:1000]}"

    for kwargs in [
        {
            "kind": "user_request",
            "source_text": user_message,
            "summary_text": user_summary,
            "score": 0.5,
        },
        {
            "kind": "assistant_response",
            "source_text": assistant_message,
            "summary_text": assistant_summary,
            "score": 0.7,
        },
        {
            "kind": "reflection",
            "source_text": assistant_message,
            "summary_text": reflection_summary,
            "score": reflection_score,
        },
        {
            "kind": "strategy",
            "source_text": user_message,
            "summary_text": f"Recommended strategy: {strategy}",
            "score": 0.8,
        },
    ]:
        try:
            save_memory(
                conversation_id=conversation_id,
                user_id=user_id,
                **kwargs,
            )
        except Exception:
            pass

    return {
        "style": style,
        "reflection": reflection_summary,
        "reflection_score": reflection_score,
        "strategy": strategy,
        "age_group": age_group,
    }


class CreateConversationRequest(BaseModel):
    user_id: Optional[str] = None
    title: Optional[str] = None


class CreateConversationResponse(BaseModel):
    conversation_id: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str
    learning: Dict[str, Any]


class ConversationHistoryResponse(BaseModel):
    conversation_id: str
    messages: List[Dict[str, Any]]


class MemorySearchResponse(BaseModel):
    conversation_id: str
    memories: List[Dict[str, Any]]


app = FastAPI(title=f"{APP_NAME} API", version="3.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(system_router)


@app.on_event("startup")
def startup_event() -> None:
    init_db()


@app.get("/")
def root() -> Dict[str, Any]:
    return {
        "name": APP_NAME,
        "status": "ok",
        "provider": "ollama",
        "chat_model": OLLAMA_CHAT_MODEL,
        "embedding_model": OLLAMA_EMBED_MODEL,
        "web_search_enabled": ENABLE_WEB_SEARCH,
    }


@app.get("/vow")
def get_vow() -> Dict[str, str]:
    return {"name": APP_NAME, "vow": VOW_OF_THE_TURNING}


@app.post("/conversations", response_model=CreateConversationResponse)
def new_conversation(req: CreateConversationRequest) -> CreateConversationResponse:
    cid = create_conversation(user_id=req.user_id, title=req.title)
    return CreateConversationResponse(conversation_id=cid)


@app.get("/conversations/{conversation_id}", response_model=ConversationHistoryResponse)
def get_conversation(conversation_id: str) -> ConversationHistoryResponse:
    if not conversation_exists(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return ConversationHistoryResponse(conversation_id=conversation_id, messages=get_full_messages(conversation_id))


@app.get("/conversations/{conversation_id}/memories", response_model=MemorySearchResponse)
def get_conversation_memories(conversation_id: str, q: str) -> MemorySearchResponse:
    if not conversation_exists(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found.")
    meta = get_conversation_meta(conversation_id)
    memories = search_memories(query=q, conversation_id=conversation_id, user_id=meta.get("user_id") if meta else None)
    sanitized = [{"kind": m["kind"], "summary_text": m["summary_text"], "similarity": m["similarity"], "created_at": m["created_at"]} for m in memories]
    return MemorySearchResponse(conversation_id=conversation_id, memories=sanitized)


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    conversation_id = req.conversation_id
    if not conversation_id:
        conversation_id = create_conversation(user_id=req.user_id)
    elif not conversation_exists(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found.")
    add_message(conversation_id, "user", req.message)
    history = get_messages(conversation_id, limit=MAX_HISTORY_MESSAGES)
    meta = get_conversation_meta(conversation_id) or {}
    effective_user_id = req.user_id or meta.get("user_id")
    user_profile = get_user_profile(effective_user_id)
    user_profile = {**user_profile, "preferences": build_backend_awareness_preferences(user_profile, req.message)}
    memories = search_memories(query=req.message, conversation_id=conversation_id, user_id=effective_user_id)
    try:
        reply = generate_response_text(history=history[:-1], user_message=req.message, user_profile=user_profile, memories=memories)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if ENABLE_COGNITION_PIPELINE:
        try:
            cognition_output = process_completed_turn(
                user_message=req.message,
                assistant_response=reply,
                identity_profile=get_identity_profile(user_profile),
                persist=True,
            )
            curiosity = cognition_output.get("curiosity") if cognition_output else None
            reply = apply_curiosity_to_response(
                response=reply,
                curiosity_candidate=curiosity,
                enabled=ENABLE_CURIOSITY_SUGGESTIONS,
            )
        except Exception as exc:
            print("Cognition pipeline warning:", repr(exc))
            cognition_output = None

    add_message(conversation_id, "assistant", reply)
    learning = persist_learning(conversation_id=conversation_id, user_id=effective_user_id, user_message=req.message, assistant_message=reply)

    return ChatResponse(conversation_id=conversation_id, reply=reply, learning=learning)


@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
    conversation_id = req.conversation_id

    if not conversation_id:
        conversation_id = create_conversation(user_id=req.user_id)
    elif not conversation_exists(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found.")

    add_message(conversation_id, "user", req.message)

    meta = get_conversation_meta(conversation_id) or {}
    effective_user_id = req.user_id or meta.get("user_id")
    history = get_messages(conversation_id, limit=MAX_HISTORY_MESSAGES)
    user_profile = get_user_profile(effective_user_id)
    user_profile = {**user_profile, "preferences": build_backend_awareness_preferences(user_profile, req.message)}
    memories = search_memories(
        query=req.message,
        conversation_id=conversation_id,
        user_id=effective_user_id,
    )

    def event_generator():
        chunks: List[str] = []

        try:
            for event in stream_response_text(
                history=history[:-1],
                user_message=req.message,
                user_profile=user_profile,
                memories=memories,
            ):
                yield event

                if event.startswith("data: "):
                    payload = json.loads(event[len("data: "):].strip())
                    if payload.get("type") == "delta":
                        chunks.append(payload.get("text", ""))
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'error': str(exc)})}\n\n"
            yield f"data: {json.dumps({'type': 'end'})}\n\n"
            return

        full_text = "".join(chunks).strip()

        if full_text:
            if ENABLE_COGNITION_PIPELINE:
                try:
                    cognition_output = process_completed_turn(
                        user_message=req.message,
                        assistant_response=full_text,
                        identity_profile=get_identity_profile(user_profile),
                        persist=True,
                    )
                    curiosity = cognition_output.get("curiosity") if cognition_output else None
                    full_text = apply_curiosity_to_response(
                        response=full_text,
                        curiosity_candidate=curiosity,
                        enabled=ENABLE_CURIOSITY_SUGGESTIONS,
                    )
                except Exception as exc:
                    print("Cognition pipeline warning:", repr(exc))
                    cognition_output = None

            add_message(conversation_id, "assistant", full_text)

            learning = persist_learning(
                conversation_id=conversation_id,
                user_id=effective_user_id,
                user_message=req.message,
                assistant_message=full_text,
            )

            yield f"data: {json.dumps({'type': 'learning', 'data': learning})}\n\n"

            confidence = {
                "memory_available": len(memories) > 0,
                "memory_count": len(memories),
                "used_fallback": len(memories) == 0,
                "reflection_score": learning.get("reflection_score") if learning else None,
                "web_search_enabled": ENABLE_WEB_SEARCH,
                "web_search_used": should_enable_web_search(req.message),
            }

            yield f"data: {json.dumps({'type': 'confidence', 'data': confidence})}\n\n"

        yield f"data: {json.dumps({'type': 'end'})}\n\n"

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Conversation-Id": conversation_id,
    }

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=headers,
    )