# Persistence

## Overview

OMEGA-ARC uses persistence to make state durable across turns and across restarts. The design deliberately separates different kinds of state so that they can evolve independently.

## Persistence Files

### backend/data/goals.json
Ownership: goals subsystem

Purpose: stores goal definitions, statuses, progress, and metadata.

### backend/data/knowledge_graph.json
Ownership: knowledge subsystem

Purpose: stores nodes and edges representing structured knowledge.

### backend/data/evidence.json
Ownership: evidence engine

Purpose: stores evidence records and their metadata.

### backend/data/constitution.json
Ownership: constitutional principles

Purpose: stores the system’s stable operating principles.

### backend/data/personality.json
Ownership: personality subsystem

Purpose: stores personality configuration and style definitions.

### backend/omega_arc.db
Ownership: runtime application state

Purpose: stores runtime data and auxiliary application state.

## Ownership Model

Each subsystem owns its own persistence shape. The application layer should not mutate another subsystem’s data without going through the relevant service.

## Future Direction

As the system matures, persistence will likely expand into specialized stores for:

- long-term memory
- multimodal evidence
- interaction logs
- environment and hardware observations
