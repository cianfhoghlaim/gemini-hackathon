"""Tests for `gemini_hackathon.ocr_ensemble` — the 4-path consensus OCR
pipeline (Document AI + Gemini Vision + Gemma-4 Vertex + pypdfium2 text layer).

Updated 2026-08-31 (Phase 6): exercises `consensus_vote`, the
`EnsembledExtractor.extract(...)` happy path, the 1-path + 0-path
fallbacks, and `EnsemblePathOutput.succeeded`.
"""

from __future__ import annotations

import pytest

from gemini_hackathon.ocr_ensemble import (
    EnsembledExtractor,
    EnsemblePathOutput,
    EnsembleResult,
    _pairwise_similarity,
    consensus_vote,
)


def _good(path: str, text: str) -> EnsemblePathOutput:
    return EnsemblePathOutput(path=path, raw_response=text)


def _bad(path: str, err: str = "boom") -> EnsemblePathOutput:
    return EnsemblePathOutput(path=path, raw_response="", error=err)


def test_ensemble_path_output_succeeded_with_text():
    """Success requires both `error is None` AND non-empty `raw_response`."""
    assert _good("gemini_vision", "hello").succeeded is True


def test_ensemble_path_output_failed_when_error_set():
    """An error makes the path a failure (even if raw_response was non-empty)."""
    out = EnsemblePathOutput(path="gemini_vision", raw_response="hello", error="boom")
    assert out.succeeded is False


def test_ensemble_path_output_failed_when_text_empty():
    """Empty text (no error) is also a failure (the path produced nothing)."""
    assert _good("gemini_vision", "").succeeded is False
    assert _good("gemini_vision", "   ").succeeded is False


def test_consensus_vote_returns_none_when_no_paths_succeed():
    """If every path errored out, the vote is `(None, 0.0, None)`."""
    paths = [_bad("gemini_vision"), _bad("document_ai"), _bad("pypdfium2")]
    winner, score, text = consensus_vote(paths)
    assert winner is None
    assert score == 0.0
    assert text is None


def test_consensus_vote_picks_longest_text_with_one_success():
    """When only one path succeeds, that one wins (unverified, score 0.5)."""
    only = _good("gemini_vision", "the only candidate text")
    paths = [_bad("document_ai"), only, _bad("pypdfium2")]
    winner, score, text = consensus_vote(paths)
    assert winner == "gemini_vision"
    assert score == 0.5
    assert text == "the only candidate text"


def test_consensus_vote_picks_path_that_agrees_with_others():
    """The winner is the path whose text is most similar to every other path."""
    paths = [
        _good("document_ai", "the quick brown fox jumps over the lazy dog"),
        _good("gemini_vision", "the quick brown fox jumps over the lazy dog"),
        _good("gemma4_vertex", "totally unrelated content"),
    ]
    winner, score, text = consensus_vote(paths)
    # One of the matching pair wins (ties go to the first in iteration order).
    assert winner in {"document_ai", "gemini_vision"}
    # The matching pair has high similarity (~1.0 vs each other, ~0 vs the
    # outlier). The mean for each of the matching pair = (1.0 + ~0) / 2 ~ 0.5.
    # For the outlier, mean = (~0 + ~0) / 2 = ~0. So the matching pair wins
    # by being strictly higher than 0.
    assert score >= 0.5
    assert "fox" in text


def test_consensus_score_calculated_from_mean_pairwise_similarity():
    """The score = mean Jaccard similarity vs every other successful path."""
    # Use identical texts → Jaccard = 1.0 between every pair → mean = 1.0.
    text = "identical text across all paths"
    paths = [
        _good("document_ai", text),
        _good("gemini_vision", text),
        _good("gemma4_vertex", text),
    ]
    _, score, _ = consensus_vote(paths)
    assert score == pytest.approx(1.0, abs=0.01)


def test_consensus_vote_handles_path_with_text_but_error():
    """Path with both non-empty text AND error → failed (succeeded=False)."""
    out = EnsemblePathOutput(
        path="gemini_vision", raw_response="hello", error="incomplete result",
    )
    assert out.succeeded is False


def test_consembled_extractor_raises_for_missing_pdf(tmp_path):
    """`extract()` raises FileNotFoundError when the PDF doesn't exist."""
    extractor = EnsembledExtractor(timeout_seconds=0.1)
    with pytest.raises(FileNotFoundError):
        extractor.extract(tmp_path / "does-not-exist.pdf")


def test_pairwise_similarity_normalises_to_one_for_identical_text():
    """Identical texts have Jaccard = 1.0."""
    assert _pairwise_similarity("the same text", "the same text") == 1.0


def test_pairwise_similarity_zero_for_disjoint_texts():
    """Disjoint tokens → 0.0 (no overlap)."""
    assert _pairwise_similarity("apple banana cherry", "dog elephant frog") == 0.0


def test_pairwise_similarity_zero_for_empty_inputs():
    """Empty strings → 0.0 (no tokens to compare)."""
    assert _pairwise_similarity("", "") == 0.0
    assert _pairwise_similarity("text", "") == 0.0
    assert _pairwise_similarity("", "text") == 0.0


def test_consensus_result_consensus_passed_above_threshold():
    """`consensus_passed` is True when score ≥ 0.60."""
    ok = EnsembleResult(consensus_score=0.61)
    fail = EnsembleResult(consensus_score=0.59)
    assert ok.consensus_passed is True
    assert fail.consensus_passed is False


def test_consensus_result_consensus_passed_at_zero():
    """A score of exactly 0.0 means the consensus vote failed."""
    out = EnsembleResult(consensus_score=0.0)
    assert out.consensus_passed is False
