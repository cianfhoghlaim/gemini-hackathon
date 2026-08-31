"""schemas.py — the canonical Pydantic shapes for the sourcing pipeline.

Phase 2 of the GCP-first refactor. Three shapes:

  - `ContentArtefactDoc` — the per-document source-of-truth (1 row per
    source PDF / HTML page). Primary key = sha256 of the content bytes.
    Lives at `journeys/{event_code}/content_artefacts/{sha256}` per the
    design decision "A" (per-event tree, so the copilot + the journey
    orchestrator + the studio see one document tree).

  - `CatalogRowDoc` — the per-jurisdiction known-URL catalog (1 row per
    source URL, e.g. "sqa.org.uk → mathematics → National 5 PDF"). Lives
    at `journeys/{event_code}/catalog/{source_key}/{subject_slug}/{language}`.
    This is the *static* "what exists" table — derived from
    `gemini_hackathon/dlt_pipelines/official_doc_fetcher.py:KNOWN_OFFICIAL_URLS`
    on each pipeline run.

  - `SourcingRunDoc` — one row per pipeline invocation, so you can
    answer "what did the last run do?" with a single Firestore query.
    Lives at `journeys/{event_code}/sourcing_runs/{run_id}`. The run_id is
    a UUID4 per invocation (matches the DLT pipeline_state convention).

The shape carries every flag the downstream journey levels flip
(`baml_extracted` / `ocr_consensus_done` / `mastery_done` / `asset_done`)
so progress is visible at the per-document level — not just at the
corpus level — and the copilot can show "27 documents ready, 5
excluded, 2 failed" without any cross-table aggregation.

The `EXCLUDED_REASONS` constant is the closed vocabulary the
`ExcludeDocumentAgent` sub-agent accepts (per the ADK copilot plan).
Adding a new reason = adding it here + updating the copilot's
`instruction=` in `gemini_hackathon/journey/sourcing_copilot/agent.py`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

#: Closed vocabulary for `content_artefacts.excluded_reason`. Add a new
#: reason here + update the copilot's `instruction=` + the codelab.
EXCLUDED_REASONS: tuple[str, ...] = (
    "out_of_scope",  # not part of the syllabus pipeline's concern
    "corrupted",  # failed to parse / page count = 0
    "duplicate",  # sha256 already exists under a different URL
    "superseded",  # newer revision available
    "language_unsupported",  # e.g. an Irish-medium doc when subnation is "scotland"
)

#: Closed vocabulary for `content_artefacts.document_type`. Drives which
#: downstream level picks the doc up (Level 1 reads syllabus PDFs; Level 2
#: reads exam papers; Level 3 reads marking schemes; etc.).
DOCUMENT_TYPES: tuple[str, ...] = (
    "syllabus_pdf",
    "marking_scheme_pdf",
    "exam_paper_pdf",
    "framework_html",
    "policy_pdf",
    "other",
)


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat(timespec="seconds")


class CatalogRowDoc(BaseModel):
    """One known-URL catalog row — the static "what exists" table.

    Primary key: `(source_key, jurisdiction, subject_slug, language)`.
    Re-written on every pipeline run (DLT `write_disposition="replace"`),
    so the table always reflects the canonical `KNOWN_OFFICIAL_URLS`.
    """

    source_key: str
    source_name: str
    jurisdiction: str
    level: str
    language: str
    subject_slug: str
    official_url: str
    fetched_at: str = Field(default_factory=_now_iso)
    expected_document_type: str = "other"


class ContentArtefactDoc(BaseModel):
    """The per-document source-of-truth — one row per fetched byte.

    Primary key: `sha256` (the content hash, not the URL — same content from
    different URLs is correctly deduplicated). Exists at
    `journeys/{event_code}/content_artefacts/{sha256}`. Written by the
    `sourced` step (merge), updated by every subsequent step (also merge
    — boolean flags flip as Levels 1-5 touch the doc).

    `excluded=True` is the workshop host's veto switch — every downstream
    query MUST filter `excluded=False`. The copilot flips this; nothing
    else does.
    """

    sha256: str
    source_key: str
    jurisdiction: str
    level: str
    language: str
    subject_slug: str
    stage_slug: str  # lc / jc / gcse / a_level / unknown (matches journey orchestrator)
    document_type: str  # one of DOCUMENT_TYPES

    official_url: str  # the URL the doc was fetched from
    gcs_uri: str  # gs://... path (prod) or file://... (dev)
    local_cache_uri: str  # file://... (dev only; empty in prod)
    byte_size: int

    page_count: int | None = None

    fetched_at: str = Field(default_factory=_now_iso)
    normalised_at: str | None = None  # ISO timestamp or None (not normalised yet)
    baml_extracted: bool = False
    ocr_consensus_done: bool = False
    mastery_done: bool = False
    asset_done: bool = False

    excluded: bool = False
    excluded_reason: str | None = None  # must be in EXCLUDED_REASONS if set

    last_run_id: str | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)


class SourcingRunDoc(BaseModel):
    """One pipeline invocation's record — append-only history.

    Lives at `journeys/{event_code}/sourcing_runs/{run_id}`. Each row
    captures: which step ran, what step it transitioned from, what it
    produced + what it failed on. The copilot reads the latest row to
    answer "what just happened?"
    """

    run_id: str  # UUID4
    step: str  # "sourced" | "normalised" | "filtered" | "extract-baml"
    started_at: str
    finished_at: str | None = None
    status: Literal["running", "succeeded", "failed", "partial"] = "running"

    # Counts — every step emits one row with the relevant ones populated.
    catalog_rows_total: int | None = None
    sourced_ok: int | None = None
    sourced_fail: int | None = None
    excluded_marked: int | None = None
    excluded_unmarked: int | None = None
    normalised: int | None = None
    baml_extracted: int | None = None
    fetch_errors: list[dict[str, Any]] = Field(default_factory=list)

    notes: str | None = None


def derive_document_type(jurisdiction: str, subject_slug: str, official_url: str) -> str:
    """Best-effort classification of a catalog row's document type.

    Used by the `sourced` step's catalog-row emission so the Firestore
    doc has a `document_type` from the moment it's written (rather than
    having to be inferred later when Level 1 / Level 2 / etc. read it).
    """
    url_lower = official_url.lower()
    if "specification" in url_lower or "syllabus" in url_lower:
        return "syllabus_pdf"
    if "marking" in url_lower or "mark" in url_lower:
        return "marking_scheme_pdf"
    if "exam" in url_lower or "past-paper" in url_lower or "paper" in url_lower:
        return "exam_paper_pdf"
    if "curriculum" in url_lower or url_lower.endswith(".html") or "framework" in url_lower:
        return "framework_html"
    return "syllabus_pdf" if jurisdiction in ("Ireland", "Northern Ireland") else "other"


__all__ = [
    "DOCUMENT_TYPES",
    "EXCLUDED_REASONS",
    "CatalogRowDoc",
    "ContentArtefactDoc",
    "SourcingRunDoc",
    "derive_document_type",
]
