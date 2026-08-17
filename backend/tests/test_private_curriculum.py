"""Private curriculum overlay: operator's-world subjects that never enter the public repo.

Private subjects live in curriculum.private.json (gitignored) and are merged at load time;
their study cycles go to study_cycles.private.json (gitignored) and are merged at read time;
the reflection digest (stored in the repo) sees them only as opaque labels; consolidation
(which writes repo-tracked artifacts) refuses them."""
import json
import sqlite3

import pytest

import app
from benchmarks.recall_benchmark import stub_embedding
from services import tutelage

LESSON_TEXT = """# Private Lesson

The secret handshake of the guild is three taps on the lintel.

The guild meets on the second moon in the cellar of the old mill.
"""

PUBLIC = {"version": 1, "subjects": [{
    "id": "public-subject", "title": "Public", "scope": "public-subject",
    "lessons": [{"id": "pub-1", "title": "Pub 1", "prerequisites": [], "sources": [],
                 "pass_threshold": 0.5,
                 "quiz": [{"id": "q1", "question": "Where does the guild meet?", "expect": ["old mill"]}]}]}]}

PRIVATE = {"version": 1, "subjects": [{
    "id": "hush-subject", "title": "Hush", "scope": "hush-subject",
    "lessons": [{"id": "hush-1", "title": "Hush 1", "prerequisites": [], "sources": [],
                 "pass_threshold": 0.5,
                 "quiz": [{"id": "q1", "question": "What is the secret handshake?", "expect": ["three taps"]}]},
                {"id": "hush-2", "title": "Hush 2", "prerequisites": ["hush-1"], "sources": [],
                 "pass_threshold": 0.5,
                 "quiz": [{"id": "q1", "question": "Where does the guild meet?", "expect": ["old mill"]}]}]}]}


def _setup(monkeypatch, tmp_path):
    database = tmp_path / "t.db"

    def fake_get_db():
        conn = sqlite3.connect(database)
        conn.row_factory = sqlite3.Row
        return conn

    monkeypatch.setattr(app, "get_db", fake_get_db)
    monkeypatch.setattr(app, "get_embedding", stub_embedding)
    monkeypatch.setattr(app, "MEMORY_SUPERSEDE_THRESHOLD", 0.0)
    monkeypatch.setattr(app, "study_answer", lambda model, question, notes: " ".join(notes))
    app.init_db()

    source = tmp_path / "lesson.md"
    source.write_text(LESSON_TEXT, encoding="utf-8")
    public = json.loads(json.dumps(PUBLIC))
    private = json.loads(json.dumps(PRIVATE))
    for store in (public, private):
        for subject in store["subjects"]:
            for lesson in subject["lessons"]:
                lesson["sources"] = [str(source)]
    pub_path, priv_path = tmp_path / "curriculum.json", tmp_path / "curriculum.private.json"
    pub_path.write_text(json.dumps(public), encoding="utf-8")
    priv_path.write_text(json.dumps(private), encoding="utf-8")
    cyc_path, priv_cyc_path = tmp_path / "study_cycles.json", tmp_path / "study_cycles.private.json"
    monkeypatch.setattr(tutelage, "DEFAULT_CURRICULUM_PATH", pub_path)
    monkeypatch.setattr(tutelage, "DEFAULT_PRIVATE_CURRICULUM_PATH", priv_path)
    monkeypatch.setattr(tutelage, "DEFAULT_STUDY_CYCLES_PATH", cyc_path)
    monkeypatch.setattr(tutelage, "DEFAULT_PRIVATE_STUDY_CYCLES_PATH", priv_cyc_path)
    return cyc_path, priv_cyc_path


def test_private_subjects_merge_at_load_and_are_tagged(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    cur = tutelage.load_curriculum(tutelage.DEFAULT_CURRICULUM_PATH)
    ids = {s["id"]: s for s in cur["subjects"]}
    assert set(ids) == {"public-subject", "hush-subject"}
    assert ids["hush-subject"]["private"] is True
    assert "private" not in ids["public-subject"]
    # a non-default path is read raw — no merge (hermetic for callers that point elsewhere)
    copy = tmp_path / "elsewhere.json"
    copy.write_text(tutelage.DEFAULT_CURRICULUM_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    assert [s["id"] for s in tutelage.load_curriculum(copy)["subjects"]] == ["public-subject"]


def test_private_cycles_go_to_private_store_only(monkeypatch, tmp_path):
    cyc_path, priv_cyc_path = _setup(monkeypatch, tmp_path)
    pub = app.run_study_cycle("pub-1")
    priv = app.run_study_cycle("hush-1")
    assert pub["status"] == "passed" and priv["status"] == "passed"
    assert priv.get("private") is True and "private" not in pub

    public_store = json.loads(cyc_path.read_text(encoding="utf-8"))
    private_store = json.loads(priv_cyc_path.read_text(encoding="utf-8"))
    assert [c["lesson_id"] for c in public_store["cycles"]] == ["pub-1"]
    assert [c["lesson_id"] for c in private_store["cycles"]] == ["hush-1"]
    assert "hush" not in cyc_path.read_text(encoding="utf-8")

    # merged read: prerequisites across stores resolve; retention sees both
    merged = tutelage.load_study_cycles(tutelage.DEFAULT_STUDY_CYCLES_PATH)
    assert {c["lesson_id"] for c in merged["cycles"]} == {"pub-1", "hush-1"}
    assert app.run_study_cycle("hush-2")["status"] == "passed"  # hush-1 prerequisite seen
    # writing again never leaks the merged view into the public file
    assert [c["lesson_id"] for c in json.loads(cyc_path.read_text(encoding="utf-8"))["cycles"]] == ["pub-1"]


def test_redaction_hides_private_names_but_keeps_scores(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    app.run_study_cycle("pub-1")
    app.run_study_cycle("hush-1")
    view = tutelage.redact_private_cycles(tutelage.load_study_cycles(tutelage.DEFAULT_STUDY_CYCLES_PATH))
    ids = sorted(c["lesson_id"] for c in view["cycles"])
    assert ids[0] == "private-lesson-" + ids[0].split("-")[-1] and ids[1] == "pub-1"
    assert "hush" not in json.dumps(view)
    private_view = [c for c in view["cycles"] if c["lesson_id"].startswith("private-lesson-")][0]
    assert private_view["status"] == "passed" and private_view["recall_post"]["score"] == 1.0
    # stable label across calls
    again = tutelage.redact_private_cycles(tutelage.load_study_cycles(tutelage.DEFAULT_STUDY_CYCLES_PATH))
    assert sorted(c["lesson_id"] for c in again["cycles"]) == ids


def test_consolidation_refuses_private_subjects(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    app.run_study_cycle("hush-1")
    with pytest.raises(ValueError, match="study-only"):
        app.run_consolidation("hush-subject")
