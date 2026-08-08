# Lesson 2 — The Memory System

The runtime's long-term memory lives in a single SQLite store. Every memory carries provenance:
where it came from, when it was created, and which conversation produced it. Embeddings for recall
are produced by the local embeddinggemma model, which was retained after a measured bake-off against
challenger embedders.

Memories are organized into rooms. A room is a scope label on a memory, and recall can search
within a single room. A conversation carries its room: memories born in a scoped conversation
inherit that scope automatically. Unscoped memories form the global wing, which stays recallable
from inside every room, while other rooms stay excluded. A lesson is a scoped conversation.

Retrieval ranking blends cosine similarity with a bounded recency term, so when two memories are
near-ties, the newer fact wins. This is the temporal tie-break. Additional lexical and fuzzy
signals exist as tunable knobs but ship disabled, because measurement showed the embedder already
handles exact-term recall.

When a new fact replaces an old one, supersession handles it. A declared change, where the new text
itself announces the replacement, supersedes the old memory automatically. An undeclared collision
becomes a pending candidate that waits for operator review; nothing is hidden from recall without
approval. Superseded memories are never deleted and can always be restored.

Memory quality is measured, not assumed. A recall benchmark scores retrieval with hit at one,
recall at k, and mean reciprocal rank. Every change to retrieval was judged against the benchmark,
and features that showed no measured gain were shipped disabled. A consolidation scan can propose
near-duplicate memories for cleanup, and its proposals also wait for operator review.
