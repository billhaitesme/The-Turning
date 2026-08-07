# Bridge Zero Runtime Behavior Architecture

This document defines behavior layers for Bridge Zero so visual, interaction, and audio changes remain coherent over time.

## Layer Stack

1. Power Layer
2. Environment Layer
3. Telemetry Layer
4. Cognitive Layer
5. Operations Layer
6. Presentation Layer
7. Audio Layer

## 1) Power Layer

Purpose: keep the bridge visibly alive independent of backend data.

Responsibilities:
- Always-on ambient power signatures (background drift, low lamp life)
- Boot progression and recovery posture
- Mechanical readiness cues

Rules:
- Power must never depend on telemetry availability.
- No-telemetry state is not equivalent to no-power state.

## 2) Environment Layer

Purpose: define operating context and global mode behavior.

Responsibilities:
- Surface mode behavior (steady/surge/lock)
- Silence posture (reduced motion, stabilized indicators)
- Global motion-rate shaping

Rules:
- Silence is meaningful, not dead.
- Mode changes are mechanical and intentional.

## 3) Telemetry Layer

Purpose: represent backend and runtime health truthfully.

Responsibilities:
- Poll health, endpoint sync, last poll, degraded/error states
- Alarm generation and acknowledgement state
- Self-check heartbeat pulse (periodic SYNC OK)

Rules:
- Degraded telemetry should remain readable and calm.
- Telemetry activity may wake cognitive/operations layers.

## 4) Cognitive Layer

Purpose: show cognition as staged flow, not a single spinner.

Responsibilities:
- Cognitive bus pulse traversal: Identity -> Evidence -> Reasoning -> Planning -> Tools -> Deliberation
- Think/speak pipeline stages:
  - RECEIVING
  - CLASSIFYING
  - IDENTITY
  - MEMORY
  - REASONING
  - PLANNING
  - COMPOSING
  - TRANSMITTING
- Subsystem personality traits:
  - Identity: stable
  - Evidence: short amber flashes
  - Reasoning: oscillation
  - Planning: progress-oriented
  - Tools: discrete pulses
  - Deliberation: slow violet breathing

Rules:
- Cognitive pulse should complete in roughly 300-500ms.
- Behavior signatures should be recognizable even without labels.

## 5) Operations Layer

Purpose: communicate current mission-state and execution outcomes.

Responsibilities:
- Plan progress, blockers, approvals, tool execution timeline
- Chronicle entries as durable records

Rules:
- Chronicle entries should arrive, type, then lock.
- Historical entries should feel permanent once written.

## 6) Presentation Layer

Purpose: map behavior state to visual mechanics.

Responsibilities:
- Mechanical transition order:
  1. panel power
  2. relay click feel
  3. lamp readiness
  4. display wake
  5. telemetry motion
- Panel cadence by load band and pattern state

Rules:
- Avoid generic opacity fades as primary state language.
- Favor intentional staged transitions.

## 7) Audio Layer

Purpose: provide consistent event-class sound language.

Event classes:
- Acknowledgement: soft click
- Navigation: mechanical switch click
- Verified observation: short confirmation tone
- Alarm: sharp chirp class
- Completion: ascending confirmation
- Chronicle entry: gentle chime

Rules:
- Keep cues short and subtle.
- Audio must be gesture-primed and user-toggle controlled.

## Implementation Notes

Current implementation anchors:
- Behavioral logic: frontend/src/App.jsx
- Visual behavior and animation: frontend/src/App.css

Change policy:
- Add behavior by layer first, then map to visuals/audio.
- Avoid introducing one-off effects that bypass layer ownership.
