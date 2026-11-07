"""The Workbench — code proposals under the operator's biometric (ADR 0027, slice 2).

The protocol is AGENTS.md's self-modification rule, made mechanical:
  proposal   — OMEGA (or the operator) files what should change and why; recorded, visible.
  backup     — nothing touches the live checkout: every change is made in its own git
               worktree on its own branch (workbench/<id>) under .workbench/.
  patch      — the frontier planner drafts exact search/replace edits against named files
               (allowlisted; the gates, secrets and data stores are protected); the runtime
               applies them in the worktree. A miss goes back to the drafter with the reason.
  syntax     — every changed .py file must compile.
  tests      — the full backend suite runs in the worktree. Red = not promotable.
  health     — the worktree's app must import and answer GET / in a subprocess.
  review     — the console shows the diff, the test tail and the health result.
  promote    — the operator's biometric merges the branch into the LIVE main as one commit
               (--no-ff); rollback is one revert of that merge. The runtime never pushes.

The live backend keeps running the old code until the operator restarts it; promote says so.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from copy import deepcopy
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Dict, List, Optional, Tuple

from services.tool_contracts import build_tool_request, utc_now_iso

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKTREES_DIRNAME = ".workbench"
BRANCH_PREFIX = "workbench/"

# Where a proposal may edit (repo-relative, POSIX). Everything else is refused.
ALLOWED_ROOTS = ("backend/", "frontend/src/", "docs/")
# Never editable by a proposal: the gates that make the Workbench safe, secrets, stores, launchers.
PROTECTED = (
    "backend/services/workbench.py",
    "backend/services/tool_approval.py",
    "backend/services/network_breaker.py",
    "backend/services/toolwright.py",
    "backend/services/tool_contracts.py",
    "backend/services/command_registry.py",
    "backend/services/model_control.py",
    "backend/routes/system.py",
    "backend/routes/mobile.py",
    "backend/data/",
    "backend/models/",
    "backend/.venv/",
)
PROTECTED_NAMES = (".env", ".env.", "secrets", "credentials")
SECRET_LINE = re.compile(r"(?i)(api[_-]?key|secret|token|password|passwd)\s*[:=]\s*['\"]?[A-Za-z0-9_\-./+]{12,}")

MAX_FILES = 6
# The frontier's per-request budget is small on the free tier (Groq answered 413 Payload Too
# Large to a 90k-char context on the first live proposal, 2026-11-06). ~4 chars per token:
# 24k chars of code plus the instructions stays well inside an 8k-token request.
MAX_FILE_CHARS = 12_000        # whole file goes to the drafter below this
MAX_CONTEXT_CHARS = 24_000     # total sent to the drafter
EXCERPT_LINES = 40             # lines either side of a keyword hit in a big file
EXCERPT_BLOCKS = 3
MAX_DRAFT_ATTEMPTS = 3
MAX_DIFF_CHARS = 60_000
SUITE_TIMEOUT_SECONDS = 900
HEALTH_TIMEOUT_SECONDS = 180
_STOP = {"the", "and", "for", "with", "that", "this", "from", "into", "when", "then", "should",
         "would", "could", "make", "have", "does", "about", "what", "which", "omega", "runtime",
         "change", "proposal", "please", "also", "like", "just", "more", "less", "than", "them"}


class WorkbenchError(ValueError):
    """A plain, operator-readable refusal or failure."""


# --------------------------------------------------------------------------- store
def _store_path() -> Path:
    from services import tool_contracts as _tc
    return _tc.TOOL_DATA_DIR / "workbench.json"


def _load() -> Dict[str, Any]:
    try:
        data = json.loads(_store_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("version", 1)
    data.setdefault("proposals", [])
    return data


def _save(data: Dict[str, Any]) -> None:
    _store_path().parent.mkdir(parents=True, exist_ok=True)
    _store_path().write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _upsert(entry: Dict[str, Any]) -> Dict[str, Any]:
    data = _load()
    items = [p for p in data["proposals"] if p.get("proposal_id") != entry["proposal_id"]]
    data["proposals"] = [entry, *items]
    _save(data)
    return deepcopy(entry)


def _mark(entry: Dict[str, Any], status: str, event: str) -> None:
    entry["status"] = status
    entry.setdefault("history", []).append({"at": utc_now_iso(), "status": status, "event": event})


def list_proposals() -> List[Dict[str, Any]]:
    return deepcopy(_load()["proposals"])


def get_proposal(proposal_id: str) -> Optional[Dict[str, Any]]:
    return next((deepcopy(p) for p in _load()["proposals"] if p.get("proposal_id") == proposal_id), None)


# --------------------------------------------------------------------------- git
def _git(*args: str, cwd: Optional[Path] = None, check: bool = True) -> str:
    result = subprocess.run(["git", *args], cwd=str(cwd or REPO_ROOT), capture_output=True,
                            text=True, encoding="utf-8", errors="replace")
    if check and result.returncode != 0:
        raise WorkbenchError(f"git {' '.join(args)} failed: {(result.stderr or result.stdout).strip()[:400]}")
    return result.stdout


def _worktree_dir(proposal_id: str) -> Path:
    return REPO_ROOT / WORKTREES_DIRNAME / proposal_id


def _branch(proposal_id: str) -> str:
    return f"{BRANCH_PREFIX}{proposal_id}"


# --------------------------------------------------------------------------- paths
def _normalise_path(raw: str) -> str:
    path = PurePosixPath(str(raw or "").strip().replace("\\", "/"))
    text = str(path)
    if not text or text.startswith("/") or ".." in path.parts or text.startswith("."):
        raise WorkbenchError(f"Refused path {raw!r}: must be repo-relative and inside the repository.")
    return text


def _assert_editable(rel: str) -> None:
    if not rel.startswith(ALLOWED_ROOTS):
        raise WorkbenchError(f"Refused {rel}: proposals may only touch {', '.join(ALLOWED_ROOTS)}.")
    if any(rel == p or rel.startswith(p) for p in PROTECTED):
        raise WorkbenchError(f"Refused {rel}: a protected file (a gate, a store, or a launcher).")
    name = PurePosixPath(rel).name.lower()
    if any(name == n or name.startswith(n) for n in PROTECTED_NAMES):
        raise WorkbenchError(f"Refused {rel}: secrets never enter a proposal.")


# --------------------------------------------------------------------------- 1. propose
def propose(title: str, what: str, why: str, *, requested_by: str, session_id: str,
            files: Optional[List[str]] = None) -> Dict[str, Any]:
    title, what = str(title or "").strip(), str(what or "").strip()
    if not title or not what:
        raise WorkbenchError("A proposal needs a title and a description of the change.")
    named = []
    for raw in files or []:
        rel = _normalise_path(raw)
        _assert_editable(rel)
        named.append(rel)
    entry = {
        "proposal_id": f"chg-{uuid.uuid4().hex[:12]}",
        "title": title[:160],
        "what": what[:4000],
        "why": str(why or "").strip()[:2000],
        "files": named[:MAX_FILES],
        "requested_by": requested_by,
        "session_id": session_id,
        "filed_at": utc_now_iso(),
        "status": "proposed",
        "draft": None,
        "result": None,
        "promotion": None,
        "history": [{"at": utc_now_iso(), "status": "proposed", "event": f"filed by {requested_by}"}],
    }
    return _upsert(entry)


# --------------------------------------------------------------------------- 2. context
def _keywords(entry: Dict[str, Any]) -> List[str]:
    words = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]{3,}", f"{entry['title']} {entry['what']}")
    return [w for w in dict.fromkeys(w.lower() for w in words) if w not in _STOP][:24]


def _candidate_files(root: Path) -> List[str]:
    out: List[str] = []
    for base in ("backend/services", "backend/routes", "backend/tests", "backend/app.py",
                 "frontend/src", "docs/decisions"):
        start = root / base
        if start.is_file():
            out.append(base)
            continue
        for path in start.rglob("*"):
            if path.is_file() and path.suffix in (".py", ".jsx", ".js", ".css", ".md"):
                out.append(path.relative_to(root).as_posix())
    return [p for p in out if not any(p == q or p.startswith(q) for q in PROTECTED)]


_PATH_IN_TEXT = re.compile(r"[\w./-]+\.(?:py|jsx|js|css|md)\b")


def _paths_in_text(root: Path, entry: Dict[str, Any]) -> List[str]:
    """Files the proposal mentions by path ("services/host_clock.py"), resolved against the
    repo root and backend/; the strongest signal there is."""
    found: List[str] = []
    for token in _PATH_IN_TEXT.findall(f"{entry['title']} {entry['what']} {entry.get('why') or ''}"):
        for candidate in (token, f"backend/{token}", f"backend/services/{token}", f"frontend/src/{token}"):
            try:
                rel = _normalise_path(candidate)
            except WorkbenchError:
                continue
            if (root / rel).is_file() and rel not in found:
                found.append(rel)
                break
    return found


def _find_files(root: Path, entry: Dict[str, Any]) -> List[str]:
    """Rank allowlisted files for the drafter. The first live proposal (2026-11-06) asked for
    describe_self + host_clock and raw word counts handed the drafter App.jsx and app.py: big
    files full of "time" and "name". Now: files named by path first; then a score that rewards
    a keyword in the path, a definition of it (def/assignment), and distinct keywords matched,
    normalised by file size so a large file cannot win on bulk alone."""
    keys = _keywords(entry)
    ranked: List[str] = _paths_in_text(root, entry)
    scored: List[Tuple[float, str]] = []
    for rel in _candidate_files(root):
        if rel in ranked:
            continue
        try:
            text = (root / rel).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lowered = text.lower()
        score = 0.0
        for k in keys:
            hits = lowered.count(k)
            if not hits:
                continue
            score += 3 + min(hits, 3)          # distinct keywords matter; bulk repetition does not
            identifier_like = "_" in k or len(k) >= 6   # "describe_self", not "host" or "time"
            if identifier_like and k in rel.lower():
                score += 15
            if _defines(text, k):
                score += 40                     # the file DEFINES the thing the proposal names:
                                                # this must beat every other signal (run 4 buried
                                                # command_console.py under files with "host" in
                                                # their path, and the drafter never saw it)
        if score:
            scored.append((score / (1 + len(text) / 50_000), rel))
    scored.sort(reverse=True)
    return ranked + [rel for _, rel in scored[: max(0, 5 - len(ranked))]]


def _defines(text: str, keyword: str) -> bool:
    return bool(re.search(rf"^\s*(?:def|class)\s+_?{re.escape(keyword)}\b|^{re.escape(keyword)}\s*=",
                          text, re.MULTILINE | re.IGNORECASE))


def definitions_in(root: Path, files: List[str], entry: Dict[str, Any]) -> List[str]:
    """'describe_self -> backend/services/command_console.py line 270 (def _describe_self)':
    deterministic pointers to where the proposal's own identifiers are defined, so the drafter
    edits the real code instead of adding a lookalike elsewhere."""
    pointers: List[str] = []
    for k in _keywords(entry):
        if not ("_" in k or len(k) >= 6):
            continue
        for rel in files:
            try:
                lines = (root / rel).read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for n, line in enumerate(lines, start=1):
                if re.match(rf"^\s*(?:def|class)\s+_?{re.escape(k)}\b", line, re.IGNORECASE):
                    pointers.append(f"{k} -> {rel} line {n} ({line.strip()[:80]})")
                    break
    return pointers


def _excerpts(text: str, keys: List[str]) -> str:
    """At most EXCERPT_BLOCKS windows of 2*EXCERPT_LINES lines, so the size is bounded whatever
    the keywords. Windows are centred first on lines that DEFINE a keyword (def _describe_self),
    then on hits of identifier-like keywords, then on any hit. Overlapping windows are skipped
    rather than merged: merging on common words ("name", "time") once grew an excerpt past
    the whole context budget and the file was dropped (run 5, 2026-11-06)."""
    lines = text.splitlines()
    strong = [k for k in keys if "_" in k or len(k) >= 6]
    centres: List[int] = []
    for pool in (
        [i for i, l in enumerate(lines) if any(re.match(rf"^\s*(?:def|class)\s+_?{re.escape(k)}\b", l, re.IGNORECASE) for k in keys)],
        [i for i, l in enumerate(lines) if any(k in l.lower() for k in strong)],
        [i for i, l in enumerate(lines) if any(k in l.lower() for k in keys)],
    ):
        for i in pool:
            if i not in centres:
                centres.append(i)
    if not centres:
        return "\n".join(f"{i + 1}: {l}" for i, l in enumerate(lines[:EXCERPT_LINES * 2]))
    blocks: List[Tuple[int, int]] = []
    for i in centres:
        lo, hi = max(0, i - EXCERPT_LINES), min(len(lines), i + EXCERPT_LINES)
        if any(lo < b_hi and hi > b_lo for b_lo, b_hi in blocks):
            continue  # already covered by an earlier (higher-priority) window
        blocks.append((lo, hi))
        if len(blocks) == EXCERPT_BLOCKS:
            break
    blocks.sort()
    parts = []
    for lo, hi in blocks:
        parts.append(f"... lines {lo + 1}-{hi} ...\n" + "\n".join(f"{n + 1}: {lines[n]}" for n in range(lo, hi)))
    return "\n".join(parts)


def gather_context(root: Path, entry: Dict[str, Any]) -> Tuple[List[str], str]:
    """The files the drafter sees. Named files that exist come first; names that do not exist
    are dropped (the 8B guessed backend/describe_self.py, 2026-11-06) and a keyword search
    fills in, so the drafter always works from real code."""
    named = [f for f in (entry.get("files") or []) if (root / f).is_file()]
    files = named[:]
    if not named or len(named) < len(entry.get("files") or []):
        for rel in _find_files(root, entry):
            if rel not in files:
                files.append(rel)
    files = files[:MAX_FILES]
    keys = _keywords(entry)
    chunks, total = [], 0
    kept: List[str] = []
    for rel in files:
        _assert_editable(rel)
        path = root / rel
        text = path.read_text(encoding="utf-8", errors="replace")
        if SECRET_LINE.search(text):
            # A file the proposer NAMED is refused out loud. One the keyword search found is
            # simply left out: the second live run died on test_workbench.py's fake API key.
            if rel in named:
                raise WorkbenchError(f"Refused {rel}: it contains what looks like a secret.")
            continue
        body = text if len(text) <= MAX_FILE_CHARS else _excerpts(text, keys)
        chunk = f"=== {rel} ({'whole file' if len(text) <= MAX_FILE_CHARS else 'excerpts, numbered lines'}) ===\n{body}\n"
        if total + len(chunk) > MAX_CONTEXT_CHARS:
            if kept:
                continue  # this one does not fit; a smaller file further down still may
            chunk = chunk[:MAX_CONTEXT_CHARS] + "\n... (cut to the context budget)\n"  # never show nothing
        kept.append(rel)
        chunks.append(chunk)
        total += len(chunk)
    if not kept:
        raise WorkbenchError("No file could be shown to the drafter (none found, or every "
                             "candidate holds what looks like a secret). Name the files to change.")
    pointers = definitions_in(root, kept, entry)
    header = ("DEFINITIONS the proposal refers to (edit THESE, do not add lookalikes):\n"
              + "\n".join(f"- {p}" for p in pointers) + "\n\n") if pointers else ""
    return kept, header + "".join(chunks)


# --------------------------------------------------------------------------- 3. draft
DRAFT_PROMPT = """You are drafting one small, reversible code change for OMEGA-ARC (a local Python/FastAPI
runtime with a React console). An operator will read the diff; a full test suite will run.

PROPOSAL: {title}
WHAT: {what}
WHY: {why}

Rules:
- The smallest change that does the job. Never delete working code to tidy it.
- Match the repository's style. No new dependencies. No network calls added.
- Add or adjust a test under backend/tests/ when behaviour changes.
- Only edit files shown below, or create a new file under backend/tests/ or docs/.
- Change the EXISTING code that implements the behaviour. Never add a parallel function or
  file with a similar name when the real one is shown below: edit the real one.
- Each edit is an exact search/replace: "old" must appear EXACTLY ONCE in the file (copy it
  verbatim, including indentation; use enough lines to be unique). For a new file, "old" is "".
- Some files are shown as numbered excerpts ("12: code"). The "N: " prefix is NOT in the file:
  "old" must contain the code text only, never the line numbers.
- Never write that something "now" does X in a comment or docstring unless your edit makes it so.
{failures}
FILES:
{context}

Reply with ONLY a JSON object:
{{"summary": "<one or two sentences>", "edits": [{{"file": "<repo-relative path>", "old": "<exact text>", "new": "<replacement>"}}]}}
"""


def _frontier(prompt: str) -> Tuple[str, str]:
    from services.adapters.deep_think import _frontier_think
    from services.network_breaker import record_fetch, require_breaker_on

    require_breaker_on()
    try:
        model, text = _frontier_think(prompt)
    except ValueError as exc:  # the provider refused or is unreachable: a reported failure
        record_fetch("frontier", "groq", byte_count=0, ok=False,
                     detail=f"workbench draft: {str(exc)[:160]}")
        raise WorkbenchError(f"the drafter was refused: {exc}") from exc
    record_fetch("frontier", f"groq:{model}", byte_count=len(text), ok=bool(text),
                 detail=f"workbench draft: prompt {len(prompt)} chars")
    return model, text


def _parse_draft(text: str) -> Dict[str, Any]:
    match = re.search(r"\{.*\}", text or "", re.DOTALL)
    if not match:
        raise WorkbenchError("the drafter did not return a JSON object")
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise WorkbenchError(f"the drafter's JSON did not parse ({exc.msg})") from exc
    edits = data.get("edits")
    if not isinstance(edits, list) or not edits:
        raise WorkbenchError("the draft has no edits")
    clean = []
    for edit in edits:
        if not isinstance(edit, dict):
            raise WorkbenchError("an edit is not an object")
        rel = _normalise_path(edit.get("file"))
        _assert_editable(rel)
        clean.append({"file": rel, "old": str(edit.get("old") or ""), "new": str(edit.get("new") or "")})
    return {"summary": str(data.get("summary") or "").strip()[:600], "edits": clean}


def _apply_edits(root: Path, edits: List[Dict[str, str]]) -> List[str]:
    """Apply search/replace edits under `root`. Raises on a miss. Returns the files touched."""
    touched: List[str] = []
    for edit in edits:
        path = root / edit["file"]
        if edit["old"] == "":
            if path.exists():
                raise WorkbenchError(f"{edit['file']}: 'old' is empty but the file exists; "
                                     "give the exact text to replace")
            if not (edit["file"].startswith("backend/tests/") or edit["file"].startswith("docs/")):
                raise WorkbenchError(f"{edit['file']}: new files are allowed only under backend/tests/ or docs/")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(edit["new"], encoding="utf-8")
        else:
            if not path.is_file():
                raise WorkbenchError(f"{edit['file']}: file not found")
            text = path.read_text(encoding="utf-8")
            count = text.count(edit["old"])
            if count != 1:
                raise WorkbenchError(f"{edit['file']}: 'old' text found {count} times; it must appear exactly once")
            path.write_text(text.replace(edit["old"], edit["new"], 1), encoding="utf-8")
        if edit["file"] not in touched:
            touched.append(edit["file"])
    return touched


# --------------------------------------------------------------------------- 4. checks
def _python() -> str:
    return sys.executable


def _subprocess_env() -> Dict[str, str]:
    env = dict(os.environ)
    env.pop("OMEGA_TOOL_DATA_DIR", None)   # the worktree's conftest picks its own temp dir
    env.pop("TURNING_DB_PATH", None)
    env["ENABLE_AGENT_LOOP"] = "false"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def syntax_check(worktree: Path, files: List[str]) -> List[str]:
    """Compile every changed .py; returns the failures (empty = all good)."""
    import py_compile
    failures = []
    for rel in files:
        path = worktree / rel
        if path.suffix == ".py" and path.exists():
            try:
                py_compile.compile(str(path), doraise=True)
            except py_compile.PyCompileError as exc:
                failures.append(f"{rel}: {str(exc).splitlines()[-1][:300]}")
    return failures


def run_suite(worktree: Path) -> Dict[str, Any]:
    """The full backend suite, in the worktree, with the live venv's interpreter."""
    try:
        result = subprocess.run([_python(), "-m", "pytest", "-q", "-p", "no:warnings"],
                                cwd=str(worktree / "backend"), capture_output=True, text=True,
                                encoding="utf-8", errors="replace", env=_subprocess_env(),
                                timeout=SUITE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        return {"ok": False, "passed": 0, "failed": 0, "tail": f"timed out after {SUITE_TIMEOUT_SECONDS}s"}
    return summarize_pytest(result.returncode, result.stdout + result.stderr)


def summarize_pytest(returncode: int, output: str) -> Dict[str, Any]:
    lines = [l for l in output.splitlines() if l.strip()]
    tail = "\n".join(lines[-40:])
    last = lines[-1] if lines else ""
    passed = int(m.group(1)) if (m := re.search(r"(\d+) passed", last)) else 0
    failed = int(m.group(1)) if (m := re.search(r"(\d+) failed", last)) else 0
    errors = int(m.group(1)) if (m := re.search(r"(\d+) error", last)) else 0
    return {"ok": returncode == 0 and failed == 0 and errors == 0, "passed": passed,
            "failed": failed + errors, "tail": tail[-6000:]}


HEALTH_SCRIPT = """
import sys
from fastapi.testclient import TestClient
import app
with TestClient(app.app) as client:
    r = client.get("/")
print("HEALTH", r.status_code)
sys.exit(0 if r.status_code == 200 else 1)
"""


def health_check(worktree: Path) -> Dict[str, Any]:
    """Boot the worktree's app in a subprocess (its own temp stores) and GET /."""
    tmp = Path(tempfile.mkdtemp(prefix="omega-workbench-health-"))
    env = _subprocess_env()
    env["OMEGA_TOOL_DATA_DIR"] = str(tmp / "tool-data")
    env["TURNING_DB_PATH"] = str(tmp / "health.db")
    try:
        result = subprocess.run([_python(), "-c", HEALTH_SCRIPT], cwd=str(worktree / "backend"),
                                capture_output=True, text=True, encoding="utf-8", errors="replace",
                                env=env, timeout=HEALTH_TIMEOUT_SECONDS)
        output = (result.stdout + result.stderr).strip()
        return {"ok": result.returncode == 0 and "HEALTH 200" in output, "tail": output[-2000:]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "tail": f"timed out after {HEALTH_TIMEOUT_SECONDS}s"}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------- 5. draft + test
def draft_and_test(proposal_id: str, *, frontier: Optional[Callable[[str], Tuple[str, str]]] = None,
                   suite: Optional[Callable[[Path], Dict[str, Any]]] = None,
                   health: Optional[Callable[[Path], Dict[str, Any]]] = None) -> Dict[str, Any]:
    """One operator press: worktree, draft, apply, syntax, tests, health. The proposal ends
    'tested' (with a pass/fail result) or 'failed' (nothing could be drafted/applied)."""
    entry = get_proposal(proposal_id)
    if entry is None:
        raise WorkbenchError(f"Unknown proposal {proposal_id}.")
    if entry["status"] not in ("proposed", "failed", "tested"):
        raise WorkbenchError(f"Proposal is {entry['status']}; DRAFT & TEST runs from proposed, failed or tested.")
    frontier = frontier or _frontier
    suite = suite or run_suite
    health = health or health_check

    worktree = _worktree_dir(proposal_id)
    branch = _branch(proposal_id)
    _remove_worktree(proposal_id)  # a re-run starts clean
    base = _git("rev-parse", "HEAD").strip()
    worktree.parent.mkdir(parents=True, exist_ok=True)
    _git("worktree", "add", "-B", branch, str(worktree), "HEAD")
    try:
        return _draft_and_test_in(entry, worktree, base, frontier, suite, health)
    except Exception as exc:  # noqa: BLE001 — whatever broke, the proposal records it and the
        # worktree goes; a 500 with a worktree left behind is what happened on the first live run
        _mark(entry, "failed", f"error during draft/test: {str(exc)[:300]}")
        _upsert(entry)
        _remove_worktree(entry["proposal_id"])
        if isinstance(exc, WorkbenchError):
            raise
        raise WorkbenchError(f"Draft/test failed: {exc}") from exc


def _draft_and_test_in(entry: Dict[str, Any], worktree: Path, base: str, frontier, suite, health) -> Dict[str, Any]:
    proposal_id = entry["proposal_id"]
    files, context = gather_context(worktree, entry)
    failures: List[str] = []
    draft: Dict[str, Any] = {}
    touched: List[str] = []
    model = ""
    for attempt in range(1, MAX_DRAFT_ATTEMPTS + 1):
        prompt = DRAFT_PROMPT.format(
            title=entry["title"], what=entry["what"], why=entry["why"] or "(not given)",
            context=context,
            failures=("\nEARLIER ATTEMPTS FAILED TO APPLY, fix this:\n" + "\n".join(failures) + "\n")
            if failures else "")
        try:
            model, text = frontier(prompt)
            draft = _parse_draft(text)
            # undo a half-applied earlier attempt (edited files, and any new file it created)
            _git("checkout", "--", ".", cwd=worktree, check=False)
            _git("clean", "-fdq", cwd=worktree, check=False)
            touched = _apply_edits(worktree, draft["edits"])
            break
        except WorkbenchError as exc:
            failures.append(f"attempt {attempt}: {exc}")
            draft, touched = {}, []
            if "413" in str(exc) or "too large" in str(exc).lower():
                context = context[: len(context) // 2] + "\n... (context halved: the drafter's request limit)\n"
    if not touched:
        _mark(entry, "failed", "draft could not be applied: " + " | ".join(failures))
        entry["draft"] = {"model": model, "failures": failures}
        _remove_worktree(proposal_id)
        return _upsert(entry)

    _git("add", "-A", cwd=worktree)
    _git("-c", "user.name=OMEGA-ARC Workbench", "-c", "user.email=workbench@omega-arc.local",
         "commit", "-q", "-m", f"Workbench {proposal_id}: {entry['title']}", cwd=worktree)
    diff = _git("diff", f"{base}..HEAD", cwd=worktree)
    syntax = syntax_check(worktree, touched)
    tests = suite(worktree) if not syntax else {"ok": False, "passed": 0, "failed": 0, "tail": "skipped: syntax errors"}
    healthy = health(worktree) if tests["ok"] else {"ok": False, "tail": "skipped: tests not green"}
    entry["draft"] = {"model": model, "summary": draft.get("summary", ""), "files": touched,
                      "attempts": len(failures) + 1, "base": base,
                      "head": _git("rev-parse", "HEAD", cwd=worktree).strip(),
                      "diff": diff[:MAX_DIFF_CHARS], "diff_truncated": len(diff) > MAX_DIFF_CHARS}
    entry["result"] = {"syntax_failures": syntax, "tests": tests, "health": healthy,
                       "promotable": not syntax and tests["ok"] and healthy["ok"], "at": utc_now_iso()}
    _mark(entry, "tested", "promotable: every check green" if entry["result"]["promotable"]
          else f"NOT promotable: syntax {len(syntax)} / tests {'green' if tests['ok'] else 'red'} / "
               f"health {'ok' if healthy['ok'] else 'failed'}")
    return _upsert(entry)


# --------------------------------------------------------------------------- 6. promote
def request_promotion(proposal_id: str, *, requested_by: str) -> Dict[str, Any]:
    from services.tool_approval import create_approval_request

    entry = get_proposal(proposal_id)
    if entry is None:
        raise WorkbenchError(f"Unknown proposal {proposal_id}.")
    if entry["status"] not in ("tested", "awaiting_promotion"):
        raise WorkbenchError("Promotion is requested on a tested proposal.")
    if not (entry.get("result") or {}).get("promotable"):
        raise WorkbenchError("This proposal is not promotable: a check is red. Re-run DRAFT & TEST.")
    request = build_tool_request(tool_name="workbench_promote",
                                 arguments={"proposal_id": proposal_id, "title": entry["title"]},
                                 requested_by=requested_by, session_id=entry.get("session_id") or "workbench")
    approval = create_approval_request(request)
    entry["promotion"] = {"request_id": request["request_id"], "approval_id": approval["approval_id"],
                          "requested_at": utc_now_iso(), "expires_at": approval.get("expires_at")}
    _mark(entry, "awaiting_promotion", "promotion approval raised; the biometric on a mobile console releases it")
    return _upsert(entry)


def promotion_approval_is_dead(entry: Dict[str, Any]) -> bool:
    from datetime import datetime, timezone
    from services.tool_approval import get_tool_approval, load_tool_approval_store

    if entry.get("status") != "awaiting_promotion":
        return False
    approval = get_tool_approval((entry.get("promotion") or {}).get("approval_id") or "",
                                 load_tool_approval_store())
    if not approval or approval.get("consumed_at"):
        return not approval
    if approval.get("status") in {"expired", "rejected", "revoked"}:
        return True
    if approval.get("status") == "approved":
        return False
    try:
        expires = datetime.fromisoformat(str(approval.get("expires_at") or "").replace("Z", "+00:00"))
    except ValueError:
        return True
    return expires <= datetime.now(timezone.utc)


def complete_promotion(proposal_id: str) -> Dict[str, Any]:
    from services.tool_approval import consume_approval, get_tool_approval, load_tool_approval_store

    entry = get_proposal(proposal_id)
    if entry is None:
        raise WorkbenchError(f"Unknown proposal {proposal_id}.")
    if entry["status"] != "awaiting_promotion" or not entry.get("promotion"):
        raise WorkbenchError("Completion runs on a proposal awaiting promotion.")
    approval = get_tool_approval(entry["promotion"]["approval_id"], load_tool_approval_store())
    if not approval or approval.get("status") != "approved" or approval.get("consumed_at"):
        raise PermissionError("Promotion waits for an approved, unconsumed approval.")
    if approval.get("confirmation") != "biometric":
        raise PermissionError("Promotion requires the operator's BIOMETRIC confirmation on a mobile console.")
    files = (entry.get("draft") or {}).get("files") or []
    dirty = _git("status", "--porcelain", "--", *files).strip() if files else ""
    if dirty:
        raise WorkbenchError("The live checkout has uncommitted changes in the proposal's files; "
                             f"commit or discard them first:\n{dirty[:400]}")
    try:
        _git("merge", "--no-ff", "--no-edit", "-m", f"Workbench promote {proposal_id}: {entry['title']}",
             _branch(proposal_id))
    except WorkbenchError:
        _git("merge", "--abort", check=False)
        raise WorkbenchError("The branch no longer merges cleanly into main (main moved). "
                             "Re-run DRAFT & TEST to redraft against the current code.")
    merge_sha = _git("rev-parse", "HEAD").strip()
    consume_approval(entry["promotion"]["approval_id"])
    entry["promotion"]["merge_sha"] = merge_sha
    entry["promotion"]["promoted_at"] = utc_now_iso()
    _remove_worktree(proposal_id, keep_branch=True)
    _mark(entry, "promoted", f"merged into main as {merge_sha[:10]} by biometric approval; "
                             "restart the backend to run it")
    return _upsert(entry)


def rollback(proposal_id: str, *, by: str) -> Dict[str, Any]:
    entry = get_proposal(proposal_id)
    if entry is None:
        raise WorkbenchError(f"Unknown proposal {proposal_id}.")
    merge_sha = (entry.get("promotion") or {}).get("merge_sha")
    if entry["status"] != "promoted" or not merge_sha:
        raise WorkbenchError("Rollback runs on a promoted proposal.")
    files = (entry.get("draft") or {}).get("files") or []
    dirty = _git("status", "--porcelain", "--", *files).strip() if files else ""
    if dirty:
        raise WorkbenchError("The live checkout has uncommitted changes in the proposal's files; "
                             f"commit or discard them first:\n{dirty[:400]}")
    try:
        _git("revert", "--no-edit", "-m", "1", merge_sha)
    except WorkbenchError:
        _git("revert", "--abort", check=False)
        raise
    entry["promotion"]["revert_sha"] = _git("rev-parse", "HEAD").strip()
    _mark(entry, "rolled_back", f"reverted by {by}; restart the backend to run the old code")
    return _upsert(entry)


def reject(proposal_id: str, *, by: str) -> Dict[str, Any]:
    entry = get_proposal(proposal_id)
    if entry is None:
        raise WorkbenchError(f"Unknown proposal {proposal_id}.")
    if entry["status"] in ("promoted", "rolled_back"):
        raise WorkbenchError(f"A {entry['status']} proposal is history; use rollback for a promoted one.")
    _remove_worktree(proposal_id)
    _mark(entry, "rejected", f"rejected by {by}; worktree and branch removed")
    return _upsert(entry)


def _remove_worktree(proposal_id: str, *, keep_branch: bool = False) -> None:
    worktree = _worktree_dir(proposal_id)
    if worktree.exists():
        _git("worktree", "remove", "--force", str(worktree), check=False)
        shutil.rmtree(worktree, ignore_errors=True)
    _git("worktree", "prune", check=False)
    if not keep_branch:
        _git("branch", "-D", _branch(proposal_id), check=False)
