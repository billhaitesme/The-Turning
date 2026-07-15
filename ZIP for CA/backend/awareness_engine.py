from __future__ import annotations
import json, shutil, subprocess, urllib.request
from dataclasses import dataclass, asdict
from pathlib import Path

BASE = Path(__file__).resolve().parent
CONSTITUTION = BASE / "data" / "constitution.json"

@dataclass
class AwarenessSnapshot:
    ollama_online: bool
    backend_online: bool
    frontend_online: bool
    network_mode: str
    active_model: str
    vision_model: str
    embedding_model: str
    router_model: str
    gpu_name: str
    tools: dict

def http_ok(url, timeout=1.5):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return 200 <= response.status < 400
    except Exception:
        return False

def gpu_name():
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().splitlines()[0]
    except Exception:
        pass
    return "UNKNOWN"

def build_awareness_snapshot(
    backend_url="http://127.0.0.1:8000/",
    frontend_url="http://localhost:5173/",
    ollama_url="http://127.0.0.1:11434/api/tags",
    network_mode="offline",
    active_model="llama2-uncensored:7b",
    vision_model="llava:7b",
    embedding_model="embeddinggemma:latest",
    router_model="gemma3:1b",
):
    return AwarenessSnapshot(
        ollama_online=http_ok(ollama_url),
        backend_online=http_ok(backend_url),
        frontend_online=http_ok(frontend_url),
        network_mode=network_mode,
        active_model=active_model,
        vision_model=vision_model,
        embedding_model=embedding_model,
        router_model=router_model,
        gpu_name=gpu_name(),
        tools={
            "ollama_cli": bool(shutil.which("ollama.exe") or shutil.which("ollama")),
            "npm": bool(shutil.which("npm.cmd") or shutil.which("npm")),
            "python": bool(shutil.which("python.exe") or shutil.which("python")),
            "vision": True,
            "memory": True,
            "web_search": network_mode != "offline",
            "documents": False,
        },
    )

def awareness_prompt(snapshot):
    data = asdict(snapshot)
    tools = "\n".join(f"- {k}: {v}" for k, v in data["tools"].items())
    return f"""Operational awareness:
- Ollama online: {data['ollama_online']}
- Backend online: {data['backend_online']}
- Frontend online: {data['frontend_online']}
- Network mode: {data['network_mode']}
- Active model: {data['active_model']}
- Vision model: {data['vision_model']}
- Embedding model: {data['embedding_model']}
- Router model: {data['router_model']}
- GPU: {data['gpu_name']}

Available tools:
{tools}

Do not invent capabilities that are unavailable."""

def constitution_prompt():
    data = json.loads(CONSTITUTION.read_text(encoding="utf-8"))
    principles = "\n".join(f"- {x}" for x in data["principles"])
    return f"Constitution:\n{principles}\n\nThe Constitution is stable and not rewritten by ordinary reflection."