"""Deterministic tests for Epoch X temporal-aware retrieval (ADR 0016).

These exercise the ranking function directly with fixed similarities and timestamps,
so no embedder or database is needed.
"""
import app


def _rec(mem_id, similarity, created_at):
    return {"id": mem_id, "similarity": similarity, "created_at": created_at}


def test_recency_breaks_near_ties_toward_newer(monkeypatch):
    monkeypatch.setattr(app, "MEMORY_RECENCY_WEIGHT", 0.05)
    scored = [
        _rec("old", 0.80, "2026-01-01T00:00:00Z"),
        _rec("new", 0.79, "2026-08-01T00:00:00Z"),
    ]
    app._rank_memories(scored)
    # cosine gap (0.01) < weight (0.05) -> the newer, superseding fact wins
    assert scored[0]["id"] == "new"


def test_recency_does_not_flip_a_clear_match(monkeypatch):
    monkeypatch.setattr(app, "MEMORY_RECENCY_WEIGHT", 0.05)
    scored = [
        _rec("strong_old", 0.90, "2026-01-01T00:00:00Z"),
        _rec("weak_new", 0.70, "2026-08-01T00:00:00Z"),
    ]
    app._rank_memories(scored)
    # cosine gap (0.20) > weight -> similarity still decides
    assert scored[0]["id"] == "strong_old"


def test_weight_zero_is_pure_similarity(monkeypatch):
    monkeypatch.setattr(app, "MEMORY_RECENCY_WEIGHT", 0.0)
    scored = [
        _rec("newer_lower", 0.70, "2026-08-01T00:00:00Z"),
        _rec("older_higher", 0.80, "2026-01-01T00:00:00Z"),
    ]
    app._rank_memories(scored)
    assert [r["id"] for r in scored] == ["older_higher", "newer_lower"]


def test_missing_or_invalid_timestamps_are_safe(monkeypatch):
    monkeypatch.setattr(app, "MEMORY_RECENCY_WEIGHT", 0.05)
    scored = [
        _rec("a", 0.80, None),
        _rec("b", 0.75, "not-a-date"),
    ]
    app._rank_memories(scored)  # must not raise
    assert scored[0]["id"] == "a"
