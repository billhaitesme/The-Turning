"""Add (or refresh) a curriculum subject from curriculum/<subject>/subject.json.

Operator-authored keys are checked against the lesson text BEFORE anything is written:
every recall `expect` phrase must be a literal substring of one paragraph-chunk of the
lesson's sources (that is exactly how grade_recall matches), and every lesson's
prerequisites / review_lessons / sources must resolve. A subject that fails validation
is not added — bad keys would produce quizzes nothing can pass.

Usage (from the repo root):
    python scripts/curriculum_add.py curriculum/<subject-dir>            # add new subject
    python scripts/curriculum_add.py curriculum/<subject-dir> --replace  # refresh keys/lessons
    python scripts/curriculum_add.py --validate curriculum/<subject-dir> # check only
    python scripts/curriculum_add.py --remove <subject-id>              # take a subject out

Private subjects (the operator's world — never in the public repo): put them under
curriculum-private/<subject-dir>/ and/or set "private": true in subject.json; they are written
to backend/data/curriculum.private.json (both paths are gitignored) and merged at load time.

The previous store is backed up alongside as <name>.bak-<timestamp>.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CURRICULUM_PATH = REPO_ROOT / "backend" / "data" / "curriculum.json"
PRIVATE_CURRICULUM_PATH = REPO_ROOT / "backend" / "data" / "curriculum.private.json"
sys.path.insert(0, str(REPO_ROOT / "backend"))
from services.tutelage import chunk_text  # noqa: E402  (same chunker the runtime ingests with)


def validate_subject(subject: dict, known_lesson_ids: set[str]) -> list[str]:
    problems: list[str] = []
    for key in ("id", "title", "scope", "lessons"):
        if key not in subject:
            problems.append(f"subject missing '{key}'")
    if problems:
        return problems
    seen: set[str] = set(known_lesson_ids)
    local: set[str] = set()
    for lesson in subject["lessons"]:
        lid = lesson.get("id", "<no id>")
        local.add(lid)
        for dep_key in ("prerequisites", "review_lessons"):
            for dep in lesson.get(dep_key, []) or []:
                if dep not in seen and dep not in local:
                    problems.append(f"{lid}: {dep_key} '{dep}' is not a known lesson (order matters)")
        chunks: list[str] = []
        for source in lesson.get("sources", []) or []:
            path = REPO_ROOT / source
            if not path.exists():
                problems.append(f"{lid}: source not found: {source}")
                continue
            chunks.extend(c.lower() for c in chunk_text(path.read_text(encoding="utf-8")))
        if not lesson.get("quiz"):
            problems.append(f"{lid}: no quiz")
        for item in lesson.get("quiz", []) or []:
            qid = item.get("id", "?")
            expect = [str(t) for t in item.get("expect", []) if str(t).strip()]
            if not expect:
                problems.append(f"{lid}/{qid}: empty expect")
                continue
            if chunks and not any(all(t.lower() in c for t in expect) for c in chunks):
                problems.append(f"{lid}/{qid}: recall expect {expect} is not a substring of any single "
                                f"paragraph-chunk of the sources (recall could never hit)")
            for group in item.get("answer_expect", []) or []:
                if isinstance(group, list) and not group:
                    problems.append(f"{lid}/{qid}: empty OR-group in answer_expect")
        seen.add(lid)
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("subject_dir", nargs="?", help="curriculum[-private]/<subject-dir> containing subject.json")
    parser.add_argument("--replace", action="store_true", help="replace an existing subject with the same id")
    parser.add_argument("--validate", action="store_true", help="validate only, write nothing")
    parser.add_argument("--private", action="store_true", help="write to the private overlay (curriculum.private.json)")
    parser.add_argument("--remove", metavar="SUBJECT_ID", help="remove a subject from whichever store holds it")
    args = parser.parse_args()

    if args.remove:
        return _remove(args.remove)
    if not args.subject_dir:
        parser.error("subject_dir is required unless --remove is given")
    subject_path = REPO_ROOT / args.subject_dir / "subject.json"
    if not subject_path.exists():
        print(f"no subject.json at {subject_path}")
        return 2
    subject = json.loads(subject_path.read_text(encoding="utf-8"))
    private = bool(args.private or subject.get("private") or "curriculum-private" in Path(args.subject_dir).parts)
    store_path = PRIVATE_CURRICULUM_PATH if private else CURRICULUM_PATH
    if private:
        subject["private"] = True
        public = _load(CURRICULUM_PATH)
        if any(s["id"] == subject["id"] for s in public["subjects"]):
            print(f"{subject['id']} exists in the PUBLIC curriculum — remove it there first (--remove)")
            return 1
    curriculum = _load(store_path)
    # prerequisites may reference lessons in either store
    other_store = _load(CURRICULUM_PATH if private else PRIVATE_CURRICULUM_PATH)
    others = [s for s in curriculum["subjects"] if s["id"] != subject["id"]]
    known = {les["id"] for s in others + other_store["subjects"] for les in s["lessons"]}

    problems = validate_subject(subject, known)
    if problems:
        print(f"REJECTED {subject['id']} — {len(problems)} problem(s):")
        for p in problems:
            print("  -", p)
        return 1
    print(f"validated {subject['id']}: {len(subject['lessons'])} lessons, "
          f"{sum(len(l['quiz']) for l in subject['lessons'])} quiz items — all keys resolve"
          f"{' [PRIVATE]' if private else ''}")
    if args.validate:
        return 0

    exists = len(others) != len(curriculum["subjects"])
    if exists and not args.replace:
        print(f"subject {subject['id']} already present (use --replace to refresh)")
        return 1
    backup = _backup(store_path)
    curriculum["subjects"] = others + [subject] if not exists else [
        subject if s["id"] == subject["id"] else s for s in curriculum["subjects"]]
    _save(store_path, curriculum)
    print(f"{'replaced' if exists else 'added'} subject {subject['id']} in {store_path.name}"
          f"{f' (backup: {backup.name})' if backup else ''}")
    return 0


def _load(path: Path) -> dict:
    if not path.exists():
        return {"version": 1, "subjects": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def _backup(path: Path):
    if not path.exists():
        return None
    backup = path.with_name(f"{path.name}.bak-{datetime.now():%Y%m%dT%H%M%S}")
    shutil.copy2(path, backup)
    return backup


def _remove(subject_id: str) -> int:
    for store_path in (CURRICULUM_PATH, PRIVATE_CURRICULUM_PATH):
        data = _load(store_path)
        keep = [s for s in data["subjects"] if s["id"] != subject_id]
        if len(keep) != len(data["subjects"]):
            _backup(store_path)
            data["subjects"] = keep
            _save(store_path, data)
            print(f"removed {subject_id} from {store_path.name}")
            return 0
    print(f"{subject_id} not found in either store")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
