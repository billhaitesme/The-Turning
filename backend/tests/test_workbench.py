"""The Workbench (ADR 0027 slice 2): proposal -> worktree draft -> syntax/tests/health -> review
-> biometric promote (one merge) -> rollback (one revert). Git is real, on a temporary repo;
the suite run, the health check and the frontier are stubbed."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from services import tool_approval, workbench

HELLO = "def greet(name):\n    return f'Hello, {name}'\n"
TEST_HELLO = "from services.hello import greet\n\n\ndef test_greet():\n    assert greet('Bill') == 'Hello, Bill'\n"
GOOD_EDIT = {"summary": "Greet politely.", "edits": [
    {"file": "backend/services/hello.py", "old": "return f'Hello, {name}'", "new": "return f'Hello, {name}!'"},
    {"file": "backend/tests/test_hello_polite.py", "old": "",
     "new": "from services.hello import greet\n\n\ndef test_polite():\n    assert greet('Bill').endswith('!')\n"},
]}
GREEN = {"ok": True, "passed": 2, "failed": 0, "tail": "2 passed"}
RED = {"ok": False, "passed": 1, "failed": 1, "tail": "1 failed, 1 passed"}
HEALTHY = {"ok": True, "tail": "HEALTH 200"}


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True, check=True).stdout


@pytest.fixture
def repo(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    (root / "backend" / "services").mkdir(parents=True)
    (root / "backend" / "tests").mkdir()
    (root / "backend" / "data").mkdir()
    (root / "backend" / "services" / "hello.py").write_text(HELLO, encoding="utf-8")
    (root / "backend" / "tests" / "test_hello.py").write_text(TEST_HELLO, encoding="utf-8")
    (root / "backend" / "services" / "tool_approval.py").write_text("GATE = True\n", encoding="utf-8")
    (root / "backend" / "services" / "keys.py").write_text("API_KEY = 'sk-abcdefghijklmnop123456'\n", encoding="utf-8")
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "t@t")
    git(root, "config", "user.name", "t")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "base")
    monkeypatch.setattr(workbench, "REPO_ROOT", root)
    monkeypatch.setattr(workbench, "run_suite", lambda worktree: GREEN)
    monkeypatch.setattr(workbench, "health_check", lambda worktree: HEALTHY)
    workbench._store_path().unlink(missing_ok=True)
    yield root
    workbench._store_path().unlink(missing_ok=True)


def render_draft(draft):
    """A draft dict in the block format the drafter is asked for."""
    lines = ["=== SUMMARY", draft.get("summary", "")]
    if draft.get("needs_from_operator"):
        lines += ["=== NEEDS", draft["needs_from_operator"]]
    for edit in draft.get("edits") or []:
        lines += [f"=== EDIT {edit['file']}", "<<<OLD", edit["old"], ">>>NEW", edit["new"]]
    lines.append("=== END")
    return "\n".join(lines) + "\n"


def frontier_with(*drafts):
    queue = list(drafts)
    prompts = []

    def frontier(prompt):
        prompts.append(prompt)
        return "openai/gpt-oss-120b", render_draft(queue.pop(0))
    frontier.prompts = prompts
    return frontier


def propose(files=None):
    return workbench.propose("Polite greeting", "greet() should end with an exclamation mark",
                             "warmth", requested_by="model:agent-seat", session_id="s", files=files)


def test_proposals_refuse_gates_secrets_and_traversal(repo):
    for bad in ("backend/services/tool_approval.py", "backend/services/workbench.py",
                "backend/services/network_breaker.py", "backend/routes/system.py",
                "backend/data/goals.json", ".env", "backend/../../etc/passwd", "scripts/launch_backend.py"):
        with pytest.raises(workbench.WorkbenchError):
            propose(files=[bad])
    assert workbench.list_proposals() == []
    # the registries are editable: adding a hand is what proposals are for
    (repo / "backend" / "services" / "command_registry.py").write_text("COMMANDS = []\n", encoding="utf-8")
    assert propose(files=["backend/services/command_registry.py"])["files"] == ["backend/services/command_registry.py"]


def test_draft_test_promote_and_rollback_end_to_end(repo):
    entry = propose(files=["backend/services/hello.py"])
    pid = entry["proposal_id"]
    live = repo / "backend" / "services" / "hello.py"

    tested = workbench.draft_and_test(pid, frontier=frontier_with(GOOD_EDIT))
    assert tested["status"] == "tested" and tested["result"]["promotable"] is True
    assert "+    return f'Hello, {name}!'" in tested["draft"]["diff"]
    assert tested["draft"]["files"] == ["backend/services/hello.py", "backend/tests/test_hello_polite.py"]
    assert live.read_text(encoding="utf-8") == HELLO                       # the live checkout is untouched
    assert (workbench._worktree_dir(pid) / "backend" / "services" / "hello.py").read_text(encoding="utf-8").endswith("!'\n")
    assert f"workbench/{pid}" in git(repo, "branch", "--list", f"workbench/{pid}")

    waiting = workbench.request_promotion(pid, requested_by="operator:desktop")
    assert waiting["status"] == "awaiting_promotion"
    with pytest.raises(PermissionError):
        workbench.complete_promotion(pid)                                  # no approval yet
    tool_approval.approve_request(waiting["promotion"]["request_id"], approved_by="operator")
    with pytest.raises(PermissionError, match="BIOMETRIC"):
        workbench.complete_promotion(pid)                                  # plain approval is not enough
    tool_approval.approve_request(waiting["promotion"]["request_id"], approved_by="operator",
                                  confirmation="biometric")
    promoted = workbench.complete_promotion(pid)
    assert promoted["status"] == "promoted"
    assert live.read_text(encoding="utf-8").endswith("!'\n")             # ONE merge changed main
    assert "Workbench promote" in git(repo, "log", "-1", "--format=%s")
    assert git(repo, "log", "-1", "--format=%P").split().__len__() == 2  # a merge commit (--no-ff)
    assert not workbench._worktree_dir(pid).exists()
    with pytest.raises(workbench.WorkbenchError):
        workbench.complete_promotion(pid)                                  # a promoted proposal cannot be re-promoted

    rolled = workbench.rollback(pid, by="operator:desktop")
    assert rolled["status"] == "rolled_back"
    assert live.read_text(encoding="utf-8") == HELLO                       # ONE revert restored it
    assert not (repo / "backend" / "tests" / "test_hello_polite.py").exists()


def test_a_missed_edit_goes_back_to_the_drafter_with_the_reason(repo):
    miss = {"summary": "x", "edits": [{"file": "backend/services/hello.py", "old": "return 'nope'", "new": "y"}]}
    frontier = frontier_with(miss, GOOD_EDIT)
    tested = workbench.draft_and_test(propose()["proposal_id"], frontier=frontier)
    assert tested["status"] == "tested" and tested["draft"]["attempts"] == 2
    assert "found 0 times" in frontier.prompts[1]


def test_red_tests_are_not_promotable(repo, monkeypatch):
    monkeypatch.setattr(workbench, "run_suite", lambda worktree: RED)
    tested = workbench.draft_and_test(propose()["proposal_id"], frontier=frontier_with(GOOD_EDIT))
    assert tested["status"] == "tested" and tested["result"]["promotable"] is False
    assert tested["result"]["health"]["tail"].startswith("skipped")
    with pytest.raises(workbench.WorkbenchError, match="not promotable"):
        workbench.request_promotion(tested["proposal_id"], requested_by="operator:desktop")


def test_a_syntax_error_is_caught_before_the_suite_runs(repo, monkeypatch):
    monkeypatch.setattr(workbench, "run_suite", lambda worktree: pytest.fail("suite must not run"))
    broken = {"summary": "x", "edits": [{"file": "backend/services/hello.py", "old": "return f'Hello, {name}'",
                                         "new": "return f'Hello, {name}'\n  oops ="}]}
    tested = workbench.draft_and_test(propose()["proposal_id"], frontier=frontier_with(broken))
    assert tested["result"]["syntax_failures"] and tested["result"]["promotable"] is False


def test_a_file_with_a_secret_never_reaches_the_drafter(repo):
    # named by the proposer: refused out loud
    with pytest.raises(workbench.WorkbenchError, match="secret"):
        workbench.gather_context(repo, propose(files=["backend/services/keys.py"]))
    # found by the keyword search: silently left out, the rest still goes (live failure #2)
    (repo / "backend" / "services" / "keys.py").write_text(
        "# greet greet greet exclamation polite\nAPI_KEY = 'sk-abcdefghijklmnop123456'\n", encoding="utf-8")
    files, context = workbench.gather_context(repo, propose())
    assert "backend/services/keys.py" not in files and "sk-abcdef" not in context
    assert "backend/services/hello.py" in files


def test_drafts_may_not_touch_protected_or_outside_files(repo):
    for bad_file in ("backend/services/tool_approval.py", "backend/data/x.json", "scripts/x.py"):
        bad = {"summary": "x", "edits": [{"file": bad_file, "old": "", "new": "pwned"}]}
        failed = workbench.draft_and_test(propose()["proposal_id"], frontier=frontier_with(bad, bad, bad))
        assert failed["status"] == "failed" and "Refused" in failed["history"][-1]["event"]
        assert not (repo / bad_file).exists() or (repo / bad_file).read_text(encoding="utf-8") != "pwned"


def test_reject_removes_worktree_and_branch(repo):
    pid = propose()["proposal_id"]
    workbench.draft_and_test(pid, frontier=frontier_with(GOOD_EDIT))
    assert workbench._worktree_dir(pid).exists()
    assert workbench.reject(pid, by="operator:desktop")["status"] == "rejected"
    assert not workbench._worktree_dir(pid).exists()
    assert git(repo, "branch", "--list", f"workbench/{pid}").strip() == ""


def test_a_dirty_live_file_blocks_promotion(repo):
    pid = propose()["proposal_id"]
    workbench.draft_and_test(pid, frontier=frontier_with(GOOD_EDIT))
    waiting = workbench.request_promotion(pid, requested_by="operator:desktop")
    tool_approval.approve_request(waiting["promotion"]["request_id"], approved_by="o", confirmation="biometric")
    (repo / "backend" / "services" / "hello.py").write_text(HELLO + "# local edit\n", encoding="utf-8")
    with pytest.raises(workbench.WorkbenchError, match="uncommitted"):
        workbench.complete_promotion(pid)


def test_excerpts_are_bounded_and_centred_on_the_definition(repo):
    # a big file where the proposal's common words ("name", "time") hit nearly every line
    body = "\n".join(f"name = time = {i}  # host zone offset" for i in range(1500))
    big = (repo / "backend" / "services" / "command_console.py")
    big.write_text(body + "\n\n\ndef _describe_self():\n    return {}\n" + body, encoding="utf-8")
    entry = propose(files=["backend/services/command_console.py"])
    entry["title"], entry["what"] = "Add host time zone to describe_self", "Modify describe_self to include the host time zone name"
    files, context = workbench.gather_context(repo, entry)
    assert files == ["backend/services/command_console.py"]             # it was NOT dropped (run 5)
    assert len(context) <= workbench.MAX_CONTEXT_CHARS + 200
    assert "def _describe_self" in context                                # the window is centred on it
    assert context.count("... lines ") <= workbench.EXCERPT_BLOCKS


def test_a_proposal_can_say_what_it_needs_from_the_operator(repo):
    entry = workbench.propose("Browser control", "drive a browser from greet()", "operator asked",
                              requested_by="model:agent-seat", session_id="s",
                              files=["backend/services/hello.py"],
                              needs="pip install playwright; playwright install chromium")
    assert entry["needs_from_operator"].startswith("pip install playwright")
    frontier = frontier_with(GOOD_EDIT)
    workbench.draft_and_test(entry["proposal_id"], frontier=frontier)
    assert "THE OPERATOR HAS AGREED TO PROVIDE: pip install playwright" in frontier.prompts[0]


def test_the_drafter_can_say_what_the_operator_must_provide_first(repo):
    blocked = {"summary": "Needs a browser driver.", "edits": [],
               "needs_from_operator": "in backend/.venv: pip install playwright; playwright install chromium"}
    frontier = frontier_with(blocked, GOOD_EDIT)
    entry = workbench.propose("Browser control", "drive a browser from greet()", "", requested_by="m",
                              session_id="s", files=["backend/services/hello.py"])
    out = workbench.draft_and_test(entry["proposal_id"], frontier=frontier)
    assert out["status"] == "blocked" and out["needs_from_operator"].startswith("in backend/.venv: pip install")
    assert not workbench._worktree_dir(entry["proposal_id"]).exists()
    with pytest.raises(workbench.WorkbenchError):
        workbench.request_promotion(entry["proposal_id"], requested_by="o")   # nothing to promote
    # the operator provides it, presses DRAFT & TEST again: the drafter now sees it as agreed
    again = workbench.draft_and_test(entry["proposal_id"], frontier=frontier)
    assert "THE OPERATOR HAS AGREED TO PROVIDE: in backend/.venv: pip install playwright" in frontier.prompts[1]
    assert again["status"] == "tested"


def test_a_rate_limited_frontier_is_waited_out_then_falls_back_to_the_local_rung(repo, monkeypatch):
    """Groq 429 on the first own-browser draft (2026-11-06): the retries fired within the same
    minute and were refused too, and the local rung was never tried."""
    from services.adapters import deep_think
    waited = []
    monkeypatch.setattr(workbench, "_sleep", lambda s: waited.append(s))
    calls = {"frontier": 0, "local": 0}

    def frontier_429(prompt):
        calls["frontier"] += 1
        raise ValueError("deep rung 'frontier' refused by provider: HTTP 429 (Rate limit reached)")

    def local(prompt):
        calls["local"] += 1
        return "huihui_ai/qwen3-abliterated:30b-a3b", render_draft(GOOD_EDIT)

    monkeypatch.setattr(deep_think, "_frontier_think", frontier_429)
    monkeypatch.setattr(deep_think, "_local_think", local)
    from services import network_breaker
    network_breaker.set_breaker(True, changed_by="test", channel="test")
    try:
        model, text = workbench._frontier("draft please")
    finally:
        network_breaker.set_breaker(False, changed_by="test", channel="test")
    assert waited == [workbench.RATE_LIMIT_WAIT_SECONDS]          # one real wait, not an instant retry
    assert calls == {"frontier": 2, "local": 1}
    assert model.endswith("(local fallback)") and workbench._parse_draft(text)["summary"] == GOOD_EDIT["summary"]


def test_a_cut_off_draft_tells_the_drafter_to_be_compact():
    with pytest.raises(workbench.WorkbenchError, match="cut off"):
        workbench._parse_draft("=== SUMMARY\nx\n=== EDIT backend/services/hello.py\n<<<OLD\nb\n>>>NEW\nunterminated")
    with pytest.raises(workbench.WorkbenchError, match="block format"):
        workbench._parse_draft('{"summary": "json is not the format"}')


def test_the_block_format_carries_code_verbatim_and_new_files():
    text = render_draft({"summary": "s", "edits": [
        {"file": "backend/services/hello.py", "old": 'return f"Hello, {name}"', "new": 'return f"Hello, {name}!"  # "quoted"'},
        {"file": "backend/tests/test_new.py", "old": "", "new": "def test_x():\n    assert 'a' in \"abc\""},
    ]})
    draft = workbench._parse_draft(text)
    assert draft["summary"] == "s" and len(draft["edits"]) == 2
    assert draft["edits"][0]["new"] == 'return f"Hello, {name}!"  # "quoted"'       # quotes survive untouched
    assert draft["edits"][1]["old"] == "" and draft["edits"][1]["new"].endswith('"abc"\n')  # new file, trailing newline


def test_pytest_summary_parsing():
    assert workbench.summarize_pytest(0, "....\n605 passed, 10 subtests passed in 87.84s") == {
        "ok": True, "passed": 605, "failed": 0, "tail": "....\n605 passed, 10 subtests passed in 87.84s"}
    red = workbench.summarize_pytest(1, "F..\n1 failed, 2 passed in 1.0s")
    assert red["ok"] is False and red["failed"] == 1 and red["passed"] == 2


def test_guessed_file_names_fall_back_to_real_files(repo):
    # the 8B named files that do not exist; the drafter must still see real code
    entry = propose(files=["backend/greeting.py", "backend/services/hello.py"])
    files, context = workbench.gather_context(repo, entry)
    assert "backend/services/hello.py" in files and "backend/greeting.py" not in files
    assert "def greet" in context


def test_ranking_prefers_named_paths_and_definitions_over_big_wordy_files(repo):
    # a big decoy stuffed with the proposal's common words, and the two real targets
    (repo / "backend" / "services" / "decoy.py").write_text(
        "# time name host zone offset\n" * 800, encoding="utf-8")
    (repo / "backend" / "services" / "host_clock.py").write_text(
        "def host_clock():\n    return {'name': 'Central'}\n", encoding="utf-8")
    (repo / "backend" / "services" / "command_console.py").write_text(
        "def _describe_self():\n    return {'voice': 'bm_fable'}\n", encoding="utf-8")
    entry = workbench.propose(
        "Add host time zone to describe_self",
        "Modify describe_self to include the host's time zone name and UTC offset "
        "(the runtime already has services/host_clock.py with host_clock())",
        "", requested_by="model:agent-seat", session_id="s")
    # and a file whose PATH carries the common word "host" (run 4: these buried the definition)
    (repo / "backend" / "services" / "host_status.py").write_text(
        "# host host time name\ndef status():\n    return 'host'\n", encoding="utf-8")
    files = workbench._find_files(repo, entry)
    assert files[0] == "backend/services/host_clock.py"           # named by path in the text
    assert files[1] == "backend/services/command_console.py"      # DEFINES _describe_self: next
    _, context = workbench.gather_context(repo, entry)
    assert "DEFINITIONS the proposal refers to" in context
    assert "describe_self -> backend/services/command_console.py line 1 (def _describe_self" in context
    decoy_rank = files.index("backend/services/decoy.py") if "backend/services/decoy.py" in files else len(files)
    assert files.index("backend/services/command_console.py") < decoy_rank  # a definition beats word soup
