"""OMEGA-ARC school day — the operator-set daily learning window (XII-B groundwork).

Runs the runtime's existing, review-gated study loop unattended between a start time and a
hard stop, then closes the day with one reflection cycle. Cadence and curriculum are set by
the operator (this script + the Windows task that fires it); the runtime chooses neither its
topics nor its schedule (ADR 0013, ADR 0025).

What it does, in order
  1. Preflight — Ollama and the backend must answer; with --start-stack it runs the
     port-guarded launcher (scripts/start-preview.ps1) and waits. A dead Ollama would
     otherwise produce silent "failed" cycles, so we refuse to study blind.
  2. Plan — from GET /system/tutelage/curriculum + /retention:
       a. NEW: the next unpassed lesson of each subject whose prerequisites are all passed,
          in curriculum order (Tier 1 → Tier 2 → Tier 3).
       b. DUE: passed lessons whose spaced re-quiz interval has elapsed (1, 3, 7, 14, 30 days
          by consecutive-pass streak) or whose latest attempt failed.
  3. Study — POST /system/tutelage/cycles per lesson while time remains. A new lesson that
     fails is retried once the same day (its sources are already ingested, so the retry is a
     pure re-quiz). 409 = prerequisite not met (skip); 422 = missing source (flag).
  4. Reflect — POST /system/reflection/cycles over today's window (operator-set cadence:
     end of each school day).
  5. Report — .runtime-logs/school/<date>.md (+ .json) with results and an operator to-do
     list. Anything gated stays gated: consolidation, adapter activation, approvals, and
     training are surfaced as to-dos, never performed here.

Usage
  python scripts/school_day.py                      # study until 14:00 local, then reflect
  python scripts/school_day.py --until 14:00 --start-stack
  python scripts/school_day.py --dry-run            # print the plan, touch nothing
  python scripts/school_day.py --max-cycles 1       # smoke test: one cycle + reflection
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_ROOT = REPO_ROOT / ".runtime-logs" / "school"
BACKEND = os.environ.get("OMEGA_BACKEND_URL", "http://127.0.0.1:8001")
OLLAMA = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434/api").rstrip("/")
if OLLAMA.endswith("/api"):
    OLLAMA = OLLAMA[:-4]

# Spaced re-quiz ladder: days to wait after N consecutive passes (capped at the last rung).
REQUIZ_LADDER_DAYS = [1, 3, 7, 14, 30]
# Comprehension can take minutes per lesson on the 12B voice; don't start a cycle we can't finish.
CYCLE_BUDGET_MIN = 12
REFLECTION_BUDGET_MIN = 6
# A lesson is never drilled more than this many times in one school day (spiral, not cram).
MAX_CYCLES_PER_LESSON_PER_DAY = 3


# ----------------------------------------------------------------------------- http helpers
def _get(path: str, timeout: int = 30) -> Any:
    with urllib.request.urlopen(f"{BACKEND}{path}", timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_state() -> tuple:
    """(curriculum, passed_lessons, retention_list, adapters) — the ONE place that knows the
    response envelopes, so the first plan and every re-plan read them identically."""
    cur = _get("/system/tutelage/curriculum")
    retention = _get("/system/tutelage/retention")
    if isinstance(retention, dict):
        retention = retention.get("retention", [])
    return cur["curriculum"], cur.get("passed_lessons", []), retention, _get("/system/tutelage/adapters")


def _post(path: str, body: Dict[str, Any], timeout: int) -> tuple[int, Any]:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(f"{BACKEND}{path}", data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8") or "null")
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8"))
        except Exception:
            detail = {"detail": str(exc)}
        return exc.code, detail


def _up(url: str, timeout: int = 4) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


# ----------------------------------------------------------------------------- preflight
def preflight(start_stack: bool, log) -> bool:
    ollama_ok = _up(f"{OLLAMA}/api/tags")
    backend_ok = _up(f"{BACKEND}/")
    log(f"preflight: ollama={'up' if ollama_ok else 'DOWN'} backend={'up' if backend_ok else 'DOWN'}")
    if ollama_ok and backend_ok:
        return True
    if not start_stack:
        log("stack is not up and --start-stack not given — refusing to study blind")
        return False
    launcher = REPO_ROOT / "scripts" / "start-preview.ps1"
    log(f"starting stack via {launcher.name} (port-guarded; only missing services start)")
    # No pipes: the launcher spawns detached children that would inherit them and hang us.
    launcher_log = LOG_ROOT / "launcher.log"
    with launcher_log.open("a", encoding="utf-8") as fh:
        proc = subprocess.Popen(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(launcher)],
                                cwd=str(REPO_ROOT), stdin=subprocess.DEVNULL, stdout=fh, stderr=subprocess.STDOUT)
    launch_deadline = time.time() + 240
    while proc.poll() is None and time.time() < launch_deadline:
        if _up(f"{OLLAMA}/api/tags") and _up(f"{BACKEND}/"):
            break
        time.sleep(3)
    if proc.poll() is None:
        log("launcher still running; continuing to wait for endpoints")
    deadline = time.time() + 120
    while time.time() < deadline:
        if _up(f"{OLLAMA}/api/tags") and _up(f"{BACKEND}/"):
            log("stack is up")
            return True
        time.sleep(3)
    log("stack did not come up — aborting the school day")
    return False


# ----------------------------------------------------------------------------- planning
def _parse_ts(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        ts = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _pass_streak(history: List[Dict[str, Any]]) -> int:
    streak = 0
    for entry in reversed(history):
        if entry.get("status") == "passed":
            streak += 1
        else:
            break
    return streak


def plan_day(curriculum: Dict[str, Any], passed: List[str], retention: List[Dict[str, Any]],
             now: datetime) -> Dict[str, List[Dict[str, Any]]]:
    """Pure planning — no I/O — so it can be unit-tested. Returns {'new': [...], 'due': [...]}."""
    passed_set = set(passed)
    by_lesson = {r["lesson_id"]: r for r in retention}
    new: List[Dict[str, Any]] = []
    due: List[Dict[str, Any]] = []
    for subject in curriculum.get("subjects", []):
        picked_new = False
        for lesson in subject.get("lessons", []):
            lid = lesson["id"]
            prereqs_ok = all(p in passed_set for p in lesson.get("prerequisites", []) or [])
            if lid not in passed_set:
                if prereqs_ok and not picked_new:
                    new.append({"subject_id": subject["id"], "lesson_id": lid, "title": lesson.get("title", lid),
                                "reason": "new lesson (prerequisites met)"})
                    picked_new = True  # one new lesson per subject per day: spiral, not cram
                continue
            history = (by_lesson.get(lid) or {}).get("history") or []
            if not history:
                continue
            last = history[-1]
            last_ts = _parse_ts(last.get("finished_at"))
            if last.get("status") != "passed":
                due.append({"subject_id": subject["id"], "lesson_id": lid, "title": lesson.get("title", lid),
                            "reason": "latest attempt failed — re-quiz"})
                continue
            streak = _pass_streak(history)
            interval = REQUIZ_LADDER_DAYS[min(streak, len(REQUIZ_LADDER_DAYS)) - 1]
            if last_ts is None or (now - last_ts) >= timedelta(days=interval):
                age = (now - last_ts).days if last_ts else None
                due.append({"subject_id": subject["id"], "lesson_id": lid, "title": lesson.get("title", lid),
                            "reason": f"spaced re-quiz (streak {streak}, interval {interval}d, age {age}d)"})
    return {"new": new, "due": due}


def fill_round(curriculum: Dict[str, Any], passed: List[str], retention: List[Dict[str, Any]],
               today_counts: Dict[str, int]) -> List[Dict[str, Any]]:
    """When nothing is new or due: reinforce. Passed lessons ordered weakest-first (lowest latest
    comprehension, then oldest), skipping any lesson already at its daily cap. Pure — testable."""
    by_lesson = {r["lesson_id"]: r for r in retention}
    passed_set = set(passed)
    candidates = []
    for subject in curriculum.get("subjects", []):
        for lesson in subject.get("lessons", []):
            lid = lesson["id"]
            if lid not in passed_set or today_counts.get(lid, 0) >= MAX_CYCLES_PER_LESSON_PER_DAY:
                continue
            history = (by_lesson.get(lid) or {}).get("history") or []
            last = history[-1] if history else {}
            comp = last.get("comprehension")
            comp = 1.0 if comp is None else comp
            candidates.append((comp, last.get("finished_at") or "", lid, lesson.get("title", lid), subject["id"]))
    candidates.sort()
    return [{"subject_id": s, "lesson_id": lid, "title": t,
             "reason": f"reinforcement (latest comprehension {c})"} for c, _, lid, t, s in candidates]


def operator_todos(curriculum: Dict[str, Any], passed: List[str], adapters: Dict[str, Any]) -> List[str]:
    """Gated actions the runner must not take — surfaced for the operator instead."""
    todos: List[str] = []
    passed_set = set(passed)
    active_subjects = {a.get("subject_id") for a in adapters.get("adapters", [])
                       if a.get("status") == "active"}
    for subject in curriculum.get("subjects", []):
        lessons = subject.get("lessons", [])
        if lessons and all(l["id"] in passed_set for l in lessons) and subject["id"] not in active_subjects:
            todos.append(f"{subject['id']}: every lesson passed and no active adapter — consolidation is "
                         f"available (needs a single-use operator approval; training stays operator-run).")
    return todos


# ----------------------------------------------------------------------------- study loop
def run_cycle(lesson_id: str, study_model: Optional[str], log) -> Dict[str, Any]:
    started = time.time()
    body: Dict[str, Any] = {"lesson_id": lesson_id, "comprehension": True}
    if study_model:
        body["study_model"] = study_model
    status, payload = _post("/system/tutelage/cycles", body, timeout=60 * 30)
    elapsed = round(time.time() - started)
    if status != 200 or not isinstance(payload, dict):
        detail = payload.get("detail") if isinstance(payload, dict) else payload
        outcome = {"lesson_id": lesson_id, "http": status, "detail": detail, "seconds": elapsed}
        log(f"  {lesson_id}: HTTP {status} — {detail} ({elapsed}s)")
        return outcome
    cycle = payload.get("cycle") or payload
    recall = ((cycle.get("recall_post") or {}).get("score"))
    comp = ((cycle.get("comprehension") or {}).get("score"))
    outcome = {"lesson_id": lesson_id, "http": 200, "status": cycle.get("status"), "recall": recall,
               "comprehension": comp, "chunks_written": cycle.get("chunks_written"),
               "cycle_id": cycle.get("id") or cycle.get("cycle_id"), "seconds": elapsed}
    log(f"  {lesson_id}: {cycle.get('status')} recall={recall} comprehension={comp} "
        f"chunks={cycle.get('chunks_written')} ({elapsed}s)")
    return outcome


def main() -> int:
    parser = argparse.ArgumentParser(description="OMEGA-ARC school day runner")
    parser.add_argument("--until", default="14:00", help="hard stop, local HH:MM (default 14:00)")
    parser.add_argument("--start-stack", action="store_true", help="start Ollama/backend if they are down")
    parser.add_argument("--dry-run", action="store_true", help="plan only; no cycles, no reflection")
    parser.add_argument("--max-cycles", type=int, default=None, help="cap study cycles (smoke tests)")
    parser.add_argument("--no-reflection", action="store_true", help="skip the end-of-day reflection cycle")
    parser.add_argument("--study-model", default=None, help="override the study seat model for today")
    args = parser.parse_args()

    now = datetime.now().astimezone()
    hh, mm = (int(x) for x in args.until.split(":"))
    deadline = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if deadline <= now:
        deadline = deadline + timedelta(days=1) if (deadline + timedelta(days=1) - now) < timedelta(hours=6) else deadline
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    day = now.strftime("%Y-%m-%d")
    log_path = LOG_ROOT / f"{day}.log"
    lines: List[str] = []

    def log(msg: str) -> None:
        stamp = datetime.now().astimezone().strftime("%H:%M:%S")
        line = f"[{stamp}] {msg}"
        print(line, flush=True)
        lines.append(line)
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    log(f"school day {day}: window until {deadline.strftime('%H:%M')} "
        f"({'DRY RUN' if args.dry_run else 'live'})")

    if not args.dry_run and not preflight(args.start_stack, log):
        _write_report(day, now, deadline, {"new": [], "due": []}, [], None, ["preflight failed"], lines)
        return 2
    if args.dry_run and not (_up(f"{BACKEND}/")):
        log("dry run: backend is down — planning from backend/data files directly")
        sys.path.insert(0, str(REPO_ROOT / "backend"))
        from services import tutelage as _t  # type: ignore  (merges the private overlay)
        curriculum = _t.load_curriculum(_t.DEFAULT_CURRICULUM_PATH)
        cycles_store = _t.load_study_cycles(_t.DEFAULT_STUDY_CYCLES_PATH)
        retention = _t.retention_report(cycles_store)
        passed = sorted({c["lesson_id"] for c in cycles_store.get("cycles", []) if c.get("status") == "passed"})
        adapters = json.loads((REPO_ROOT / "backend/data/adapters.json").read_text(encoding="utf-8"))
    else:
        curriculum, passed, retention, adapters = fetch_state()

    plan = plan_day(curriculum, passed, retention, datetime.now(timezone.utc))
    log(f"plan: {len(plan['new'])} new, {len(plan['due'])} due")
    for item in plan["new"] + plan["due"]:
        log(f"  - {item['lesson_id']}  [{item['reason']}]")
    todos = operator_todos(curriculum, passed, adapters)

    results: List[Dict[str, Any]] = []
    reflection: Optional[Dict[str, Any]] = None
    if not args.dry_run:
        # School runs in ROUNDS until the window closes: each round re-reads the curriculum and
        # retention (so lessons unlocked by a pass this morning — or subjects the operator adds
        # mid-day — are picked up), studies what is new/due, and when nothing is new or due it
        # re-quizzes the weakest lessons. Every lesson is capped at MAX_CYCLES_PER_LESSON_PER_DAY.
        # "If the tests pass, keep it studying until 14:00" — the operator's instruction.
        today_counts: Dict[str, int] = {}
        retried: set[str] = set()
        round_no = 0
        while True:
            remaining = deadline - datetime.now().astimezone()
            if remaining < timedelta(minutes=CYCLE_BUDGET_MIN + REFLECTION_BUDGET_MIN):
                log(f"stopping study: {int(remaining.total_seconds() // 60)} min left before {args.until}")
                break
            if args.max_cycles is not None and len(results) >= args.max_cycles:
                log(f"stopping study: --max-cycles {args.max_cycles} reached")
                break
            round_no += 1
            if round_no > 1:
                curriculum, passed, retention, _ = fetch_state()
                plan = plan_day(curriculum, passed, retention, datetime.now(timezone.utc))
            queue = [i for i in plan["new"] + plan["due"]
                     if today_counts.get(i["lesson_id"], 0) < MAX_CYCLES_PER_LESSON_PER_DAY]
            if not queue:
                queue = fill_round(curriculum, passed, retention, today_counts)
                if not queue:
                    log(f"round {round_no}: nothing left to study today (every lesson at its daily cap)")
                    break
                log(f"round {round_no}: nothing new or due — reinforcing {len(queue)} weakest lesson(s)")
            else:
                log(f"round {round_no}: {len(queue)} lesson(s) queued")
            for item in queue:
                remaining = deadline - datetime.now().astimezone()
                if remaining < timedelta(minutes=CYCLE_BUDGET_MIN + REFLECTION_BUDGET_MIN):
                    break
                if args.max_cycles is not None and len(results) >= args.max_cycles:
                    break
                log(f"cycle: {item['lesson_id']} ({item['reason']})")
                outcome = run_cycle(item["lesson_id"], args.study_model, log)
                outcome["reason"] = item["reason"]
                results.append(outcome)
                today_counts[item["lesson_id"]] = today_counts.get(item["lesson_id"], 0) + 1
                if outcome.get("http") == 200 and outcome.get("status") != "passed" \
                        and item["lesson_id"] not in retried \
                        and today_counts[item["lesson_id"]] < MAX_CYCLES_PER_LESSON_PER_DAY:
                    retried.add(item["lesson_id"])
                    log(f"cycle: {item['lesson_id']} (retry after failed attempt)")
                    outcome = run_cycle(item["lesson_id"], args.study_model, log)
                    outcome["reason"] = "retry after failed attempt"
                    results.append(outcome)
                    today_counts[item["lesson_id"]] += 1
                elif outcome.get("http") == 422:
                    todos.append(f"{item['lesson_id']}: source file missing (HTTP 422) — fix the curriculum.")
                elif outcome.get("http") not in (200, 409):
                    todos.append(f"{item['lesson_id']}: HTTP {outcome.get('http')} — {outcome.get('detail')}")
        if not args.no_reflection:
            window_since = now.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
            log("reflection: composing today's self-observation")
            status, payload = _post("/system/reflection/cycles",
                                    {"window_since": window_since.isoformat()}, timeout=60 * 15)
            if status == 200 and isinstance(payload, dict):
                cyc = payload.get("cycle") or payload
                obs = (cyc.get("observation") or cyc.get("observation_text") or "")
                reflection = {"http": 200, "cycle_id": cyc.get("id") or cyc.get("cycle_id"),
                              "observation_preview": str(obs)[:400]}
                log(f"  reflection recorded ({len(str(obs))} chars)")
            else:
                reflection = {"http": status, "detail": payload}
                log(f"  reflection failed: HTTP {status} {payload}")

    _write_report(day, now, deadline, plan, results, reflection, todos, lines)
    passed_n = sum(1 for r in results if r.get("status") == "passed")
    log(f"done: {len(results)} cycles, {passed_n} passed, reflection={'ok' if reflection and reflection.get('http') == 200 else 'skipped/failed'}")
    return 0


def _write_report(day: str, started: datetime, deadline: datetime, plan: Dict[str, Any],
                  results: List[Dict[str, Any]], reflection: Optional[Dict[str, Any]],
                  todos: List[str], lines: List[str]) -> None:
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    (LOG_ROOT / f"{day}.json").write_text(json.dumps({
        "day": day, "started": started.isoformat(), "deadline": deadline.isoformat(),
        "plan": plan, "results": results, "reflection": reflection, "operator_todos": todos,
    }, indent=1), encoding="utf-8")
    md = [f"# School day {day}", "",
          f"Window: {started.strftime('%H:%M')} → {deadline.strftime('%H:%M')} local", "",
          "## Plan", ""]
    for item in plan.get("new", []) + plan.get("due", []):
        md.append(f"- `{item['lesson_id']}` — {item['reason']}")
    md += ["", "## Results", ""]
    if not results:
        md.append("_no cycles run_")
    for r in results:
        if r.get("http") == 200:
            md.append(f"- `{r['lesson_id']}` — **{r.get('status')}** recall {r.get('recall')} · "
                      f"comprehension {r.get('comprehension')} · chunks {r.get('chunks_written')} · {r.get('seconds')}s")
        else:
            md.append(f"- `{r['lesson_id']}` — HTTP {r.get('http')}: {r.get('detail')}")
    md += ["", "## Reflection", ""]
    if reflection and reflection.get("http") == 200:
        md.append(f"Recorded (cycle `{reflection.get('cycle_id')}`):")
        md.append("")
        md.append("> " + str(reflection.get("observation_preview", "")).replace("\n", "\n> "))
    else:
        md.append(f"_not recorded_ {reflection or ''}")
    md += ["", "## Operator to-do (gated — not done by the runner)", ""]
    md += [f"- {t}" for t in todos] or ["_nothing pending_"]
    md += ["", "## Log", "", "```", *lines, "```", ""]
    (LOG_ROOT / f"{day}.md").write_text("\n".join(md), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
