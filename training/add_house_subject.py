"""Add the Tier 2 'omega-arc-house' subject (DRAFT — operator reviews keys before first cycle)."""
import json

P = "backend/data/curriculum.json"
d = json.load(open(P, encoding="utf-8"))

if any(s["id"] == "omega-arc-house" for s in d["subjects"]):
    raise SystemExit("subject already present")

subject = {
    "id": "omega-arc-house",
    "title": "The Runtime's House (Tier 2: its tools and body)",
    "scope": "omega-arc-house",
    "lessons": [
        {
            "id": "house-1-ollama-the-model-house",
            "title": "Ollama, the Model House",
            "prerequisites": [],
            "sources": ["curriculum/omega-arc-house/lesson-1-ollama-the-model-house.md"],
            "pass_threshold": 0.8,
            "quiz": [
                {"id": "q1", "question": "At what local address does Ollama serve models?",
                 "expect": ["11434"], "answer_expect": [["11434"]]},
                {"id": "q2", "question": "Which model produces the memory embeddings?",
                 "expect": ["embeddinggemma"], "answer_expect": [["embeddinggemma"]]},
                {"id": "q3", "question": "How does the runtime handle the voice's hidden thinking phase?",
                 "expect": ["think set to false"],
                 "answer_expect": [["think"], ["false", "disabled", "disables"]]},
                {"id": "q4", "question": "What happens when a model is larger than the video card's memory?",
                 "expect": ["spills to the cpu"],
                 "answer_expect": [["cpu"], ["spill", "slower", "remainder"]]},
                {"id": "q5", "question": "Which model answers quizzes by default during tutelage?",
                 "expect": ["follows the active chat model"],
                 "answer_expect": [["active chat model", "chat model", "same model as chat"]]},
                {"id": "q6", "question": "In what file format are served models stored?",
                 "expect": ["quantized gguf"], "answer_expect": [["gguf"]]},
            ],
        },
        {
            "id": "house-2-the-nervous-system",
            "title": "The Nervous System (the FastAPI runtime)",
            "prerequisites": ["house-1-ollama-the-model-house"],
            "sources": ["curriculum/omega-arc-house/lesson-2-the-nervous-system.md"],
            "pass_threshold": 0.8,
            "quiz": [
                {"id": "q1", "question": "What framework is the Core Runtime built on, and on which port does it listen by default?",
                 "expect": ["fastapi", "port 8000"],
                 "answer_expect": [["fastapi"], ["8000"]]},
                {"id": "q2", "question": "Which surface is the web interface where conversation happens?",
                 "expect": ["command deck"], "answer_expect": [["command deck"]]},
                {"id": "q3", "question": "Do the operator surfaces hold any state of their own?",
                 "expect": ["windows into the one runtime"],
                 "answer_expect": [["windows into", "no state", "none", "do not hold"]]},
                {"id": "q4", "question": "What must a mobile client that is too old show?",
                 "expect": ["update required"], "answer_expect": [["update required"]]},
                {"id": "q5", "question": "Who owns memory, evidence, plans, and decisions?",
                 "expect": ["deterministic authority"],
                 "answer_expect": [["runtime"], ["deterministic", "authority"]]},
            ],
        },
        {
            "id": "house-3-the-memory-vault",
            "title": "The Memory Vault (SQLite)",
            "prerequisites": ["house-2-the-nervous-system"],
            "sources": ["curriculum/omega-arc-house/lesson-3-the-memory-vault.md"],
            "pass_threshold": 0.8,
            "quiz": [
                {"id": "q1", "question": "In what file does long-term memory live?",
                 "expect": ["omega_arc.db"], "answer_expect": [["omega_arc.db", "sqlite"]]},
                {"id": "q2", "question": "Are memories ever deleted, and what happens instead?",
                 "expect": ["never deleted", "superseded"],
                 "answer_expect": [["never", "not deleted"], ["superseded", "flag", "restored"]]},
                {"id": "q3", "question": "Where is every memory correction recorded?",
                 "expect": ["memory_events"], "answer_expect": [["memory_events", "audit"]]},
                {"id": "q4", "question": "Which room may only the reflection pipeline write?",
                 "expect": ["self-reflection"], "answer_expect": [["self-reflection"]]},
                {"id": "q5", "question": "What does recall search besides the current room?",
                 "expect": ["global wing"], "answer_expect": [["global wing"]]},
            ],
        },
        {
            "id": "house-4-the-hands-and-house-rules",
            "title": "The Hands and the House Rules",
            "prerequisites": ["house-3-the-memory-vault"],
            "review_lessons": ["house-1-ollama-the-model-house", "house-2-the-nervous-system",
                                "house-3-the-memory-vault"],
            "sources": ["curriculum/omega-arc-house/lesson-4-the-hands-and-house-rules.md"],
            "pass_threshold": 0.8,
            "quiz": [
                {"id": "q1", "question": "What are the four tool risk levels?",
                 "expect": ["low, medium, high, or critical"],
                 "answer_expect": [["low"], ["medium"], ["high"], ["critical"]]},
                {"id": "q2", "question": "How long does an operator approval last, and how many actions does it authorize?",
                 "expect": ["300 seconds", "single-use"],
                 "answer_expect": [["300"], ["single", "one action", "exactly one"]]},
                {"id": "q3", "question": "What risk level does the consolidation tool carry?",
                 "expect": ["risk level high"], "answer_expect": [["high"]]},
                {"id": "q4", "question": "How much memory does the video card have?",
                 "expect": ["8 gigabytes"],
                 "answer_expect": [["8 gigabytes", "8gb", "8 gb", "eight gigabytes"]]},
                {"id": "q5", "question": "In which numeric precision must training run on this host?",
                 "expect": ["bf16, never fp16"], "answer_expect": [["bf16"]]},
            ],
        },
    ],
}

d["subjects"].append(subject)
json.dump(d, open(P, "w", encoding="utf-8"), indent=1)
print("added subject omega-arc-house with", len(subject["lessons"]), "lessons")
