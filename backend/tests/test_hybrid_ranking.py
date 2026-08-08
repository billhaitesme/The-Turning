"""Deterministic tests for Epoch X hybrid (lexical + vector) retrieval (ADR 0017).

Exercise the ranking function and lexical scorer directly with fixed values, so no
embedder or database is needed.
"""
import app


def _rec(mem_id, similarity, lexical=0.0, created_at="2026-01-01T00:00:00Z"):
    return {"id": mem_id, "similarity": similarity, "lexical": lexical, "created_at": created_at}


def test_lexical_breaks_vector_near_tie(monkeypatch):
    monkeypatch.setattr(app, "MEMORY_LEXICAL_WEIGHT", 0.15)
    monkeypatch.setattr(app, "MEMORY_RECENCY_WEIGHT", 0.0)  # isolate the lexical signal
    scored = [
        _rec("twin_wrong", 0.80, lexical=0.5),
        _rec("exact_right", 0.79, lexical=1.0),
    ]
    app._rank_memories(scored)
    # cosine gap (0.01) < 0.15*(1.0-0.5)=0.075 -> the exact-term match wins
    assert scored[0]["id"] == "exact_right"


def test_lexical_does_not_override_a_clear_cosine_winner(monkeypatch):
    monkeypatch.setattr(app, "MEMORY_LEXICAL_WEIGHT", 0.15)
    monkeypatch.setattr(app, "MEMORY_RECENCY_WEIGHT", 0.0)
    scored = [
        _rec("strong", 0.95, lexical=0.0),
        _rec("weak_lex", 0.70, lexical=1.0),
    ]
    app._rank_memories(scored)
    assert scored[0]["id"] == "strong"  # 0.95 > 0.70 + 0.15


def test_lexical_weight_zero_ignores_lexical(monkeypatch):
    monkeypatch.setattr(app, "MEMORY_LEXICAL_WEIGHT", 0.0)
    monkeypatch.setattr(app, "MEMORY_RECENCY_WEIGHT", 0.0)
    scored = [
        _rec("high_lex_low_sim", 0.70, lexical=1.0),
        _rec("low_lex_high_sim", 0.80, lexical=0.0),
    ]
    app._rank_memories(scored)
    assert [r["id"] for r in scored] == ["low_lex_high_sim", "high_lex_low_sim"]


def test_lexical_score_is_query_term_coverage():
    q = app._tokenize("What does ticket OMEGA-419 track?")
    right = app._lexical_score(q, {"summary_text": "Ticket OMEGA-419 tracks the export bug.", "source_text": ""})
    wrong = app._lexical_score(q, {"summary_text": "Ticket OMEGA-412 tracks the login bug.", "source_text": ""})
    assert right > wrong          # the "419" token is the discriminator
    assert 0.0 <= wrong < right <= 1.0


def test_stopwords_do_not_count_as_matches():
    q = app._tokenize("what is the current model")   # -> {"model"} after stopword/So removal
    assert "the" not in q and "is" not in q and "current" not in q
    assert "model" in q


def test_fuzzy_score_tolerates_a_typo():
    q = app._char_trigrams("prjoect orion")  # "project orion" with a transposition
    right = app._fuzzy_score(q, {"summary_text": "Project Orion is written in Rust.", "source_text": ""})
    wrong = app._fuzzy_score(q, {"summary_text": "Project Nova is written in Go.", "source_text": ""})
    # despite the typo, the correct memory still scores higher (most trigrams survive)
    assert 0.0 <= wrong < right <= 1.0


def test_fuzzy_breaks_near_tie_under_typo(monkeypatch):
    monkeypatch.setattr(app, "MEMORY_FUZZY_WEIGHT", 0.2)
    monkeypatch.setattr(app, "MEMORY_LEXICAL_WEIGHT", 0.0)
    monkeypatch.setattr(app, "MEMORY_RECENCY_WEIGHT", 0.0)
    scored = [
        {"id": "wrong", "similarity": 0.80, "fuzzy": 0.4, "created_at": "2026-01-01T00:00:00Z"},
        {"id": "right", "similarity": 0.79, "fuzzy": 0.9, "created_at": "2026-01-01T00:00:00Z"},
    ]
    app._rank_memories(scored)
    assert scored[0]["id"] == "right"


def test_fuzzy_weight_zero_ignores_fuzzy(monkeypatch):
    monkeypatch.setattr(app, "MEMORY_FUZZY_WEIGHT", 0.0)
    monkeypatch.setattr(app, "MEMORY_LEXICAL_WEIGHT", 0.0)
    monkeypatch.setattr(app, "MEMORY_RECENCY_WEIGHT", 0.0)
    scored = [
        {"id": "high_fuzzy_low_sim", "similarity": 0.70, "fuzzy": 1.0, "created_at": "2026-01-01T00:00:00Z"},
        {"id": "low_fuzzy_high_sim", "similarity": 0.80, "fuzzy": 0.0, "created_at": "2026-01-01T00:00:00Z"},
    ]
    app._rank_memories(scored)
    assert [r["id"] for r in scored] == ["low_fuzzy_high_sim", "high_fuzzy_low_sim"]
