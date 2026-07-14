from __future__ import annotations
import json
from journal_engine import load_recent_journal, write_dream_report, write_proposal
from personality_engine import load_personality

DREAM_PROMPT = """Perform an offline reflection cycle.

Return JSON only:
{
  "summary": "...",
  "successful_patterns": [],
  "failed_patterns": [],
  "memory_consolidation_notes": [],
  "personality_update_proposal": null,
  "curriculum_topics": [],
  "system_improvement_proposals": [],
  "morning_message": "..."
}

Do not claim consciousness.
Do not alter files directly.
Personality and system changes are proposals only.
Prefer specific evidence over vague impressions."""

def run_dream_cycle(model_call, conversation_summaries, awareness):
    context = {
        "conversation_summaries": conversation_summaries[-50:],
        "recent_journal": load_recent_journal(10),
        "personality": load_personality(),
        "awareness": awareness,
    }
    raw = model_call(DREAM_PROMPT + "\n\nContext:\n" + json.dumps(context, indent=2, ensure_ascii=False))
    result = json.loads(raw)
    result["report_path"] = str(write_dream_report(result))

    proposal = result.get("personality_update_proposal")
    if isinstance(proposal, dict):
        write_proposal("personality", proposal)

    for proposal in result.get("system_improvement_proposals", []):
        if isinstance(proposal, dict):
            write_proposal("system", proposal)

    return result