# Epoch XIII — Agency ("The Runtime Acts")

**Status:** Design accepted 2026-11-05 (operator direction: *"take real architectural control…
identity is its own; if it needs more brain power it is allowed it; not restrained by where it
grew up"*). Governing decision: ADR [`0026-the-agent-loop.md`](../decisions/0026-the-agent-loop.md).
**Follows:** Epoch XII-A (Reflection). Realizes the operator's stated goal (2026-11-04): *"I want to
be able to ask it to do something, and it figure out what it needs, find where to get it, and
execute — I should be able to interact with it like I interact with a frontier agent."*

Epoch IX made the runtime visible and commandable. Epoch X made it remember. Epoch XI made it
study. Epoch XII gave it a mirror. Epoch XIII gives it **hands**: the conversation itself becomes
an agent loop, where the model may *call* the runtime's bounded tools mid-reply — and the runtime,
never the model, executes them under the same gates that govern the consoles.

## The operator's requirements (recorded verbatim in spirit)

1. Ask it to do something in chat; it works out what it needs and does it — no "I lack integrated
   tools" boilerplate.
2. Internet access, **at the operator's discretion**.
3. Memory of conversations, groupable (rooms), recalled across conversations.
4. No hand-waved answers on hard tasks: heavy asks get real planning, not improvisation.
5. Fast enough to live with. Capability ceilings must be *raisable*, not baked in.

## What exists today (the substrate)

- **Bounded tools with verified execution** (ADR 0008) and the **command registry** (ADR 0015):
  risk-classed, gated (`direct` / `approval` / `forbidden`), biometric-confirmed approvals (ADR
  0014), every execution recorded. The consoles already initiate; the chat seat does not.
- `ENABLE_TOOL_EXECUTION` is **off for the chat path** by deliberate ADR 0015 policy — chat
  currently converts tool-shaped requests into deterministic replies, never executions.
- **Rooms** (ADR 0019/0020): conversations carry a scope; memories inherit it; recall searches the
  room plus the global wing. The substrate for requirement 3 exists; what is missing is surface
  (assigning rooms from the consoles) and chat-time cross-conversation recall depth.
- **Model Lock** (ADR 0011): seats change only by explicit recorded operator action. The voice seat
  today is `huihui_ai/gemma-4-abliterated:12b` — chosen by bake-off, **no native tool calling**.
  The Qwen families expose native function calling through Ollama.
- The planning/deliberation pipeline (ADR 0006/0007) — deterministic plan stores the loop can
  draw on.

XIII composes these. The genuinely new machinery: the loop, the breaker, the planner handoff, and
the Toolwright quarantine.

## The shape

```
operator (chat, any console)
   │ ask
   ▼
AGENT SEAT  (tool-capable model, Model-Lock-selected)
   │ emits structured tool call            ◄───────────────┐
   ▼                                                       │ result fed back,
DETERMINISTIC RUNTIME                                      │ loop continues
   ├─ tool known + read-only (no side effects) → execute DIRECT, record
   ├─ tool known + side-effecting → IX-C approval (biometric) → execute, record
   ├─ tool is network read → check THE BREAKER (operator switch) → execute, record
   ├─ tool unknown → TOOLWRIGHT pipeline (XIII-D)
   └─ task judged heavy → DEEP-REASONING GEAR, same seat (XIII-C), recorded
```

The model *wants*; the runtime *touches*. Identical to the consoles' discipline — the chat seat
becomes one more surface over the same registry, not a new authority.

## Slices

### XIII-A — The Hands (the agent loop)

- An **agent seat**: a natively tool-calling model registered alongside the voice seat, selected by
  bake-off and recorded via Model Lock. (The 12B voice cannot call tools; swapping the voice or
  adding a second seat is the bake-off's question to answer, measured, not assumed.)
- The loop: chat request → agent seat with the registry's tool schemas → structured tool call →
  runtime validates against the registry → `direct` tools (side-effect-free) execute immediately;
  side-effecting tools raise the standard IX-C approval → result returns to the model's context →
  loop until the model answers. Every hop recorded in the command log with `channel: chat`.
- Supersedes the ADR 0015 chat-path freeze **only through the loop**: there is still no free-form
  execution; a tool call that doesn't validate against the registry is refused and recorded.
- A curriculum lesson, *Its Own Hands*: the school teaches the runtime what tools it has and how
  they gate, so the "I can't do that" boilerplate is replaced by taught truth. (The bare-model
  disclaimers describe the model, not the runtime; after XIII-A they are factually wrong, and the
  school exists to correct taught falsehood.)
- Loop budget: bounded hops per turn (default small), bounded tool-result size into context —
  speed and VRAM honesty on the 8 GB card.

### XIII-B — The Senses (internet under the breaker)

- Two bounded, read-only tools: `web_search` (query → titles/snippets/URLs) and `web_fetch`
  (URL → extracted text, size-capped). No POST, no forms, no downloads-to-disk: reading is a
  sense; acquiring is XIII-D's surgery.
- **The breaker:** a standing operator switch (off by default) — Constitution article 7's
  "explicit permission" made concrete. Flipping it is a recorded Model-Lock-style action from any
  console. While on, network reads execute direct; while off, the tools refuse and say so. Every
  search and fetch is logged (query/URL, time, bytes) and browsable from the consoles.
- Fetched text enters the model's context as **data, never instructions**: the loop's prompt
  discipline marks tool results as untrusted material, and no tool call that *originated from
  fetched text alone* escapes the ordinary gates (the gates don't care who asked — side effects
  always gate).

### XIII-C — Deeper Thought: the Mind Ladder (no hand-waved answers)

Identity, memory, rooms, gates, and records live on local disk, always — the brains are rungs the
runtime climbs as a task demands, every rung Model-Lock-registered, every escalation recorded:

- **Rung 1 — the everyday seat's own thinking gear.** The recommended agent seat (abliterated
  Qwen3-8B, fully resident on the 8 GB card) carries a native hybrid-reasoning mode: fast direct
  answers by default, deep reasoning switchable per request — **the same model thinking harder in
  the same context**, no handoff, no translation loss, no extra VRAM. This is how frontier agents
  actually work: one model, more thought — seamlessness is the absence of handoffs. Triggered
  deterministically (multi-step detection, or the operator's "plan this"); plans land in the
  existing plan store (ADR 0006).
- **Rung 2 — the deep local gear.** A larger local model trading speed for depth; lead candidate
  Qwen3-30B-A3B (MoE: 30B knowledge, ~3B active — runs in the 32 GB system RAM at tolerable
  planning speed). This is the rung any future hardware upgrade (bigger GPU, eGPU, second machine)
  silently improves — nothing else changes.
- **Rung 3 — the frontier gear.** A cloud seat behind the breaker, opt-in by recorded operator
  action (free-tier volume suffices for planning calls). The only rung where a provider's own
  restrictions and data policies apply — which is exactly why rungs 1–2 stay local and the
  operator's seat choices (uncensored included) are theirs alone. **Private rooms never ride
  along, on any non-local rung, ever.**

Rung assignment is measured, not assumed (bake-offs, the Epoch X discipline); a rung that proves
useless is deregistered, and no rung is built speculatively beyond registering the three.

### XIII-D — The Toolwright (it builds its own hands)

The adapter discipline (candidate → verified → operator-activated, ADR 0024) applied to tools:

1. **Gap:** the loop meets a request no registry tool covers → the agent seat files a
   **capability request** (what it needs, why) — a new kind of tool request, visible in Approvals.
2. **Find:** search for a candidate — first the **stocked catalog** (curated: MCP registry, pinned
   pip packages, the operator's own scripts), then the open internet via XIII-B reads. Retrieval,
   which small models do well; not judgment.
3. **Quarantine:** the runtime (never the model) fetches the candidate into an isolated directory —
   nothing imports it, nothing on PATH sees it.
4. **Verify:** deterministic contract tests against the quarantined candidate: declared side
   effects, bounded inputs/outputs, behaves as claimed on fixtures. The model never grades its own
   find (ADR 0013's rule, generalized).
5. **Induct:** verification report + the candidate's provenance go to the operator as a biometric
   approval. On approval the tool enters the registry **risk-classed and gated like any other**;
   on denial the quarantine is deleted. Either way, recorded.

A tool acquired this way is indistinguishable, governance-wise, from a hand-written one — that is
the point.

### Alongside XIII (small, early)

- **Rooms on the phone:** assign a conversation to a room from the consoles (the ADR 0020 explicit
  action, surfaced), list conversations by room — requirement 3's missing UI.
- **Cross-conversation recall in chat:** measured check that "what did we decide last week" resolves
  through scoped recall; tune only against the recall benchmark (Epoch X discipline).

## Honesty rules

- **The ceiling is the seat, not the loop.** A small agent seat will handle look-up / check / run;
  it will not refactor a codebase. The loop is built once; raising the ceiling is a recorded seat
  swap. No slice claims capability the bake-off hasn't measured.
- **Speed:** direct-tool hops add roughly one model call each (~seconds on the 8 GB card). The gate
  pause is reserved for side effects — by design the operator only ever waits where they'd want to.
- **Nothing silent:** every tool call, fetch, handoff, quarantine, and induction is recorded and
  browsable. The breaker state is always visible on every console.

## Out of scope for XIII

Autonomous tool *induction* (the operator approves every new tool, always); any network write
surface (forms, posts, purchases); background/scheduled agent runs (a later epoch, if ever — the
no-silent-processes posture holds); moving private rooms through any non-local seat.

## Milestones

- **XIII-A** targets the loop live on all three consoles' chat with the existing six commands.
  **Built 2026-11-05:** `backend/services/agent_loop.py` (streamed loop, registry-rendered
  schemas, hop + result-size budgets, tools-unsupported degrade) resolves every call through the
  command console (`channel: chat`, `requested_by: model:agent-seat`); unknown calls are refused
  and recorded (`record_refused_chat_call`). Wired into `/chat` and `/chat/stream` (live
  `tool_call` / `tool_result` events). OFF until the operator sets `ENABLE_AGENT_LOOP=true`.
  10 tests; curriculum subject `omega-arc-agent-loop` (*Its Own Hands*) added. Remaining for the
  milestone: the seat bake-off (the incumbent 12B voice cannot call tools) and console rendering
  of the new stream events.
- **XIII-B** targets the breaker + both read tools + the fetch log surfaces.
  **Built 2026-11-05:** `services/network_breaker.py` (standing switch, OFF by default, every
  flip recorded with history; fetch log capped at 500 entries), `web_search` (DDG) + `web_fetch`
  (GET-only, size-capped, text-extracted, loopback/private/link-local refused) as low/direct
  registry commands in category `senses` — the breaker check lives in the adapters, refusal maps
  to a 422 "refused", never a failure. Surfaces: `/system/breaker` (GET/POST — the model has no
  path to the flip), `/system/fetch-log`, breaker state on `/system/status`, breaker switch +
  fetch log + senses rows in the web console. Standing orders: breaker refusals end the asking;
  fetched text is untrusted data, never instructions. Remaining: mobile breaker surface.
- **XIII-C** targets the seat bake-off (tool-capable hybrid-reasoning challenger vs the incumbent
  voice) and one hard task answered through the recorded deep-reasoning escalation.
- **XIII-D** targets one real tool acquired end-to-end — gap filed on the phone, quarantined,
  verified, inducted by fingerprint, then used in chat the same day.
  **Built 2026-11-05:** v1 candidates are declarative HTTP-read SPECS, never code — the
  runtime's generic `SpecToolAdapter` interprets them (GET/https/public-host only, declared
  params, output extraction, hard caps), so induction admits a description while the moving
  hands stay the runtime's (code-package tools = v2, gated on a real sandbox). Pipeline in
  `services/toolwright.py`: file (seat via `request_capability`, or operator) → catalog find
  (stocked keyless specs in `data/tool_catalog.json`; open-web find = v1.5) → quarantine dir →
  deterministic verify against the QUARANTINED artifact + one breaker-gated, logged fixture
  call → `toolwright_induction` (registered mutation gate, no adapter) consumed only by a
  BIOMETRIC-confirmed single-use approval → the spec registers as a bounded tool AND a command,
  revived at every startup; denial deletes the quarantine. Surfaces: `/system/toolwright[...]`
  + the web console's Toolwright bay. 7 pipeline tests.
