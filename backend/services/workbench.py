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
import time
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
    # command_registry.py and tool_registry.py are deliberately NOT protected: adding a hand is
    # the main thing OMEGA proposes, and the registry's own import-time invariants (a direct
    # command must be low-risk; approval commands map to a bounded tool) plus the operator's
    # diff review and biometric are the guard (2026-11-06).
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
MAX_FILE_CHARS = 10_000        # whole file goes to the drafter below this
# Groq's free tier allows 8,000 tokens per minute and refuses any single request above it,
# prompt AND completion together. 16k chars of code (~4k tokens) plus ~1k of instructions leaves
# ~3k tokens for the draft. (24k chars left nothing: the first own-browser draft was cut off
# mid-JSON and the retries were throttled, 2026-11-06.)
MAX_CONTEXT_CHARS = 16_000     # total sent to the drafter
RATE_LIMIT_WAIT_SECONDS = 61.0 # a 429 means the minute's budget is spent: wait it out once
# The drafter is chosen by WORKBENCH_DRAFTER. "groq" = the Mind Ladder's frontier planner on
# the operator's Groq key (the small budgets above). "claude-code" = the operator's Claude Code
# CLI on his subscription (`claude -p`, tools off: it only WRITES the draft; the Workbench
# applies and tests it), whose budget is an order of magnitude larger, so a four-file draft
# arrives in one reply and the context may show whole files. Either falls down the ladder when
# it fails: claude-code -> groq -> the local deep rung.
LARGE_FILE_CHARS = 40_000
LARGE_CONTEXT_CHARS = 60_000
CLAUDE_CODE_TIMEOUT_SECONDS = 600.0
EXCERPT_LINES = 40             # lines either side of a keyword hit in a big file
EXCERPT_BLOCKS = 3
MAX_DRAFT_ATTEMPTS = 3
MAX_DRAFT_PARTS = 4            # a draft delivered in parts (=== CONTINUE), each within the budget
MAX_REPAIR_ROUNDS = 2          # red suite -> the failure goes back to the drafter, this many times
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
            files: Optional[List[str]] = None, needs: str = "") -> Dict[str, Any]:
    """`needs` is what only the operator can provide for this change (a package installed, a
    device, an account): it is shown on the console as NEEDS FROM YOU and relaxes the drafter's
    no-new-dependencies rule for exactly those items (Bill, 2026-11-06: "it should be able to
    tell me what it needs")."""
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
        "needs_from_operator": str(needs or "").strip()[:1000],
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


class DraftContext:
    """What the drafter may see and must touch.

    targets   files to edit or create, in the proposal's order (named files that exist, then
              the NEW files it names); one per reply when the drafter's budget is small
    new_files the subset of targets that do not exist yet
    reference files the keyword search added for reading (never asked for on their own)
    header    definition pointers, shown with every reply
    chunks    one bounded chunk of code per existing file
    """

    def __init__(self, targets: List[str], new_files: List[str], reference: List[str],
                 header: str, chunks: Dict[str, str]) -> None:
        self.targets, self.new_files, self.reference = targets, new_files, reference
        self.header, self.chunks = header, chunks

    @property
    def files(self) -> List[str]:
        return [f for f in self.targets if f not in self.new_files] + self.reference

    def new_file_note(self, only: Optional[str] = None) -> str:
        names = [f for f in self.new_files if only is None or f == only]
        if not names:
            return ""
        return ("NEW FILES the proposal names (they do not exist yet: create each with ONE edit whose "
                "OLD part is empty; import the helpers above by the paths shown):\n"
                + "\n".join(f"- {f}" for f in names) + "\n\n")

    def text(self, only: Optional[str] = None) -> str:
        """The whole context, or (paced) the pointers plus ONE target's code or new-file note."""
        if only is None:
            return self.header + self.new_file_note() + "".join(self.chunks[f] for f in self.files)
        return self.header + self.new_file_note(only) + self.chunks.get(only, "")


def _new_files_named(root: Path, entry: Dict[str, Any]) -> List[str]:
    """Named files that do not exist are NEW only when the proposal's text names them by path
    (the own-browser proposal did, 2026-11-06); a bare guess in the files list is dropped as
    before (the 8B guessed backend/describe_self.py), so the drafter never invents lookalikes."""
    text = f"{entry.get('title', '')} {entry.get('what', '')}"
    out: List[str] = []
    for rel in entry.get("files") or []:
        if (root / rel).exists() or rel not in text:
            continue
        _assert_editable(rel)
        if (root / rel).parent.is_dir():
            out.append(rel)
    return out


def gather_plan(root: Path, entry: Dict[str, Any], *, large_budget: bool = False) -> DraftContext:
    """The files the drafter sees. Named files that exist come first; names that do not exist
    are dropped (the 8B guessed backend/describe_self.py, 2026-11-06) unless the proposal's text
    names them as new files, and a keyword search fills in, so the drafter always works from
    real code. A large-budget drafter (Claude Code) is shown whole files up to a bigger cap."""
    file_cap = LARGE_FILE_CHARS if large_budget else MAX_FILE_CHARS
    context_cap = LARGE_CONTEXT_CHARS if large_budget else MAX_CONTEXT_CHARS
    named = [f for f in (entry.get("files") or []) if (root / f).is_file()]
    new_files = _new_files_named(root, entry)
    files = named[:]
    # the search adds files to READ when names are missing or guessed, and whenever a new file
    # is to be written (its helpers live in files the proposal did not name)
    if not named or new_files or len(named) + len(new_files) < len(entry.get("files") or []):
        for rel in _find_files(root, entry):
            if rel not in files:
                files.append(rel)
    files = files[:MAX_FILES]
    keys = _keywords(entry)
    chunks: Dict[str, str] = {}
    total = 0
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
        body = text if len(text) <= file_cap else _excerpts(text, keys)
        chunk = f"=== {rel} ({'whole file' if len(text) <= file_cap else 'excerpts, numbered lines'}) ===\n{body}\n"
        if total + len(chunk) > context_cap:
            if kept:
                continue  # this one does not fit; a smaller file further down still may
            chunk = chunk[:context_cap] + "\n... (cut to the context budget)\n"  # never show nothing
        kept.append(rel)
        chunks[rel] = chunk
        total += len(chunk)
    if not kept and not new_files:
        raise WorkbenchError("No file could be shown to the drafter (none found, or every "
                             "candidate holds what looks like a secret). Name the files to change.")
    pointers = definitions_in(root, kept, entry)
    header = ("DEFINITIONS the proposal refers to (edit THESE, do not add lookalikes):\n"
              + "\n".join(f"- {p}" for p in pointers) + "\n\n") if pointers else ""
    # the proposal's own order, new files included; files the search added come after, to read
    targets = [f for f in (entry.get("files") or []) if f in kept or f in new_files]
    reference = [f for f in kept if f not in targets]
    return DraftContext(targets, new_files, reference, header, chunks)


def gather_context(root: Path, entry: Dict[str, Any]) -> Tuple[List[str], str]:
    """(files shown, context text): the one-reply view of gather_plan."""
    plan = gather_plan(root, entry)
    return plan.files, plan.text()


# --------------------------------------------------------------------------- 3. draft
DRAFT_PROMPT = """You are drafting one small, reversible code change for OMEGA-ARC (a local Python/FastAPI
runtime with a React console). An operator will read the diff; a full test suite will run.

PROPOSAL: {title}
WHAT: {what}
WHY: {why}
{needs}
Rules:
- The smallest change that does the job. Never delete working code to tidy it.
- Match the repository's style. No new dependencies beyond what the operator has agreed to
  provide (listed above, if anything). No network calls added.
- Add or adjust a test under backend/tests/ when behaviour changes.
- Only edit files shown below, or create the NEW files the proposal names (anywhere under
  backend/, frontend/src/ or docs/).
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

Reply in EXACTLY this block format and nothing else (no JSON, no code fences, no commentary;
{budget_line}):

=== SUMMARY
one or two sentences
=== EDIT <repo-relative path>
<<<OLD
the exact existing text to replace (leave this part empty for a NEW file)
>>>NEW
the replacement text
=== EDIT <another file>
<<<OLD
...
>>>NEW
...
=== END

If the whole change does not fit in one reply, stop at a FILE boundary and end with
=== CONTINUE
instead of === END; you will be asked for the rest (and told which files are already done).

If the change CANNOT be made without something only the operator can provide (a package not
installed, a program, a device, an account or key) that is not listed as agreed above, do not
draft. Reply instead with:

=== SUMMARY
why
=== NEEDS
the exact commands or items, e.g. in backend/.venv: pip install playwright; playwright install chromium
=== END
"""


def _sleep(seconds: float) -> None:  # module-level so tests can make waiting instant
    time.sleep(seconds)


REPAIR_PROMPT = """Your draft for this OMEGA-ARC change was applied, and THE SUITE FAILED. Fix it with further
edits on top of the files as they are NOW (shown below). Re-read WHAT and make sure every
requirement in it is met, including anything your draft skipped.

PROPOSAL: {title}
WHAT: {what}

FAILURE:
{failure}

FILES AS THEY ARE NOW:
{context}

Reply in the same block format (=== SUMMARY / === EDIT <path> / <<<OLD / >>>NEW / === END):
"old" must match the CURRENT text exactly once. Keep the reply under 2500 tokens.
"""


def drafter_name() -> str:
    return (os.getenv("WORKBENCH_DRAFTER") or "groq").strip().lower()


def small_budget() -> bool:
    """Groq's free tier is the small budget (8k tokens, prompt and completion together); Claude
    Code answers in tens of thousands, so nothing need be paced or excerpted for it."""
    return drafter_name() != "claude-code"


def _claude_binary() -> str:
    return os.getenv("WORKBENCH_CLAUDE_BIN") or shutil.which("claude") or ""


def drafter_status() -> Dict[str, Any]:
    """For the console: which drafter is configured and whether it can run."""
    name = drafter_name()
    if name == "claude-code":
        binary = _claude_binary()
        return {"name": name, "model": os.getenv("WORKBENCH_CLAUDE_MODEL", "sonnet"), "budget": "large",
                "available": bool(binary), "fallback": "groq, then the local deep rung",
                "note": "" if binary else "no `claude` on PATH: drafts fall back to Groq"}
    return {"name": "groq", "model": os.getenv("GROQ_PLANNER_MODEL", "openai/gpt-oss-120b"), "budget": "small",
            "available": bool(os.getenv("GROQ_API_KEY", "").strip()), "fallback": "the local deep rung",
            "note": "" if os.getenv("GROQ_API_KEY", "").strip() else "GROQ_API_KEY not set: drafts fall back to the local rung"}


def _clean_env() -> Dict[str, str]:
    """The backend is often started from inside a Claude Code session (the operator develops
    it there); a nested `claude` inheriting that session's CLAUDE_*/ANTHROPIC_* variables
    answers "Not logged in" (measured 2026-11-06). The CLI gets a plain environment."""
    return {k: v for k, v in os.environ.items() if not k.upper().startswith(("CLAUDE", "ANTHROPIC"))}


def _claude_code_think(prompt: str) -> Tuple[str, str]:
    """One headless Claude Code call on the operator's subscription: prompt on stdin, text out,
    every tool off (it writes the draft; the Workbench applies and tests), no MCP servers, no
    settings, no saved session, run from a scratch folder rather than the repo."""
    binary = _claude_binary()
    if not binary:
        raise ValueError("drafter 'claude-code' is not installed: no `claude` on PATH "
                         "(npm install -g @anthropic-ai/claude-code, then `claude` once to sign in).")
    model = os.getenv("WORKBENCH_CLAUDE_MODEL", "sonnet")
    argv = [binary, "-p", "--output-format", "text", "--no-session-persistence", "--tools", "",
            "--strict-mcp-config", "--setting-sources", "", "--model", model]
    scratch = Path(tempfile.gettempdir()) / "omega-arc-workbench-drafter"
    scratch.mkdir(parents=True, exist_ok=True)
    try:
        run = subprocess.run(argv, input=prompt, capture_output=True, text=True, encoding="utf-8",
                             errors="replace", cwd=str(scratch), env=_clean_env(),
                             timeout=CLAUDE_CODE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as exc:
        raise ValueError(f"drafter 'claude-code' timed out after {int(CLAUDE_CODE_TIMEOUT_SECONDS)} s") from exc
    except OSError as exc:
        raise ValueError(f"drafter 'claude-code' could not start: {exc}") from exc
    if run.returncode != 0:
        detail = (run.stderr or run.stdout or "").strip().replace("\n", " ")[:200]
        raise ValueError(f"drafter 'claude-code' failed (exit {run.returncode}): {detail}")
    return f"claude-code:{model}", run.stdout


def _frontier(prompt: str) -> Tuple[str, str]:
    """The strongest configured rung drafts. Claude Code first when configured; then the
    frontier planner, whose 429 (the minute's token budget is spent) is waited out once and
    retried; if every provider refuses, the LOCAL deep rung drafts instead (ADR 0027: "the
    local deep rung as fallback"), recorded as such."""
    from services.adapters.deep_think import _frontier_think, _local_think
    from services.network_breaker import record_fetch, require_breaker_on

    require_breaker_on()
    errors: List[str] = []
    if drafter_name() == "claude-code":
        try:
            model, text = _claude_code_think(prompt)
            record_fetch("frontier", model, byte_count=len(text), ok=bool(text),
                         detail=f"workbench draft: prompt {len(prompt)} chars")
            return model, text
        except ValueError as exc:
            errors.append(str(exc))
            record_fetch("frontier", "claude-code", byte_count=0, ok=False, detail=f"workbench draft: {str(exc)[:160]}")
    for attempt in (1, 2):
        try:
            model, text = _frontier_think(prompt)
            record_fetch("frontier", f"groq:{model}", byte_count=len(text), ok=bool(text),
                         detail=f"workbench draft: prompt {len(prompt)} chars")
            return (f"{model} (groq fallback)" if errors else model), text
        except ValueError as exc:
            errors.append(str(exc))
            record_fetch("frontier", "groq", byte_count=0, ok=False, detail=f"workbench draft: {str(exc)[:160]}")
            if "429" in str(exc) and attempt == 1:
                _sleep(RATE_LIMIT_WAIT_SECONDS)
                continue
            break
    refused = " | ".join(e[:200] for e in errors)
    try:
        model, text = _local_think(prompt)
    except ValueError as exc:
        raise WorkbenchError(f"the drafter was refused: {refused}; local fallback failed: {exc}") from exc
    record_fetch("frontier", f"local-fallback:{model}", byte_count=len(text), ok=bool(text),
                 detail=f"workbench draft after frontier refusal: prompt {len(prompt)} chars")
    return f"{model} (local fallback)", text


_MARKER = r"=== (?:EDIT |END\b|CONTINUE\b|SUMMARY\b|NEEDS\b)"
_SUMMARY_RE = re.compile(rf"=== SUMMARY[ \t]*\n(.*?)(?=\n{_MARKER}|\Z)", re.DOTALL)
_NEEDS_RE = re.compile(rf"=== NEEDS[ \t]*\n(.*?)(?=\n{_MARKER}|\Z)", re.DOTALL)
_EDIT_RE = re.compile(rf"=== EDIT[ \t]+(\S+)[ \t]*\n<<<OLD[ \t]*\n(.*?)\n?>>>NEW[ \t]*\n(.*?)(?=\n{_MARKER}|\Z)", re.DOTALL)
_CONTROL_TOKEN = re.compile(r"<\|[^|>]{1,40}\|>")   # leaked model control tokens such as <|message|>
_TERMINATOR_RE = re.compile(r"^=== (END|CONTINUE)\b", re.MULTILINE)


def _parse_draft(text: str) -> Dict[str, Any]:
    """The block format: code travels as plain text between markers, never inside JSON strings.
    Three JSON drafts in a row broke on escaping or ran out of room (2026-11-06). Every marker
    line is a boundary, control tokens are stripped, and the LAST terminator decides whether
    more is coming: a live reply carried "=== END\\n\\n=== CONTINUE<|message|>=== EDIT ..." in the
    middle and the registry edit swallowed two files as text."""
    text = _CONTROL_TOKEN.sub("\n", (text or "").replace("\r\n", "\n"))
    terminators = _TERMINATOR_RE.findall(text)
    if not terminators:
        if "=== " in text:
            raise WorkbenchError("the draft was cut off before its === END line (answer more "
                                 "compactly, or stop at a file boundary with === CONTINUE and "
                                 "deliver the rest when asked)")
        raise WorkbenchError("the drafter did not answer in the block format (=== SUMMARY / === EDIT / === END)")
    more = terminators[-1] == "CONTINUE"
    body = text
    summary = (_SUMMARY_RE.search(body).group(1).strip() if _SUMMARY_RE.search(body) else "")[:600]
    needs_match = _NEEDS_RE.search(body)
    edits = _EDIT_RE.findall(body)
    if needs_match and not edits:
        # The drafter's verdict: this cannot be done until the operator provides something.
        # Not a failure; the proposal shows it as NEEDS FROM YOU (Bill, 2026-11-06).
        return {"summary": summary, "edits": [], "needs": needs_match.group(1).strip()[:1000]}
    if not edits:
        raise WorkbenchError("the draft has no === EDIT blocks")
    clean = []
    for rel_raw, old, new in edits:
        rel = _normalise_path(rel_raw)
        _assert_editable(rel)
        old = old.rstrip("\n")
        new = new.rstrip("\n")
        if old == "" and new and not new.endswith("\n"):
            new += "\n"  # a new file ends with a newline
        clean.append({"file": rel, "old": old, "new": new})
    return {"summary": summary, "edits": clean, "more": more}


def _apply_edits(root: Path, edits: List[Dict[str, str]]) -> List[str]:
    """Apply search/replace edits under `root`. Raises on a miss. Returns the files touched."""
    touched: List[str] = []
    for edit in edits:
        path = root / edit["file"]
        if edit["old"] == "":
            if path.exists():
                raise WorkbenchError(f"{edit['file']}: 'old' is empty but the file exists; "
                                     "give the exact text to replace")
            # A new file anywhere editable: a new adapter under backend/services/adapters/ is
            # the canonical self-extension, and the tests/docs-only rule rejected a complete,
            # valid own-browser draft (2026-11-06). _assert_editable already excluded the gates.
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
    if entry["status"] not in ("proposed", "failed", "tested", "blocked"):
        raise WorkbenchError(f"Proposal is {entry['status']}; DRAFT & TEST runs from proposed, failed, tested or blocked.")
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
    small = getattr(frontier, "small_budget", None)
    if small is None:
        small = small_budget() if frontier is _frontier else True
    plan = gather_plan(worktree, entry, large_budget=not small)
    context = plan.text()
    budget_line = ("keep the whole reply under 2500 tokens: lean code, no decorative comments" if small
                   else "lean code, no decorative comments")
    failures: List[str] = []
    draft: Dict[str, Any] = {}
    touched: List[str] = []
    model = ""
    attempt = 0
    parts = 0           # a big draft may arrive in parts (=== CONTINUE), each within the budget
    continuation = ""
    summary = ""
    last_text = ""
    # Small budget and three or more files to touch: the RUNTIME drives the parts, one file per
    # reply, because a model does not foresee running out of room (three cut-offs in a row on a
    # four-file draft, 2026-11-06), and each reply is shown ONLY that file's code: the four-file
    # context itself was what left no room to answer (three more cut-offs, same night).
    one_per_reply = small and len(plan.targets) >= 3
    max_parts = max(MAX_DRAFT_PARTS, len(plan.targets) + 1)
    while attempt < MAX_DRAFT_ATTEMPTS:
        if not continuation:
            attempt += 1
        pacing = ""
        if one_per_reply:
            remaining = [t for t in plan.targets if t not in touched]
            target, last = remaining[0], len(remaining) == 1
            context = plan.text(only=target)
            pacing = (f"\nTHIS REPLY: {target} ONLY. The change spans {len(plan.targets)} files and is "
                      "drafted one file per reply so each fits your budget: give === SUMMARY and the "
                      f"EDIT block(s) for this one file, then end with {'=== END' if last else '=== CONTINUE'}.\n"
                      + (f"ALREADY DONE: {', '.join(touched)}\n" if touched else "")
                      + (f"STILL TO COME (not now): {', '.join(remaining[1:])}\n" if not last else ""))
        prompt = DRAFT_PROMPT.format(
            title=entry["title"], what=entry["what"], why=entry["why"] or "(not given)",
            needs=(f"THE OPERATOR HAS AGREED TO PROVIDE: {entry['needs_from_operator']}\n"
                   if entry.get("needs_from_operator") else ""),
            context=context, budget_line=budget_line,
            failures=("\nEARLIER ATTEMPTS FAILED TO APPLY, fix this:\n" + "\n".join(failures) + "\n")
            if failures else "") + pacing + continuation
        try:
            model, text = frontier(prompt)
            last_text = text
            draft = _parse_draft(text)
            if draft.get("needs"):
                entry["needs_from_operator"] = draft["needs"]
                entry["draft"] = {"model": model, "summary": draft["summary"], "files": [], "attempts": attempt}
                _mark(entry, "blocked", f"the drafter needs something from the operator: {draft['needs'][:200]}")
                _remove_worktree(proposal_id)
                return _upsert(entry)
            if parts == 0:
                # a fresh attempt: undo any half-applied earlier one (edited files, new files)
                _git("checkout", "--", ".", cwd=worktree, check=False)
                _git("clean", "-fdq", cwd=worktree, check=False)
                summary = draft.get("summary", "")
            for rel in _apply_edits(worktree, draft["edits"]):
                if rel not in touched:
                    touched.append(rel)
            parts += 1
            if one_per_reply:
                # the runtime decides when the draft is complete: every target touched (a reply
                # that ends with === END early, or runs ahead, changes nothing about that)
                if any(t not in touched for t in plan.targets) and parts < max_parts:
                    continue
                break
            if draft.get("more") and parts < MAX_DRAFT_PARTS:
                continuation = ("\nALREADY APPLIED in earlier parts (do not repeat them; continue with the "
                                f"remaining edits, then === END after the last): {', '.join(touched)}\n")
                continue
            break
        except WorkbenchError as exc:
            failures.append(f"attempt {attempt}: {exc}")
            draft, touched, parts, continuation = {}, [], 0, ""
            if not one_per_reply and ("413" in str(exc) or "too large" in str(exc).lower()):
                context = context[: len(context) // 2] + "\n... (context halved: the drafter's request limit)\n"
    if not touched:
        _mark(entry, "failed", "draft could not be applied: " + " | ".join(failures))
        # keep the end of the last raw reply: without it a cut-off cannot be diagnosed
        entry["draft"] = {"model": model, "failures": failures, "last_reply_tail": last_text[-800:]}
        _remove_worktree(proposal_id)
        return _upsert(entry)
    draft["summary"] = summary or draft.get("summary", "")
    draft["parts"] = parts

    def commit_and_check() -> Tuple[List[str], Dict[str, Any]]:
        _git("add", "-A", cwd=worktree)
        _git("-c", "user.name=OMEGA-ARC Workbench", "-c", "user.email=workbench@omega-arc.local",
             "commit", "-q", "--allow-empty", "-m", f"Workbench {proposal_id}: {entry['title']}", cwd=worktree)
        syntax = syntax_check(worktree, touched)
        tests = suite(worktree) if not syntax else {"ok": False, "passed": 0, "failed": 0, "tail": "skipped: syntax errors"}
        return syntax, tests

    syntax, tests = commit_and_check()
    repairs = 0
    # Red suite: the failure goes back to the drafter with the files AS THEY NOW ARE, and its
    # further edits are applied on top (the own-browser draft failed only its own test, which
    # never registered the tool, 2026-11-06). Syntax errors are repaired the same way.
    while not tests["ok"] and repairs < MAX_REPAIR_ROUNDS:
        repairs += 1
        current = gather_plan(worktree, {**entry, "files": touched}, large_budget=not small).text()
        prompt = REPAIR_PROMPT.format(
            title=entry["title"], what=entry["what"],
            failure="\n".join(syntax) if syntax else tests.get("tail", ""),
            context=current)
        try:
            model, text = frontier(prompt)
            fix = _parse_draft(text)
            if fix.get("needs"):
                break  # the drafter says it cannot be fixed without the operator: leave it red
            for rel in _apply_edits(worktree, fix["edits"]):
                if rel not in touched:
                    touched.append(rel)
        except WorkbenchError as exc:
            failures.append(f"repair {repairs}: {exc}")
            break
        syntax, tests = commit_and_check()
    diff = _git("diff", f"{base}..HEAD", cwd=worktree)
    healthy = health(worktree) if tests["ok"] else {"ok": False, "tail": "skipped: tests not green"}
    entry["draft"] = {"model": model, "summary": draft.get("summary", ""), "files": touched,
                      "attempts": len(failures) + 1, "parts": draft.get("parts", 1), "repairs": repairs, "base": base,
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
