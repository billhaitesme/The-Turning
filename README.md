# OMEGA-ARC

OMEGA-ARC is an Artificial Development Framework for a persistent local intelligence with continuity, memory, reflection, education, self-authored personality, and reviewable growth.

**Current release:** Epoch XII / Version 0.5.0
**Active series:** Version 0.5.x
**Active milestone:** Epoch XII — Reflection (XII-A The Mirror released as 0.5.0, tagged `epoch-xii-a`)

Bridge Zero is the operator surface for the deterministic Core Runtime. Desktop Bridge Zero remains Mission Control; the native iOS and Android applications are synchronized operator consoles for the same runtime.

## Core principles

- Continuity over replacement
- Coherence over spectacle
- Truth over appearance
- Local-first operation where practical
- Replaceable subsystems
- Human-readable records
- Reversible changes
- Identity without repetitive ceremony

Nothing meaningful should change without leaving a history.

## Components

| Component | Location | Release identity |
|---|---|---|
| Core Runtime | `backend/` | Epoch XII / 0.5.0 |
| Desktop Bridge Zero | `bridge/bridge-zero/` | Epoch XII / 0.5.0 |
| iOS Operator Console | `bridge/bridge-zero-ios/` | Epoch XII / 0.5.0 |
| Android Operator Console | `bridge/bridge-zero-android/` | Epoch XII / 0.5.0 |
| Shared mobile contract | `bridge/shared/mobile/` | Epoch XII / 0.5.0 |

## Epoch IX

Epoch IX-A established authenticated native operator consoles, synchronized conversations, Model Lock visibility, diagnostics, Chronicle, and compatibility gates.

Epoch IX-B is complete and tagged `epoch-ix-a`. It introduced an authoritative RuntimeStore, typed runtime events, an event bus, live telemetry, an Operations Dashboard, and shared design tokens.

Epoch IX-C (Operator Actions) shipped as **0.2.1** (tagged `epoch-ix-c`): an allowlisted operator model selector, an in-app New Conversation control, and operator approvals with on-device biometric confirmation (iOS Face ID, Android BiometricPrompt). It also adds the OMEGA-ARC app icon across iOS, Android, and the desktop browser tab / PWA, and a real Aurebesh utility rendered from a bundled OFL font. It shipped with a documented **Android on-device validation exception** (owed as a follow-up; iOS was validated on hardware). IX-D command-console evolution remains future work.

## Epoch X — Memory

Epoch X delivers the memory pillar: durable, scoped, benchmarked long-term memory — the substrate the
future Tutelage/Learning epoch depends on. Techniques adapted from
[MemPalace](https://github.com/MemPalace/mempalace) (MIT) are credited in ADRs 0016–0023.

- **X-A — Memory Foundation (0.3.0, `epoch-x-a`):** a recall benchmark (retrieval quality is
  measured, not assumed), temporal-aware retrieval (recency tie-breaks, on), hybrid lexical/typo-fuzzy
  signals (available, off — measurement showed no current gain), reversible supersession flags, and
  scoped retrieval ("rooms"; measured hit@1 0.500 → 1.000 on cross-room facts).
- **X-B — Rooms and Revision (0.3.1, `epoch-x-b`):** scope assignment — the conversation carries the
  room, explicitly, and recall searches the room plus the global wing; robust supersession upgraded
  per ADR 0021 — auto only on a *declared* change, undeclared collisions queue for operator review
  (off by default with calibrated two-tier floors); an embedder bake-off retained `embeddinggemma`.
- **X-C — Review and Consolidation (0.3.2, `epoch-x-c`):** a memory review surface (browse rooms,
  re-room, restore — audited, never deleted) and an operator-invoked consolidation scan that proposes
  near-duplicate residue into the same review queue.

## Start here
- [Current project status](PROJECT_STATUS.md)
- [Architecture decision index](ARCHITECTURE_DECISIONS.md)
- [IX-B validation report](docs/governance/IX_B_VALIDATION_REPORT.md)
- [Engineering contribution guide](docs/governance/CONTRIBUTING.md)
- [Versioning authority](docs/architecture/versioning.md)
- [Bridge Zero Mobile architecture](docs/architecture/bridge-zero-mobile.md)
- [Architecture](ARCHITECTURE.md)
- [Roadmap](ROADMAP.md)
- [Changelog](CHANGELOG.md)

## Epoch XI — Tutelage

The runtime studies. Epoch XI's first milestone shipped as **0.4.0** (tagged `epoch-xi-a`): an
operator-authored curriculum whose subjects are memory rooms; a deterministic study cycle (ingest
lesson sources into the room with per-chunk provenance → pre/post recall test → the study-seat model
answers the quiz from its own notes, graded against operator-authored keys — the model never grades
itself); prerequisite gating; idempotent re-runs; auditable cycle records. The first real lessons ran
2026-08-08 — the seed subject is OMEGA-ARC's own architecture (anatomy is taught; identity is
authored: what the runtime is *made of* is curriculum, who it *is* remains its own to determine).
See ADR 0013 and [`docs/architecture/epoch-xi-tutelage.md`](docs/architecture/epoch-xi-tutelage.md).
XI-B added retention (cumulative quizzes, interference gating, spaced re-quizzes; 0.4.1) and XI-C
the consolidation gate (key-verified distillation behind single-use operator approval, a versioned
adapter registry; 0.4.2) — closed out for real when the first tutored adapter was trained, served,
and answered its quiz **5/5 verbatim from bare weights**, then activated in the registry.

## Epoch XII — Reflection

The runtime considers itself. XII-A "The Mirror" shipped as **0.5.0** (tagged `epoch-xii-a`): a
reserved memory scope, `self-reflection`, written only by the reflection pipeline — the operator
reviews and may supersede, but never authors there (the inverse of the tutelage discipline, same
governance spine). A reflection cycle builds a deterministic digest of the runtime's actual recorded
activity (study cycles, memory events, gated consolidation runs, prior reflections), and only then
does the voice model compose a short first-person observation grounded in that digest, which is
stored beside it as provenance — *no ungrounded self-narrative*. Identity consolidation, when it
eventually happens, draws only from this room and remains double-gated. See ADR 0025 and
[`docs/architecture/epoch-xii-reflection.md`](docs/architecture/epoch-xii-reflection.md).

## Models

The default conversational model is **`huihui_ai/gemma-4-abliterated:12b`** (uncensored, ~7.6 GB,
Apache 2.0): an 11.9B Gemma-4 with 131K context and vision/tools/audio capabilities, chosen by the
operator after a hands-on voice trial and a perfect 12/12 on the tutelage comprehension quizzes —
the first candidate to run the table. Its HF original (`huihui-ai/Huihui-gemma-4-12B-it-abliterated`)
is publisher-matched, which keeps the future consolidation path traceable. It is thinking-capable:
raw `ollama run` shows reasoning text, but in-app the runtime disables the hidden reasoning phase
deterministically (`OLLAMA_THINK=false`, the default; leaked `<think>` blocks are stripped anyway).

The operator can switch models at any time from the console selector (Model-Lock-recorded); reasons
you might:

| Selectable model | Why you would switch to it |
|---|---|
| `mo-shakib/gemma4-e4b-uncensored` | The previous default voice — lighter effective-4B compute; a familiar fallback. |
| `huihui_ai/gemma-4-abliterated:e4b` | Same family as the default, smaller effective compute; 11/12 on the quizzes. |
| `richardyoung/llama-3.1-8b-instruct-abliterated` | Smaller download (~5 GB) and lighter in RAM; a strong uncensored 8B if disk/bandwidth are tight. |
| `dolphin-mixtral:8x7b` | The largest and most capable of the set (26 GB MoE) — needs far more VRAM than a laptop GPU, so most of it spills to CPU and responses crawl. Worth it only with serious hardware. |
| `llama2-uncensored:7b` | Legacy lightweight fallback; fastest to load, older generation — compatibility more than quality. |
| `llama3.1:8b` | The one *aligned* model in the list — pick it if you want refusal-style safety behavior (e.g., demos to others). Note this departs from the project's uncensored default posture. |

Note on hardware: OMEGA-ARC never chooses CPU vs GPU — Ollama auto-offloads each model to the GPU
up to available VRAM and spills the remainder to CPU. On an 8 GB GPU, models up to ~7 GB run fully
GPU-accelerated; larger ones degrade gracefully toward CPU speed.

Auxiliary roles: `embeddinggemma` (memory embeddings — retained after a measured bake-off),
`qwen3-vl` (vision default, currently dormant), `gemma3:1b` (router, disabled under Model Lock),
`llama3.1:8b` (fallback). Model changes only ever happen by explicit operator action (ADR IX-001).

## License

Dual-licensed under either the [MIT License](LICENSE-MIT) or the
[Apache License 2.0](LICENSE-APACHE), at your option (`MIT OR Apache-2.0`). Unless you explicitly
state otherwise, contributions you submit are dual-licensed the same way. The bundled Aurebesh font
retains its own [SIL OFL 1.1 license](bridge/shared/fonts/LICENSE.md).
