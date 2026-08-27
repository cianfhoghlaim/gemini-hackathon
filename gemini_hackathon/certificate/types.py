"""gemini_hackathon.certificate.types — the data types for the certificate pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass(frozen=True)
class CertificationCitation:
    """A single citation to a page in one of the 5 NCCA policy PDFs.

    Every claim on every generated certificate carries at least one of these.
    """

    source_pdf: str  # filename (e.g. "SC-L1-L2-Programme-Statement.pdf")
    page: int  # 1-indexed
    quote: str  # verbatim text from the page
    relevance: str  # 1-sentence explanation of how this page informed the claim


@dataclass(frozen=True)
class CertificationCriteria:
    """The official certification criteria (extracted from the 5 NCCA PDFs)."""

    stage: str  # "aistear" / "bunscoil" / "meanscoil" / "scoil_sinsearach" / "ollscoil"
    subject_slug: str
    award_descriptor: str  # NCCA descriptor (e.g. "Exceptional", "Above expectations")
    descriptor_vocabulary: list[str]  # the 4-6 canonical descriptors
    key_competencies: list[str]  # the 5 (or 6 with Staying Well) NCCA Key Competencies
    policy_citations: list[CertificationCitation]  # every cited page


@dataclass
class CertificateOutcomeRecord:
    """One learning-outcome mastery record that's on the certificate."""

    outcome_code: str  # e.g. "MA-LC-CH-2.1"
    subject_slug: str
    descriptor: str  # 1-line description
    mastery_score: float  # 0.0-1.0
    key_competency_codes: list[str] = field(default_factory=list)
    ncca_policy_citations: list[CertificationCitation] = field(default_factory=list)


@dataclass
class CertificateRecord:
    """The final certificate record produced by the pipeline.

    Contains everything needed to render the certificate image + PDF
    + the provenance footer + the skill-progression summary.
    """

    learner_id: str
    learner_name: str
    subject_slug: str
    stage: str  # "aistear" / "bunscoil" / "meanscoil" / "scoil_sinsearach" / "ollscoil"
    # The rendered outputs
    png_bytes: bytes
    pdf_bytes: bytes
    # The certification metadata
    criteria: CertificationCriteria = field(default=None)  # type: ignore[assignment]
    outcomes: list[CertificateOutcomeRecord] = field(default_factory=list)
    policy_citations: list[CertificationCitation] = field(default_factory=list)
    # The skill-progression summary (from the W9 MasteryLedger)
    learner_state_summary: dict[str, Any] = field(default_factory=dict)
    # Timestamp
    issued_at: str = field(default_factory=lambda: datetime.now().isoformat())


__all__ = [
    "CertificationCitation",
    "CertificationCriteria",
    "CertificateOutcomeRecord",
    "CertificateRecord",
]
