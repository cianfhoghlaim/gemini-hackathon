"""Per-subject DLT factory for the gemini-hackathon's 8 core NCCA LC subjects.

Lifted from `cianfhoghlaim/dlt_sources/education/ireland/british_isles/subjects/{mathematics,english,gaeilge,chemistry,geography,physics,biology,computer_science}/{sources,schema}.py` ×16 files (the canonical per-subject factory).

Slimmed to a single file that exposes one `create_<subject>_source()`
function per subject. Each function returns the (pages, pdfs) DLT
resource tuple for the subject.

The 8 NCCA LC subjects we ship for the hackathon:
  1. mathematics   2. english    3. gaeilge    4. chemistry
  5. geography     6. physics    7. biology    8. computer_science

The 6 adjacent subjects (applied_mathematics, history, french,
business, accounting, art) are listed in
`dlt_pipelines/ireland/subjects/_adjacent.py` (deferred for the hackathon).
"""

from __future__ import annotations

from typing import Any

import dlt

from ..._subject_base import (
    CrawledPage,
    PDFResource,
    classify_document_type,
    compute_content_hash,
    crawl_subject,
    extract_pdfs_from_subject,
)
from ..._base.jurisdiction_pipeline_base import IrelandJurisdictionPipeline


_NCCA_CODE_BY_SUBJECT: dict[str, str] = {
    "mathematics": "LC-MATH-LO",
    "english": "LC-ENGL-LO",
    "gaeilge": "LC-GAEL-LO",
    "chemistry": "LC-CHEM-LO",
    "geography": "LC-GEOG-LO",
    "physics": "LC-PHYS-LO",
    "biology": "LC-BIO-LO",
    "computer_science": "LC-CS-LO",
}

_CYCLE: str = "scoil_sinsearach"  # The Senior Cycle (LC) stage for all 8 LC subjects

_IRELAND_PIPELINE = IrelandJurisdictionPipeline()


def _make_source(subject: str, cycle: str = _CYCLE, language: str = "en"):
    """The factory pattern lifted from `subjects/{slug}/sources.py`."""

    @dlt.resource(
        name=f"{subject}_pages",
        write_disposition="merge",
        primary_key=["url"],
        columns={
            "url": {"data_type": "text"},
            "title": {"data_type": "text"},
            "content": {"data_type": "text"},
            "content_hash": {"data_type": "text"},
            "cycle": {"data_type": "text"},
            "subject": {"data_type": "text"},
            "language": {"data_type": "text"},
            "source": {"data_type": "text"},
            "document_type": {"data_type": "text"},
            "crawled_at": {"data_type": "timestamp"},
            "metadata": {"data_type": "complex"},
            "status": {"data_type": "text"},
            "error": {"data_type": "text"},
        },
    )
    def pages_resource() -> Any:
        """Crawled pages for {subject} ({cycle}, {language})."""
        for page in crawl_subject(subject, cycle, language):
            yield page.to_dict()

    @dlt.resource(
        name=f"{subject}_pdfs",
        write_disposition="merge",
        primary_key=["url"],
        columns={
            "url": {"data_type": "text"},
            "cycle": {"data_type": "text"},
            "subject": {"data_type": "text"},
            "language": {"data_type": "text"},
            "source": {"data_type": "text"},
            "document_type": {"data_type": "text"},
            "discovered_at": {"data_type": "timestamp"},
            "source_page_url": {"data_type": "text"},
            "title": {"data_type": "text"},
            "year": {"data_type": "bigint"},
        },
    )
    def pdfs_resource() -> Any:
        """PDF URLs for {subject} ({cycle}, {language})."""
        for pdf in extract_pdfs_from_subject(subject, cycle, language):
            yield pdf.to_dict()

    return pages_resource, pdfs_resource


# Per-subject factories — 8 NCCA LC subjects
create_mathematics_source = lambda cycle=_CYCLE, language="en": _make_source("mathematics", cycle, language)
create_english_source = lambda cycle=_CYCLE, language="en": _make_source("english", cycle, language)
create_gaeilge_source = lambda cycle=_CYCLE, language="en": _make_source("gaeilge", cycle, language)
create_chemistry_source = lambda cycle=_CYCLE, language="en": _make_source("chemistry", cycle, language)
create_geography_source = lambda cycle=_CYCLE, language="en": _make_source("geography", cycle, language)
create_physics_source = lambda cycle=_CYCLE, language="en": _make_source("physics", cycle, language)
create_biology_source = lambda cycle=_CYCLE, language="en": _make_source("biology", cycle, language)
create_computer_science_source = lambda cycle=_CYCLE, language="en": _make_source("computer_science", cycle, language)


# All-subjects registry for the gemini-hackathon ops
ALL_LC_SUBJECTS: tuple[str, ...] = (
    "mathematics", "english", "gaeilge", "chemistry",
    "geography", "physics", "biology", "computer_science",
)


def create_all_lc_subjects_sources(cycle: str = _CYCLE, language: str = "en") -> list[Any]:
    """Create DLT resources for all 8 NCCA LC subjects.

    Used by the Lakehouse orchestration (Phase 1.10) + the multi-subject
    panel routes (Phase 7.4).
    """
    resources: list[Any] = []
    for subject in ALL_LC_SUBJECTS:
        pages, pdfs = _make_source(subject, cycle, language)
        resources.extend([pages, pdfs])
    return resources


__all__ = [
    "ALL_LC_SUBJECTS",
    "create_all_lc_subjects_sources",
    "create_biology_source",
    "create_chemistry_source",
    "create_computer_science_source",
    "create_english_source",
    "create_geography_source",
    "create_gaeilge_source",
    "create_mathematics_source",
    "create_physics_source",
]