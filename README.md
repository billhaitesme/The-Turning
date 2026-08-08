# OMEGA-ARC

OMEGA-ARC is an Artificial Development Framework for a persistent local intelligence with continuity, memory, reflection, education, self-authored personality, and reviewable growth.

**Current release:** Epoch X / Version 0.3.1
**Active series:** Version 0.3.x
**Active milestone:** Epoch X — Memory (X-B Rooms and Revision released as 0.3.1, tagged `epoch-x-b`)

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
| Core Runtime | `backend/` | Epoch X / 0.3.1 |
| Desktop Bridge Zero | `bridge/bridge-zero/` | Epoch X / 0.3.1 |
| iOS Operator Console | `bridge/bridge-zero-ios/` | Epoch X / 0.3.1 |
| Android Operator Console | `bridge/bridge-zero-android/` | Epoch X / 0.3.1 |
| Shared mobile contract | `bridge/shared/mobile/` | Epoch X / 0.3.1 |

## Epoch IX

Epoch IX-A established authenticated native operator consoles, synchronized conversations, Model Lock visibility, diagnostics, Chronicle, and compatibility gates.

Epoch IX-B is complete and tagged `epoch-ix-a`. It introduced an authoritative RuntimeStore, typed runtime events, an event bus, live telemetry, an Operations Dashboard, and shared design tokens.

Epoch IX-C (Operator Actions) shipped as **0.2.1** (tagged `epoch-ix-c`): an allowlisted operator model selector, an in-app New Conversation control, and operator approvals with on-device biometric confirmation (iOS Face ID, Android BiometricPrompt). It also adds the OMEGA-ARC app icon across iOS, Android, and the desktop browser tab / PWA, and a real Aurebesh utility rendered from a bundled OFL font. It shipped with a documented **Android on-device validation exception** (owed as a follow-up; iOS was validated on hardware). IX-D command-console evolution remains future work.

## Epoch X — Memory

Epoch X begins the memory pillar: durable, scoped, benchmarked long-term memory — the substrate the
future Tutelage/Learning epoch depends on. The X-A foundation shipped as **0.3.0** (tagged
`epoch-x-a`): a recall benchmark (retrieval quality is measured, not assumed), temporal-aware
retrieval (recency tie-breaks, on), hybrid lexical/typo-fuzzy signals (available, off by default —
measurement showed no current gain), write-time supersession (reversible, off pending calibration),
and scoped retrieval ("rooms"; recall by subject — measured hit@1 0.500 → 1.000 on cross-room facts).
Techniques adapted from [MemPalace](https://github.com/MemPalace/mempalace) (MIT) are credited in ADRs
0016–0019.

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
