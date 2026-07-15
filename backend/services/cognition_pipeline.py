from __future__ import annotations

from typing import Any, Dict

from services.cognition_engine import analyze_message
from services.curiosity_engine import choose_curiosity_question
from services.goal_engine import apply_goal_candidates, load_goal_store, save_goal_store
from services.knowledge_graph import apply_knowledge_candidates, load_graph, save_graph
from services.reflection_engine import reflect_on_turn


def process_completed_turn(
    *,
    user_message: str,
    assistant_response: str,
    identity_profile: Dict[str, Any] | None = None,
    persist: bool = True,
) -> Dict[str, Any]:
    cognition = analyze_message(message=user_message, assistant_response=assistant_response)

    reflection = reflect_on_turn(
        user_message=user_message,
        assistant_response=assistant_response,
        cognition_result=cognition,
    )

    goal_store = load_goal_store()
    updated_goals = apply_goal_candidates(goal_store, cognition.get("goal_candidates", []))

    graph = load_graph()
    updated_graph = apply_knowledge_candidates(graph, cognition.get("knowledge_candidates", []))

    curiosity = choose_curiosity_question(
        user_message=user_message,
        cognition_result=cognition,
        identity_profile=identity_profile,
    )

    if persist:
        save_goal_store(updated_goals)
        save_graph(updated_graph)

    return {
        "cognition": cognition,
        "reflection": reflection,
        "goals": updated_goals,
        "knowledge_graph": updated_graph,
        "curiosity": curiosity,
    }
