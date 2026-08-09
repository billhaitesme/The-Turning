# Lesson 3 — The Memory Vault (SQLite)

The runtime's long-term memory lives in a single SQLite database file named omega_arc.db, on this
machine. The deterministic runtime is the only writer; the language model never touches the store
directly.

Each memory carries a score, a scope, and provenance. The scope is the memory's room: subjects of
study are rooms, and recall searches the current room plus the global wing. A reserved room named
self-reflection holds the runtime's observations about itself, and only the reflection pipeline
may write there.

Memories are never deleted. When a fact is replaced, the old memory receives a reversible
superseded flag and can always be restored. Every correction — a re-room, a restore, a
supersession — is recorded in the memory_events audit log, so the history of the memory system is
itself remembered.

Recall is measured, not assumed. Retrieval quality is tracked by a recall benchmark, and the
embeddings that power similarity search are produced locally by the embeddinggemma model. When
the embedder changes, calibrated thresholds must be re-measured.
