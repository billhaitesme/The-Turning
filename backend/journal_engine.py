from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
JOURNAL = DATA / "journal"
REPORTS = DATA / "dream_reports"
PROPOSALS = DATA / "proposals"

for folder in (JOURNAL, REPORTS, PROPOSALS):
    folder.mkdir(parents=True, exist_ok=True)

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def write_journal_entry(title, summary, observations, lessons, unresolved_questions, source_conversation_ids=None):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    path = JOURNAL / f"journal_{stamp}.json"
    payload = {
        "created_at": utc_now(),
        "title": str(title)[:200],
        "summary": str(summary)[:4000],
        "observations": [str(x)[:1000] for x in observations][:20],
        "lessons": [str(x)[:1000] for x in lessons][:20],
        "unresolved_questions": [str(x)[:1000] for x in unresolved_questions][:20],
        "source_conversation_ids": source_conversation_ids or [],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path

def load_recent_journal(limit=10):
    result = []
    for path in sorted(JOURNAL.glob("journal_*.json"), reverse=True)[:limit]:
        try:
            result.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            pass
    return result

def write_dream_report(report):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    path = REPORTS / f"dream_report_{stamp}.json"
    report = dict(report)
    report.setdefault("created_at", utc_now())
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return path

def write_proposal(kind, payload):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    path = PROPOSALS / f"{kind}_{stamp}.json"
    record = {"created_at": utc_now(), "kind": kind, "status": "pending", "payload": payload}
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    return path