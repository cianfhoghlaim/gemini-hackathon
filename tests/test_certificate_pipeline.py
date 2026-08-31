"""Tests for `gemini_hackathon.certificate` — the LC/JC certificate pipeline.

Updated 2026-08-31 (Phase 6): exercises the canonical data types + the
CertificatePipelineConfig + the pipeline run() end-to-end (with all 7
stages mocked). All tests are offline — no PIL/PDF generation required.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from gemini_hackathon.certificate.pipeline import (
    NCCA_POLICY_PDFS,
    CertificatePipeline,
    CertificatePipelineConfig,
)
from gemini_hackathon.certificate.types import (
    CertificateOutcomeRecord,
    CertificateRecord,
    CertificationCitation,
    CertificationCriteria,
)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _outcome(code: str = "MA-LC-CH-2.1", score: float = 0.85) -> CertificateOutcomeRecord:
    return CertificateOutcomeRecord(
        outcome_code=code,
        subject_slug="chemistry_lc",
        descriptor="Apply the ideal gas law to closed systems",
        mastery_score=score,
        key_competency_codes=("communicating",),
    )


def test_ncca_policy_pdfs_constant_has_five_entries():
    """The 5 NCCA policy PDFs are the canonical source of truth."""
    assert len(NCCA_POLICY_PDFS) == 5


def test_ncca_policy_pdfs_are_unique_and_nonempty():
    """Every entry is a non-empty string with a `.pdf` suffix."""
    seen = set()
    for pdf in NCCA_POLICY_PDFS:
        assert isinstance(pdf, str)
        assert pdf
        assert pdf.endswith(".pdf")
        assert pdf not in seen
        seen.add(pdf)


def test_pipeline_config_defaults():
    """The default config has the canonical 1200x850 dimensions."""
    cfg = CertificatePipelineConfig()
    assert cfg.image_size == (1200, 850)
    # UNOFFICIAL banner is always on by default (per the user's spec).
    assert cfg.include_unofficial_banner is True


def _do_run(coro):
    """Run a coroutine in a fresh event loop."""
    return asyncio.new_event_loop().run_until_complete(coro) or _dummy()


def _dummy():
    return None


def test_pipeline_runs_through_all_seven_stages():
    """`run()` orchestrates stage 1 (criteria) → 7 (provenance)."""
    cfg = CertificatePipelineConfig()
    pipeline = CertificatePipeline(config=cfg)
    # Patch the 7 stage methods to record order.
    pipeline._extract_criteria = AsyncMock(
        return_value=CertificationCriteria(
            stage="scoil_sinsearach",
            subject_slug="chemistry_lc",
            award_descriptor="Exceptional",
            descriptor_vocabulary=[],
            key_competencies=[],
            policy_citations=[],
        )
    )
    pipeline._decompose_outcomes = AsyncMock(return_value=[_outcome()])
    pipeline._extract_paper_and_marking = AsyncMock(return_value=(None, None))
    pipeline._search_official_documents = AsyncMock(return_value=[])
    pipeline._generate_certificate_background = AsyncMock(return_value=b"")
    pipeline._compose_certificate = AsyncMock(return_value=b"\x89PNG-rh")
    pipeline._export_pdf = AsyncMock(return_value=b"%PDF-1.4\n")
    pipeline._save_to_provenance = AsyncMock()

    record = _do_run(pipeline.run(
        learner_id="learner-uuid-1",
        learner_name="Maya O'Brien",
        subject_slug="chemistry_lc",
        stage="scoil_sinsearach",
        outcomes=[_outcome()],
    ))

    # All 7 stages were invoked.
    pipeline._extract_criteria.assert_awaited_once()
    pipeline._decompose_outcomes.assert_awaited_once()
    pipeline._extract_paper_and_marking.assert_awaited_once()
    pipeline._search_official_documents.assert_awaited_once()
    pipeline._generate_certificate_background.assert_awaited_once()
    pipeline._compose_certificate.assert_awaited_once()
    pipeline._export_pdf.assert_awaited_once()
    pipeline._save_to_provenance.assert_awaited_once()

    # The returned record carries through the inputs.
    assert isinstance(record, CertificateRecord)
    assert record.learner_id == "learner-uuid-1"
    assert record.learner_name == "Maya O'Brien"
    assert record.subject_slug == "chemistry_lc"
    assert record.stage == "scoil_sinsearach"
    assert record.png_bytes == b"\x89PNG-rh"
    assert record.pdf_bytes == b"%PDF-1.4\n"
    assert record.issued_at  # populated


def test_citation_carries_required_fields():
    """Every `CertificationCitation` has the 4 canonical fields."""
    cite = CertificationCitation(
        source_pdf="programme.pdf",
        page=12,
        quote="An exemplar of the criterion",
        relevance="Justifies the Exceptional descriptor",
    )
    assert cite.source_pdf == "programme.pdf"
    assert cite.page == 12
    assert cite.quote.startswith("An exemplar")
    assert "Justifies" in cite.relevance


def test_citation_is_frozen_dataclass():
    """Citations are frozen so they cannot be mutated mid-pipeline."""
    cite = CertificationCitation(
        source_pdf="x.pdf", page=1, quote="q", relevance="r"
    )
    with pytest.raises((AttributeError, Exception)):
        cite.page = 99  # type: ignore[misc]


def test_outcome_record_mastery_score_round_trip():
    """`CertificateOutcomeRecord.mastery_score` survives construction."""
    o = _outcome(score=0.42)
    assert o.mastery_score == 0.42
    assert o.subject_slug == "chemistry_lc"


def test_extract_criteria_has_one_citation_per_policy_pdf():
    """Stage 1 yields one `CertificationCitation` per NCCA policy PDF."""
    pipeline = CertificatePipeline()
    criteria = _do_run(pipeline._extract_criteria("chemistry_lc", "scoil_sinsearach"))
    assert len(criteria.policy_citations) == len(NCCA_POLICY_PDFS)


def test_extract_criteria_descriptors_vocabulary_includes_canonical_set():
    """The canonical descriptor vocabulary covers the 4 NCCA tiers."""
    pipeline = CertificatePipeline()
    criteria = _do_run(pipeline._extract_criteria("chemistry_lc", "scoil_sinsearach"))
    assert "Exceptional" in criteria.descriptor_vocabulary
    assert "Above expectations" in criteria.descriptor_vocabulary
    assert "In line with expectations" in criteria.descriptor_vocabulary
    assert "Yet to meet expectations" in criteria.descriptor_vocabulary


def test_extract_criteria_key_competencies_has_six_entries():
    """The NCCA's 6 Key Competencies are surfaced (including Staying Well)."""
    pipeline = CertificatePipeline()
    criteria = _do_run(pipeline._extract_criteria("chemistry_lc", "scoil_sinsearach"))
    assert len(criteria.key_competencies) == 6
    assert "Staying Well" in criteria.key_competencies
