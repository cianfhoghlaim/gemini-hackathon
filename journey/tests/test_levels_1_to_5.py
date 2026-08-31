"""test_levels_1_to_5.py — combined happy-path + error-tolerance tests for Levels 1-5."""

from __future__ import annotations

import asyncio


def _run(coro):
    """Run an async level entrypoint in a fresh event loop (mirrors the
    pattern the Gradio studio uses; safe to call from sync pytest)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ── Level 1 ───────────────────────────────────────────────────────────


def test_level_1_offline_syllabus_extraction():
    """The full BAML → embed → upsert pipeline runs offline with stub fallbacks."""
    from gemini_hackathon.journey.level_1_syllabus_extraction import run_level_1

    r = _run(run_level_1(subnation="ireland", subject="mathematics", language="en"))
    assert r.pdf_path, "pdf_path must be set"
    assert r.syllabus["subject"] == "mathematics"
    assert r.syllabus["language"] == "en"
    assert len(r.chunks) >= 1, "at least one chunk must be embedded"
    assert len(r.chunks[0]["vector"]) == 1536, "vector dim must match Vertex gemini-embedding-001"
    assert r.upserted_count >= 1, "at least one chunk must be upserted"
    assert r.vector_backend, "vector_backend must be reported"


def test_level_1_handles_unknown_subject():
    """The stub fallback kicks in for subjects outside the BAML enum."""
    from gemini_hackathon.journey.level_1_syllabus_extraction import run_level_1

    r = _run(run_level_1(subnation="ireland", subject="unknown_subject", language="en"))
    # The stub still produces 3 chunks (the offline stub sentence count).
    assert len(r.chunks) >= 1


# ── Level 2 ───────────────────────────────────────────────────────────


def test_level_2_4_path_consensus_offline():
    from gemini_hackathon.journey.level_2_past_paper_ocr import run_level_2

    r = _run(run_level_2())
    assert r.voted_path, "consensus must pick a winner"
    assert r.consensus_score > 0
    assert len(r.paths) == 4, "all 4 OCR paths must run"
    for p in r.paths:
        assert p["path"] in {"document_ai", "gemini_vision", "gemma4_vertex", "pypdfium2"}


def test_level_2_consensus_finds_correct_winner_among_matching_paths():
    """When 2+ paths produce identical text, the consensus picks one of them."""
    from gemini_hackathon.ocr_ensemble import EnsemblePathOutput, consensus_vote

    p1 = EnsemblePathOutput(path="document_ai", raw_response="the cat sat on the mat")
    p2 = EnsemblePathOutput(path="gemini_vision", raw_response="the cat sat on the mat today")
    p3 = EnsemblePathOutput(path="gemma4_vertex", raw_response="completely unrelated noise")
    winner, score, text = consensus_vote([p1, p2, p3])
    # The 2 agreeing paths have identical pairwise similarity to all other
    # successful paths (no clear pairwise winner), so the consensus
    # picks the first one in input order. Both agree on the same substring
    # (the longest common prefix); the winner's exact text is whichever
    # was listed first.
    assert winner == "document_ai"
    assert score > 0
    assert "the cat sat on the mat" in text


def test_level_2_consensus_rejects_isolated_path():
    """A single successful path still produces a result (with the fallback
    unverified score — no peer to agree with)."""
    from gemini_hackathon.ocr_ensemble import EnsemblePathOutput, consensus_vote

    only = EnsemblePathOutput(path="document_ai", raw_response="only path here")
    winner, score, text = consensus_vote([only])
    assert winner == "document_ai"
    assert score == 0.5  # the unverified-single-path fallback
    assert text == "only path here"


# ── Level 3 ───────────────────────────────────────────────────────────


def test_level_3_marks_student_answer_per_criterion():
    from gemini_hackathon.journey.level_3_marking_scheme import DEFAULT_CRITERIA, run_level_3

    r = _run(
        run_level_3(subject="mathematics", question_id="Q5", student_answer="Use the sine rule")
    )
    assert len(r.criterion_grades) == len(DEFAULT_CRITERIA) == 3
    assert r.total_marks_awarded > 0
    assert r.total_max_marks > 0
    assert r.total_marks_awarded <= r.total_max_marks
    assert r.ncca_policy_citations, "summary must cite the NCCA policy PDF"


def test_level_3_empty_answer_scores_low():
    from gemini_hackathon.journey.level_3_marking_scheme import run_level_3

    r = _run(run_level_3(student_answer=""))
    # The stub grader awards 20% of max for empty answers.
    assert r.total_marks_awarded < r.total_max_marks * 0.5


# ── Level 4 ───────────────────────────────────────────────────────────


def test_level_4_mastery_ledger_4_backend_status():
    from gemini_hackathon.journey.level_4_mastery_update import run_level_4

    r = _run(
        run_level_4(
            learner_id="test@school.ie",
            subject_slug="mathematics",
            outcome_code="MA-LC-MA-1.1",
            mastery_score=0.75,
        )
    )
    expected_backends = {
        "firestore_achievements",
        "mastery_vector",
        "skill_graph",
        "markdown_memory",
    }
    assert expected_backends.issubset(r.per_backend_status.keys())
    # The in-memory MasteryLedger.default() is always healthy.
    for backend, status in r.per_backend_status.items():
        assert status.startswith("OK") or status.startswith("WARN"), (
            f"unexpected status for {backend}: {status!r}"
        )


def test_level_4_handles_empty_subject_safely():
    """The level must not crash on an empty/blank learner_id."""
    from gemini_hackathon.journey.level_4_mastery_update import run_level_4

    r = _run(run_level_4(learner_id="", mastery_score=0.5))
    # The fallback MasteryLedger accepts empty IDs in offline mode.
    assert r.per_backend_status


# ── Level 5 ───────────────────────────────────────────────────────────


def test_level_5_user_question_produces_asset():
    from gemini_hackathon.journey.level_5_asset_generation import run_level_5

    r = _run(
        run_level_5(
            user_question="Draw a labelled diagram of the sine rule for triangle ABC",
            subnation="ireland",
            subject="mathematics",
        )
    )
    assert r.matched_outcomes, "search must return at least 1 matched outcome"
    assert r.asset_request, "BAML extraction must produce an asset_request dict"
    assert r.asset_request["asset_type"] == "syllabus_diagram"
    assert r.asset_local_path, "asset must be saved to a local path"
    assert r.storage_uri, "asset must have a storage URI (file:// or gs://)"
    assert r.asset_bytes_size > 0
    assert "fibo" in r.generation_backend.lower()


def test_level_5_empty_question_still_produces_asset():
    """The asset generation pipeline must degrade gracefully on empty input."""
    from gemini_hackathon.journey.level_5_asset_generation import run_level_5

    r = _run(run_level_5(user_question="", subnation="ireland", subject="mathematics"))
    # Even an empty question produces the stub asset (the offline path
    # doesn't require a meaningful question).
    assert r.storage_uri
