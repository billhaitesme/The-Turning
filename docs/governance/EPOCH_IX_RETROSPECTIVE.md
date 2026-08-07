# Epoch IX-B Retrospective — Independent Review to Hardened Candidate

**Date:** 2026-07-24

This records the arc from the independent engineering review to the current state, so a future
steward can see what changed and why.

## Where we started

An independent review of the RC1 working tree concluded **NO — not eligible for checkpoint**, with
six blocking issues:

1. iOS client did not compile (unbalanced parenthesis in `APIClient.swift`).
2. No checkpoint commit and no `epoch-ix-a` tag; the entire mobile and shared tree was untracked.
3. Android resource/concurrency defects: unclosed OkHttp responses (leak per reconnect),
   non-atomic `StateFlow` read-modify-write, uncancellable blocking reads.
4. Full backend suite unverified (only 16 of 340 tests confirmed).
5. Physical-device validation gate not met on either platform.
6. Design-system parity failed across desktop / iOS / Android.

The architecture itself passed: Model Lock, deterministic runtime, and the operator-console model
were implemented as designed. The problem was release engineering, not concept.

## Where we are now

| # | Blocker | Disposition | Evidence |
|---|---|---|---|
| 1 | iOS compile | **Resolved + validated** | Fixed; CI builds green on macos-14 / Xcode 16 / iOS 17 SDK; on-device run |
| 2 | Checkpoint / tracking | **Committed, not yet tagged** | `release/epoch-ix-0.2.0`, reviewed logical commits, pushed; sources tracked. `epoch-ix-a` intentionally withheld |
| 3 | Android defects | **Resolved + validated** | `use{}` close, atomic `update{}`, `runInterruptible`; clean `assembleDebug` + unit tests; 8/8 device checklist |
| 4 | Backend suite | **Resolved** | 344 passing, hermetic, ~150s |
| 5 | Physical-device gate | **Android complete; iOS partial** | Android 8/8 on moto g15 power / Android 15. iOS: live SSE + streaming validated on a physical iPhone; appearance/accessibility tail not yet recorded |
| 6 | Design-token parity | **Foundation aligned** | iOS colors/typography/separator aligned; Android status badge + typography added; Android device-verified (dark, scaling) |

## Defects found *because* we validated on hardware

None of these were caught by static review; all surfaced by running on real devices, and all are
fixed with tests where applicable:

- **iOS live SSE was dead** — `URLSession.AsyncBytes.lines` dropped the blank-line SSE delimiter,
  so neither telemetry nor streaming ever finalized an event. Fixed by manual byte splitting.
- **Evidence/deliberation diagnostics were wrong** — evidence checked a non-existent key (could
  never report healthy); deliberation used `bool(store)` (always healthy). Fixed + regression tests.
- **`launch_backend.py` ignored the `.env` bind host** — read `OMEGA_BIND_HOST` before loading
  `.env`, silently staying on loopback. This was the practical form of B-03 / TD-C04. Fixed.

## What is still open before an `epoch-ix-a` tag

1. iOS physical-device checklist tail (appearance, dynamic type, VoiceOver) — or explicit
   acceptance by the release owner.
2. The `backend/data/` runtime records need a fixture-or-ignore decision (still uncommitted).
3. Create the annotated `epoch-ix-a` tag on the reviewed `release/epoch-ix-0.2.0` checkpoint.

## IX-C work already underway

Operator model selection was pulled forward onto `feature/epoch-ix-c-model-selector`: an
allowlisted, Model-Lock-recorded model selector across backend, desktop, Android, and iOS. This
is IX-C "Operator Actions" scope, deliberately kept off the IX-B checkpoint branch. The in-app
"new conversation" control remains deferred IX-C work.

## Net assessment

The candidate moved from "not eligible" to a hardened state with nearly every blocker resolved and
verified — much of it on real hardware, which also surfaced three genuine bugs static analysis
missed. The remaining work is a short, well-defined list, not open-ended.
