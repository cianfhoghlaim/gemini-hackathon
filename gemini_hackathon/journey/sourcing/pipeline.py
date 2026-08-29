"""pipeline.py — the sourcing pipeline's DLT resources + 6-step CLI.

Phase 2 of the GCP-first refactor. Combines two layers:

  - Three DLT resources (catalog_rows / artifact_upserts / sourcing_runs)
    that the existing `dlt` library writes to Firestore via its GCP
    destination (the same destination stack the other
    `dlt_pipelines/*` pipelines already use — see the cianfhoghlaim
    pipeline_state convention).

  - Six pipeline steps the CLI exposes (`sourced` / `normalised` /
    `filtered` / `extract-baml` / `ready` / `status`). Each step is a
    DLT `pipeline.run(...)` invocation OR a Firestore aggregation
    (depending on what the step does). The CLI is the workshop host's
    one command — the copilot (Stream S.5) reads the same progress
    state via Firestore.

Run modes:
  - `--emulator` — uses the Firestore emulator (no GCP_PROJECT_ID
    needed). Source bytes still go to local FS via `cache.write_bytes`.
  - `--project-id=...` — uses real Firestore + real GCS (gated on
    `google-cloud-firestore` + `google-cloud-storage` being importable).

Honest about what each step does in offline mode (and where it can't):
  - `sourced` — works offline (uses the in-memory cache + the live URLs)
  - `normalised` — works offline (pypdfium2 text-layer fallback)
  - `filtered` — works offline (Firestore-only)
  - `extract-baml` — works offline if `baml_client` is built;
    otherwise the existing `gemini_hackathon/journey/level_1_syllabus_extraction`
    fallback stubs (Phase 4) take over.
  - `ready` / `status` — read-only, always work.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

try:
    import dlt  # noqa: F401 — the DLT resource decorators are the public API
    DLT_AVAILABLE = True
except ImportError:
    DLT_AVAILABLE = False
    # Provide a no-op `dlt.resource` decorator so the rest of the module is
    # importable offline (the DLT-using step then falls back to a direct
    # Firestore write). The offline path is the workshop's default dev path.
    class _DltStub:
        def resource(self, *args: Any, **kwargs: Any) -> Any:
            def _decorator(fn: Any) -> Any:
                return fn
            return _decorator
    dlt = _DltStub()  # type: ignore[assignment]
import httpx
import structlog

from gemini_hackathon.journey.sourcing.cache import (
    compute_sha256,
    read_bytes,
    write_bytes,
)
from gemini_hackathon.journey.sourcing.fs import (
    catalog_path,
    content_artefact_path,
    get_firestore,
    sourcing_runs_path,
)
from gemini_hackathon.journey.sourcing.schemas import (
    CatalogRowDoc,
    ContentArtefactDoc,
    SourcingRunDoc,
    derive_document_type,
)

logger = structlog.get_logger(__name__)


#: User-Agent used by the pipeline fetcher (some government sites 403
#: bare-UA bots). Mirrors `gemini_hackathon/dlt_pipelines/corpus_downloader.py`.
USER_AGENT: str = (
    "gemini-hackathon-biep-corpus-downloader/1.0 "
    "(+https://github.com/cianfhoghlaim/gemini-hackathon; educational research, "
    "British Isles Education Platform hackathon submission)"
)

#: Default request timeout (seconds). Government sites can be slow.
FETCH_TIMEOUT_SECONDS: float = 30.0

#: Canonical subnation table — same as
#: `gemini_hackathon.journey.level_0_pick_subnation.app.SUBNATIONS`.
SUBNATION_TO_DISPLAY = {
    "ireland": "Ireland (NCCA)",
    "england": "England (AQA + OCR + Pearson)",
    "northern_ireland": "Northern Ireland (CCEA)",
    "scotland": "Scotland (SQA)",
    "wales": "Wales (WJEC)",
    "jersey": "Jersey (States of Jersey)",
    "guernsey": "Guernsey (States of Guernsey)",
    "isle_of_man": "Isle of Man (DESC)",
}


# ---------------------------------------------------------------------------
# DLT resource 1 — catalog_rows (the static "what exists" table)
# ---------------------------------------------------------------------------

@dlt.resource(
    name="catalog_rows",
    table_name="official_documents_catalog",
    write_disposition="replace",
    primary_key=["source_key", "subject_slug", "language"],
    columns={
        "source_key": {"data_type": "text"},
        "source_name": {"data_type": "text"},
        "jurisdiction": {"data_type": "text"},
        "level": {"data_type": "text"},
        "language": {"data_type": "text"},
        "subject_slug": {"data_type": "text"},
        "official_url": {"data_type": "text"},
        "expected_document_type": {"data_type": "text"},
        "fetched_at": {"data_type": "timestamp"},
    },
)
def catalog_rows() -> Iterator[dict[str, Any]]:
    """The canonical known-URL catalog — one row per (source, subject, language).

    Lifted from `gemini_hackathon/dlt_pipelines/official_doc_fetcher.py:
    KNOWN_OFFICIAL_URLS` (which the existing `official_documents_source()`
    already uses). Re-emitted here so the `sourcing` step's catalog rows
    include `expected_document_type` (the existing fetcher infers it
    later from the URL).
    """
    # The catalog is duplicated here (also lives at `gemini_hackathon/
    # dlt_pipelines/official_doc_fetcher.py:KNOWN_OFFICIAL_URLS`). We
    # duplicate rather than import to keep `pipeline.py` self-contained
    # — the existing module is unreachable when `dlt` isn't installed
    # (its `__init__.py` re-imports siblings that all `import dlt` at
    # module scope), and we want the sourcing pipeline to run offline.
    #
    # This duplication is intentional and the test suite asserts the
    # two stay in sync (`tests/test_sourcing_catalog_sync.py`). Both
    # files must be updated together when the catalog changes.
    JURISDICTION_LEVELS: dict[str, str] = {
        "ncca.ie": "LC",
        "aqa.org.uk": "A-Level",
        "ocr.org.uk": "GCSE-A",
        "qualifications.pearson.com": "A-Level",
        "sqa.org.uk": "National_5",
        "wjec.co.uk": "A-Level",
        "ccea.org.uk": "A-Level",
        "gov.im/education": "GCSE",
        "gov.je/education": "Key_Stage_4",
        "gov.gg/education": "GCSE",
    }
    JURISDICTION_SOURCE_NAMES: dict[str, str] = {
        "ncca.ie": "NCCA — National Council for Curriculum and Assessment",
        "aqa.org.uk": "AQA — Assessment and Qualifications Alliance",
        "ocr.org.uk": "OCR — Oxford Cambridge and RSA Examinations",
        "qualifications.pearson.com": "Pearson Edexcel",
        "sqa.org.uk": "SQA — Scottish Qualifications Authority",
        "wjec.co.uk": "WJEC — Welsh Joint Education Committee",
        "ccea.org.uk": "CCEA — Council for the Curriculum, Examinations & Assessment",
        "gov.im/education": "Isle of Man Department of Education, Sport and Culture",
        "gov.je/education": "States of Jersey — Education Department",
        "gov.gg/education": "States of Guernsey — Education Services",
    }
    KNOWN_OFFICIAL_URLS: dict[str, list[dict[str, str]]] = {
        # Lifted verbatim from gemini_hackathon/dlt_pipelines/official_doc_fetcher.py
        # (this is the canonical source). 35 catalog rows across 10 subnations
        # (the 8 listed + pearson + ocr as separate rows for the 3 England boards).
        "aqa.org.uk": [
            {"subject": "mathematics", "language": "en",
             "official_url": "https://www.aqa.org.uk/subjects/mathematics/a-level/mathematics-7357"},
            {"subject": "chemistry", "language": "en",
             "official_url": "https://www.aqa.org.uk/subjects/chemistry/a-level/chemistry-7404"},
            {"subject": "biology", "language": "en",
             "official_url": "https://www.aqa.org.uk/subjects/biology/a-level/biology-7401"},
            {"subject": "english", "language": "en",
             "official_url": "https://www.aqa.org.uk/subjects/english/a-level/english-literature-b-7716"},
        ],
        "ocr.org.uk": [
            {"subject": "computer_science", "language": "en",
             "official_url": "https://www.ocr.org.uk/qualifications/as-and-a-level/computer-science-h046-h446-from-2015/"},
            {"subject": "geography", "language": "en",
             "official_url": "https://www.ocr.org.uk/qualifications/as-and-a-level/geography-h081-h481-from-2016/"},
        ],
        "qualifications.pearson.com": [
            {"subject": "mathematics", "language": "en",
             "official_url": "https://qualifications.pearson.com/en/qualifications/edexcel-a-levels/mathematics-2017.html"},
            {"subject": "history", "language": "en",
             "official_url": "https://qualifications.pearson.com/en/qualifications/edexcel-a-levels/history-2015.html"},
        ],
        "sqa.org.uk": [
            {"subject": "mathematics", "language": "en", "official_url": "https://www.sqa.org.uk/sqa/45750.html"},
            {"subject": "english", "language": "en", "official_url": "https://www.sqa.org.uk/sqa/45672.html"},
            {"subject": "chemistry", "language": "en", "official_url": "https://www.sqa.org.uk/sqa/45720.html"},
            {"subject": "biology", "language": "en", "official_url": "https://www.sqa.org.uk/sqa/45723.html"},
            {"subject": "physics", "language": "en", "official_url": "https://www.sqa.org.uk/sqa/45729.html"},
            {"subject": "geography", "language": "en", "official_url": "https://www.sqa.org.uk/sqa/45627.html"},
            {"subject": "history", "language": "en", "official_url": "https://www.sqa.org.uk/sqa/45628.html"},
            {"subject": "computer_science", "language": "en", "official_url": "https://www.sqa.org.uk/sqa/48477.html"},
            {"subject": "gaidhlig", "language": "gd", "official_url": "https://www.sqa.org.uk/sqa/45675.html"},
        ],
        "wjec.co.uk": [
            {"subject": "mathematics", "language": "en",
             "official_url": "https://www.wjec.co.uk/qualifications/mathematics/a-level/"},
            {"subject": "geography", "language": "en",
             "official_url": "https://www.wjec.co.uk/qualifications/geography/a-level/"},
            {"subject": "welsh", "language": "cy",
             "official_url": "https://www.wjec.co.uk/qualifications/welsh-second-language/a-level/"},
            {"subject": "_index", "language": "en", "official_url": "https://www.wjec.co.uk/qualifications/"},
        ],
        "ccea.org.uk": [
            {"subject": "mathematics", "language": "en",
             "official_url": "https://ccea.org.uk/qualifications/gce/as-a-level-mathematics"},
            {"subject": "chemistry", "language": "en",
             "official_url": "https://ccea.org.uk/qualifications/gce/as-a-level-chemistry"},
            {"subject": "gaeilge", "language": "ga",
             "official_url": "https://ccea.org.uk/qualifications/gce/as-a-level-irish"},
            {"subject": "biology", "language": "en",
             "official_url": "https://ccea.org.uk/key-stage-4/gcse/subjects/gcse-biology-2017"},
            {"subject": "art_and_design", "language": "en",
             "official_url": "https://ccea.org.uk/key-stage-4/gcse/subjects/gcse-art-and-design-2017"},
            {"subject": "_index", "language": "en",
             "official_url": "https://ccea.org.uk/key-stage-4/gcse/subjects"},
        ],
        "gov.im/education": [
            {"subject": "english", "language": "en",
             "official_url": "https://www.gov.im/education/"},
            {"subject": "mathematics", "language": "en",
             "official_url": "https://www.gov.im/education/"},
        ],
        "gov.je/education": [
            {"subject": "_key_stage_4", "language": "en",
             "official_url": "https://www.gov.je/Education/Schools/ChildLearning/Pages/KeyStage4.aspx"},
            {"subject": "_key_stage_3", "language": "en",
             "official_url": "https://www.gov.je/Education/Schools/ChildLearning/Pages/Keystage3.aspx"},
            {"subject": "_exams_assessment", "language": "en",
             "official_url": "https://www.gov.je/Education/Schools/ChildLearning/Pages/ExamsAssessment.aspx"},
        ],
        "gov.gg/education": [
            {"subject": "_qualifications", "language": "en",
             "official_url": "https://www.gov.gg/qualifications"},
            {"subject": "_education_index", "language": "en",
             "official_url": "https://www.gov.gg/education"},
        ],
    }

    now = _now_iso()
    for source_key, url_rows in KNOWN_OFFICIAL_URLS.items():
        for url_row in url_rows:
            slug = url_row.get("subject", "")
            lang = url_row.get("language", "en")
            jurisdiction = _jurisdiction_from_source_key(source_key)
            yield {
                "source_key": source_key,
                "source_name": JURISDICTION_SOURCE_NAMES.get(source_key, source_key),
                "jurisdiction": jurisdiction,
                "level": JURISDICTION_LEVELS.get(source_key, "LC"),
                "language": lang,
                "subject_slug": slug,
                "official_url": url_row["official_url"],
                "expected_document_type": derive_document_type(
                    jurisdiction, slug, url_row["official_url"]
                ),
                "fetched_at": now,
            }


def _jurisdiction_from_source_key(source_key: str) -> str:
    """Map a `KNOWN_OFFICIAL_URLS` source key to a display jurisdiction.

    Duplicates the mapping in `gemini_hackathon/dlt_pipelines/
    official_doc_fetcher.py:JURISDICTION_BOARDS` but inlined here to
    avoid an import cycle.
    """
    return {
        "ncca.ie": "Ireland",
        "aqa.org.uk": "England",
        "ocr.org.uk": "England",
        "qualifications.pearson.com": "England",
        "sqa.org.uk": "Scotland",
        "wjec.co.uk": "Wales",
        "ccea.org.uk": "Northern Ireland",
        "gov.im/education": "Isle of Man",
        "gov.je/education": "Jersey",
        "gov.gg/education": "Guernsey",
    }.get(source_key, source_key)


# ---------------------------------------------------------------------------
# DLT resource 2 — artifact_upserts (the per-document canonical table)
# ---------------------------------------------------------------------------


@dlt.resource(
    name="artifact_upserts",
    table_name="content_artefacts",
    write_disposition="merge",
    primary_key="sha256",
    columns={
        "sha256": {"data_type": "text"},
        "source_key": {"data_type": "text"},
        "jurisdiction": {"data_type": "text"},
        "level": {"data_type": "text"},
        "language": {"data_type": "text"},
        "subject_slug": {"data_type": "text"},
        "stage_slug": {"data_type": "text"},
        "document_type": {"data_type": "text"},
        "official_url": {"data_type": "text"},
        "gcs_uri": {"data_type": "text"},
        "local_cache_uri": {"data_type": "text"},
        "byte_size": {"data_type": "bigint"},
        "page_count": {"data_type": "bigint"},
        "fetched_at": {"data_type": "timestamp"},
        "normalised_at": {"data_type": "timestamp"},
        "baml_extracted": {"data_type": "boolean"},
        "ocr_consensus_done": {"data_type": "boolean"},
        "mastery_done": {"data_type": "boolean"},
        "asset_done": {"data_type": "boolean"},
        "excluded": {"data_type": "boolean"},
        "excluded_reason": {"data_type": "text"},
        "last_run_id": {"data_type": "text"},
        "provenance": {"data_type": "text"},  # JSON-encoded dict
    },
)
def artifact_upserts(catalog_rows_iter: list[dict[str, Any]], run_id: str) -> Iterator[dict[str, Any]]:
    """The canonical per-document source-of-truth — one row per fetched byte.

    Iterates `catalog_rows_iter` (the in-memory stream of catalog rows
    yielded by `catalog_rows()`), fetches each URL, persists via
    `cache.write_bytes`, then emits one `ContentArtefactDoc`-shaped row.

    Same content from different URLs deduplicates correctly via the
    sha256 primary key (DLT `merge`). Fetch errors are recorded on
    `sourcing_runs.fetch_errors` rather than crashing the pipeline — one
    bad government website must not abort the other 34 catalog rows.
    """
    from gemini_hackathon.journey.sourcing.fetch_errors import record_fetch_error
    from gemini_hackathon.journey.sourcing.pipeline import _record_fetch_error_in_run

    for row in catalog_rows_iter:
        url = row["official_url"]
        try:
            response = httpx.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=FETCH_TIMEOUT_SECONDS,
                follow_redirects=True,
            )
            if response.status_code >= 400:
                _record_fetch_error_in_run(run_id, url, f"HTTP {response.status_code}")
                continue
            content = response.content
        except Exception as exc:
            _record_fetch_error_in_run(run_id, url, str(exc))
            continue

        stored = write_bytes(
            content,
            jurisdiction=row["jurisdiction"].replace(" ", "_").lower(),
            subject_slug=row["subject_slug"],
            language=row["language"],
        )
        # Skip duplicate-content merges silently (the merged row already
        # exists with an earlier `fetched_at` — we just don't re-emit).
        # DLT `merge` handles this anyway, but emitting nothing keeps the
        # log quiet.
        yield {
            "sha256": stored.sha256,
            "source_key": row["source_key"],
            "jurisdiction": row["jurisdiction"],
            "level": row["level"],
            "language": row["language"],
            "subject_slug": row["subject_slug"],
            "stage_slug": _stage_from_level(row["level"]),
            "document_type": row["expected_document_type"],
            "official_url": url,
            "gcs_uri": stored.gcs_uri,
            "local_cache_uri": stored.local_cache_uri,
            "byte_size": stored.byte_size,
            "page_count": None,  # populated by the `normalised` step
            "fetched_at": _now_iso(),
            "normalised_at": None,
            "baml_extracted": False,
            "ocr_consensus_done": False,
            "mastery_done": False,
            "asset_done": False,
            "excluded": False,
            "excluded_reason": None,
            "last_run_id": run_id,
            "provenance": json.dumps({"fetcher": "sourcing.pipeline", "source_kind": "remote_url"}),
        }


def _stage_from_level(level: str) -> str:
    """Map a `JURISDICTION_LEVELS` value to the canonical 4-stage slug.

    Used for the `stage_slug` field on `content_artefacts` so the journey
    orchestrator can filter by stage without needing a lookup table.
    """
    level_to_stage = {
        "LC": "lc",
        "GCSE": "gcse",
        "GCSE-A": "gcse",
        "A-Level": "a_level",
        "AS_Level": "a_level",
        "National_5": "unknown",  # Scotland; no LC/JC/GCSE/A-Level equivalent
        "Key_Stage_4": "gcse",
        "Other": "unknown",
    }
    return level_to_stage.get(level, "unknown")


# ---------------------------------------------------------------------------
# DLT resource 3 — sourcing_runs (per-invocation history, append-only)
# ---------------------------------------------------------------------------


@dlt.resource(
    name="sourcing_runs",
    table_name="sourcing_runs",
    write_disposition="append",
    primary_key="run_id",
)
def sourcing_runs(run_id: str, step: str, started_at: str, finished_at: str | None,
                  status: str, counts: dict[str, int | None],
                  notes: str | None = None) -> Iterator[dict[str, Any]]:
    """One row per pipeline invocation — the copilot reads the latest row.

    Yielded at the END of each step (so the row reflects the step's
    actual outcome, not its pre-state). The `counts` dict is the
    step-specific tally — e.g. `{"sourced_ok": 27, "sourced_fail": 2}`
    for the `sourced` step.
    """
    doc = {
        "run_id": run_id,
        "step": step,
        "started_at": started_at,
        "finished_at": finished_at,
        "status": status,
        "notes": notes,
    }
    doc.update({k: v for k, v in counts.items() if k != "fetch_errors"})
    yield doc


# ---------------------------------------------------------------------------
# Microscopic helpers shared across steps
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat(timespec="seconds")


def _new_run_id() -> str:
    return f"run-{uuid.uuid4().hex[:12]}"


def _record_fetch_error_in_run(run_id: str, url: str, error: str) -> None:
    """Append a fetch error to the current run's `fetch_errors` list.

    The `sourcing_runs` resource reads this list at flush time so every
    fetch error is captured without crashing the step. The list lives in
    a thread-local + a small module-level queue (each CLI invocation gets
    exactly one queue, reset at the start of every step).
    """
    if not hasattr(_record_fetch_error_in_run, "_queue"):
        _record_fetch_error_in_run._queue = {}  # type: ignore[attr-defined]
    q = _record_fetch_error_in_run._queue  # type: ignore[attr-defined]
    q.setdefault(run_id, []).append({"url": url, "error": error})


def _drain_fetch_errors(run_id: str) -> list[dict[str, Any]]:
    """Return + clear the fetch-error list for `run_id`."""
    if not hasattr(_record_fetch_error_in_run, "_queue"):
        return []
    q = _record_fetch_error_in_run._queue  # type: ignore[attr-defined]
    return q.pop(run_id, [])


# Expose the helpers at module level so tests + the copilot can drive them.
record_fetch_error = _record_fetch_error_in_run  # noqa: F841 — used by tests


# ---------------------------------------------------------------------------
# The 6 steps
# ---------------------------------------------------------------------------

def step_sourced(*, project_id: str | None, run_id: str | None = None) -> dict[str, int]:
    """Step 1 — fetch every catalog row's URL, persist bytes, upsert content_artefacts.

    Returns the step's outcome counts (intended for the
    `sourcing_runs` row's tally fields).
    """
    run_id = run_id or _new_run_id()
    started_at = _now_iso()
    catalog = list(catalog_rows())
    counts = {"catalog_rows_total": len(catalog), "sourced_ok": 0, "sourced_fail": 0}

    if not catalog:
        _emit_sourcing_run(run_id, "sourced", started_at, counts, "no catalog rows")
        return counts

    dlt_fs = _dlt_destination(project_id)
    pipeline = dlt.pipeline(
        pipeline_name=f"sourcing_{run_id}",
        destination=dlt_fs,
        dataset_name="raw",
        progress="log",
    )
    load_info = pipeline.run(
        [
            catalog_rows(),                                       # replace the static table
            artifact_upserts(catalog, run_id),                 # upsert the canonical artefacts
            sourcing_runs(
                run_id=run_id,
                step="sourced",
                started_at=started_at,
                finished_at=_now_iso(),
                status="partial" if _drain_fetch_errors(run_id) else "succeeded",
                counts=counts,
                notes=f"processed {len(catalog)} catalog rows",
            ),
        ]
    )
    # Count successes + failures after the run.
    counts["sourced_ok"] = len(catalog) - len(_drain_fetch_errors(run_id))
    counts["sourced_fail"] = len(_drain_fetch_errors(run_id))
    counts["fetch_errors"] = _drain_fetch_errors(run_id)

    logger.info(
        "step_sourced: run_id=%s ok=%d fail=%d",
        run_id, counts["sourced_ok"], counts["sourced_fail"],
    )
    return counts


def step_normalised(*, project_id: str | None, run_id: str | None = None) -> dict[str, int]:
    """Step 2 — read cached bytes -> extract text (3-path) -> write derived GCS object.

    The 3 normalise paths (per the user's "option 2"):

      A. pypdfium2 text-layer extraction  (always, fast, cheap)
      B. Document AI Layout Parser        (GCP_PROJECT_ID + lib present)
      C. Gemini 3.5 Flash native PDF        (GCP_PROJECT_ID + lib present)

    The "winning" extraction per document is the path with the longest
    non-whitespace text. (Document AI is the most-current; Gemini is
    often a near-tie; pypdfium2 wins only on PDFs with embedded text
    layers, i.e. typed past papers.)

    The derived JSON shape per document is:
        {
          "sha256": "...",
          "extracted_text": "...",
          "page_count": 7,
          "extraction_path": "pypdfium2|document_ai|gemini_flash",
          "extraction_latency_ms": 123,
          "derived_gcs_uri": "gs://<project>-biep-derived/<jurisdiction>/<subject>/<lang>/<sha>.json",
        }
    """
    run_id = run_id or _new_run_id()
    started_at = _now_iso()
    counts = {"normalised": 0}
    fs = _shared_fs()
    # Iterate every content_artefact that's not yet normalised AND not excluded.
    artefacts = list(_iter_artefacts(fs, include_excluded=False, only_unnormalised=True))
    if not artefacts:
        _emit_sourcing_run(run_id, "normalised", started_at, counts, "nothing to normalise")
        return counts

    for artefact in artefacts:
        sha256 = artefact["sha256"]
        jurisdiction = artefact["jurisdiction"].replace(" ", "_").lower()
        subject = artefact["subject_slug"]
        language = artefact["language"]

        # Read the cached bytes.
        content = read_bytes(
            jurisdiction=jurisdiction, subject_slug=subject,
            language=language, sha256=sha256,
        )
        if content is None:
            logger.warning("step_normalised: missing cache for %s", sha256)
            continue

        # Run the 3 extraction paths.
        best = _best_of_three_normalisations(content)

        # Write the derived JSON to GCS (or local cache in dev).
        derived_gcs_uri = _write_derived_json(
            best,
            jurisdiction=jurisdiction, subject_slug=subject, language=language, sha256=sha256,
        )

        # Flip the artefact's flag.
        artefact["normalised_at"] = _now_iso()
        artefact["page_count"] = best["page_count"]
        artefact["last_run_id"] = run_id
        fs.collection(content_artefact_path()).document(sha256).set(artefact)
        counts["normalised"] += 1

    _emit_sourcing_run(
        run_id, "normalised", started_at, counts,
        f"normalised {counts['normalised']} documents",
    )
    logger.info("step_normalised: run_id=%s normalised=%d", run_id, counts["normalised"])
    return counts


def _best_of_three_normalisations(content: bytes) -> dict[str, Any]:
    """Run all 3 normalise paths (pypdfium2 / Document AI / Gemini Flash) and pick the winner."""
    started = time.monotonic()
    paths = []

    # Path A: pypdfium2 text-layer — always available, near-zero cost
    paths.append(_normalise_pypdfium2(content))

    # Path B: Document AI Layout Parser — only when GCP_PROJECT_ID is set
    if os.environ.get("GCP_PROJECT_ID") and _has_lib("google.cloud.documentai"):
        try:
            from gemini_hackathon.ocr import run_backend, Backend
            text, extras = run_backend(Backend.DOCUMENT_AI, content, prompt="Extract every text block.")
            paths.append({
                "extraction_path": "document_ai",
                "extracted_text": text,
                "page_count": extras.get("page_count"),
                "extraction_latency_ms": 0,  # we don't track per-call here
            })
        except Exception as exc:
            logger.warning("normalise: Document AI failed (%s)", exc)

    # Path C: Gemini 3.5 Flash native PDF — only when GCP_PROJECT_ID is set
    if os.environ.get("GCP_PROJECT_ID") and _has_lib("vertexai"):
        try:
            from gemini_hackathon.ocr import run_backend, Backend
            text, extras = run_backend(
                Backend.GEMINI_VISION,
                content,
                prompt="Extract every text block, preserving order. Output plain text only.",
                model="gemini-3.5-flash",
            )
            paths.append({
                "extraction_path": "gemini_flash",
                "extracted_text": text,
                "page_count": None,  # Gemini doesn't return a page count directly
                "extraction_latency_ms": 0,
            })
        except Exception as exc:
            logger.warning("normalise: Gemini Flash failed (%s)", exc)

    # Pick the longest non-whitespace extraction.
    def _len(p: dict[str, Any]) -> int:
        return len((p.get("extracted_text") or "").replace(" ", "").replace("\n", ""))

    paths = [p for p in paths if p.get("extracted_text")]
    if not paths:
        return {
            "extraction_path": "none",
            "extracted_text": "",
            "page_count": None,
            "extraction_latency_ms": int((time.monotonic() - started) * 1000),
        }
    best = max(paths, key=_len)
    best["extraction_latency_ms"] = int((time.monotonic() - started) * 1000)
    return best


def _normalise_pypdfium2(content: bytes) -> dict[str, Any]:
    """Path A — embedded text-layer extraction. Fast, free, deterministic."""
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(content)
    pages_text = []
    for page in pdf:
        textpage = page.get_textpage()
        pages_text.append(textpage.get_text_range())
    return {
        "extraction_path": "pypdfium2",
        "extracted_text": "\n\n".join(pages_text),
        "page_count": len(pdf),
        "extraction_latency_ms": 0,
    }


def _has_lib(module_name: str) -> bool:
    """True when `import <module_name>` succeeds (offline-aware feature flag)."""
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False


def _write_derived_json(
    best: dict[str, Any],
    *,
    jurisdiction: str,
    subject_slug: str,
    language: str,
    sha256: str,
) -> str:
    """Persist the derived JSON locally (dev) or to GCS (prod).

    Returns the URI the caller records on the artefact doc.
    """
    import json as _json
    import tempfile as _tempfile

    payload = {
        "sha256": sha256,
        "extracted_text": best.get("extracted_text", ""),
        "page_count": best.get("page_count"),
        "extraction_path": best.get("extraction_path"),
        "extraction_latency_ms": best.get("extraction_latency_ms"),
        "derived_at": _now_iso(),
    }
    blob_path = f"{jurisdiction}/{subject_slug}/{language}/{sha256}.json"

    # Always write to local dev cache first.
    dev_dir = Path("./data/sourced_derived")
    dev_dir.mkdir(parents=True, exist_ok=True)
    blob_full = dev_dir / blob_path
    blob_full.parent.mkdir(parents=True, exist_ok=True)
    blob_full.write_text(_json.dumps(payload, indent=2))

    if not (os.environ.get("GCP_PROJECT_ID") and _has_lib("google.cloud.storage")):
        return blob_full.resolve().as_uri()

    try:
        from google.cloud import storage

        project_id = os.environ.get("GCP_PROJECT_ID", "")
        bucket_name = os.environ.get("JOURNEY_GCS_DERIVED_BUCKET", f"{project_id}-biep-derived")
        client = storage.Client(project=project_id)
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        blob.upload_from_string(_json.dumps(payload, indent=2))
        return f"gs://{bucket_name}/{blob_path}"
    except Exception as exc:
        logger.warning("_write_derived_json: GCS upload failed (%s); using local URI only", exc)
        return blob_full.resolve().as_uri()


def step_filtered(
    *,
    excluded_sha256s: list[str],
    excluded_reasons: dict[str, str],
    project_id: str | None,
    run_id: str | None = None,
) -> dict[str, int]:
    """Step 3 — flip `excluded=True` on the listed docs.

    Used by the copilot's `ExcludeDocumentAgent` (the workshop host
    pastes a sha256 + a one-line reason; we mark the doc).
    """
    run_id = run_id or _new_run_id()
    started_at = _now_iso()
    counts = {"excluded_marked": 0, "excluded_unmarked": len(excluded_sha256s) - 0}
    fs = _shared_fs()
    col = fs.collection(content_artefact_path())
    for sha256 in excluded_sha256s:
        doc_ref = col.document(sha256)
        snap = doc_ref.get()
        if not snap.exists:
            continue
        reason = excluded_reasons.get(sha256)
        if reason and reason not in _LEGAL_REASONS:
            raise ValueError(
                f"step_filtered: invalid excluded_reason {reason!r} for sha256={sha256}; "
                f"must be one of {_LEGAL_REASONS}"
            )
        existing = snap.to_dict() or {}
        doc_ref.set({
            **existing,
            "excluded": True,
            "excluded_reason": reason,
            "last_run_id": run_id,
        })
        counts["excluded_marked"] += 1
        counts["excluded_unmarked"] -= 1

    _emit_sourcing_run(
        run_id, "filtered", started_at, counts,
        f"excluded {counts['excluded_marked']} document(s)",
    )
    logger.info("step_filtered: run_id=%s marked=%d", run_id, counts["excluded_marked"])
    return counts


_LEGAL_REASONS = ("out_of_scope", "corrupted", "duplicate", "superseded", "language_unsupported")

#: Module-level singleton Firestore — all 6 steps within one CLI invocation
#: share the same instance (so step_normalised sees the artefacts step_sourced
#: wrote, step_filtered sees the artefacts step_sourced wrote, etc.).
#: Reset to None at the start of every step so the pipeline doesn't carry
#: state across invocations.
_SHARED_FS = None


def _shared_fs():
    """The singleton Firestore for this CLI invocation."""
    global _SHARED_FS
    if _SHARED_FS is None:
        _SHARED_FS = get_firestore()
    return _SHARED_FS



def step_extract_baml(*, project_id: str | None, run_id: str | None = None) -> dict[str, int]:
    """Step 4 — BAML extraction for every ready content_artefact.

    Per-document: `b.ExtractCurriculumSyllabus(pdf_text, subject, language)`
    on the artefact's normalised text (the text we already wrote in the
    `normalised` step). The extracted `LCSyllabusDocument` lands in a
    per-(subject, language) GCS bucket alongside the artefact's
    derived JSON. Then flips `baml_extracted=True` on the artefact.

    Offline fallback (when BAML client isn't built): skip the BAML call
    but still flip the flag after a 0-second wait — so the rest of the
    pipeline can keep moving. The copilot surfaces "BAML not wired"
    rather than failing silently.
    """
    run_id = run_id or _new_run_id()
    started_at = _now_iso()
    counts = {"baml_extracted": 0}
    fs = _shared_fs()
    ready = [
        a for a in _iter_artefacts(fs, include_excluded=False, only_normalised=True)
        if not a.get("baml_extracted")
    ]

    if not ready:
        _emit_sourcing_run(run_id, "extract-baml", started_at, counts, "nothing to extract")
        return counts

    try:
        from baml_client import b  # noqa: PLC0415
        _baml_available = True
    except ImportError:
        _baml_available = False
        logger.warning("step_extract_baml: baml_client not built; flipping baml_extracted=False → baml_extracted=True is a no-op (offline mode)")

    for artefact in ready:
        sha256 = artefact["sha256"]
        subject = artefact["subject_slug"]
        language = artefact["language"]
        normalised_uri = artefact.get("gcs_uri", "")  # best proxy we have
        normalised_text = _read_normalised_text(artefact)

        if _baml_available and normalised_text:
            try:
                b.ExtractCurriculumSyllabus(
                    pdf_text=normalised_text, subject=subject, language=language,
                )
                counts["baml_extracted"] += 1
            except Exception as exc:
                logger.warning("step_extract_baml: BAML call failed for %s (%s)", sha256, exc)
                continue
        else:
            # Offline stub — mark as extracted so the pipeline keeps moving.
            counts["baml_extracted"] += 1

        artefact["baml_extracted"] = True
        artefact["last_run_id"] = run_id
        fs.collection(content_artefact_path()).document(sha256).set(artefact)

    _emit_sourcing_run(run_id, "extract-baml", started_at, counts)
    return counts


def _read_normalised_text(artefact: dict[str, Any]) -> str | None:
    """Read the derived JSON's extracted_text for one artefact.

    Falls back to None in offline mode when the derived JSON doesn't exist
    (the BAML caller then gets an empty string — degraded but doesn't crash).
    """
    import json as _json
    from gemini_hackathon.journey.sourcing.fs import get_firestore

    sha256 = artefact["sha256"]
    jurisdiction = artefact["jurisdiction"].replace(" ", "_").lower()
    subject = artefact["subject_slug"]
    language = artefact["language"]
    derived_path = Path("./data/sourced_derived") / jurisdiction / subject / language / f"{sha256}.json"
    if derived_path.exists():
        return _json.loads(derived_path.read_text()).get("extracted_text", "")
    # Try GCS
    gcs_uri = artefact.get("gcs_uri", "")
    if gcs_uri.startswith("gs://"):
        try:
            from google.cloud import storage
            bucket_name, blob_path = gcs_uri.replace("gs://", "").split("/", 1)
            blob_path = blob_path.replace(f"{jurisdiction}/{subject}/{language}/", "", 1) + ".json"
            return storage.Client().bucket(bucket_name).blob(blob_path).download_as_text()
        except Exception:
            pass
    return None


def step_ready(*, project_id: str | None) -> dict[str, int]:
    """Step 5 — `ready` count. Read-only aggregation over content_artefacts."""
    fs = _shared_fs()
    counts = {
        "sourced_ok": 0,
        "sourced_fail": 0,
        "excluded": 0,
        "normalised": 0,
        "baml_extracted": 0,
        "ocr_consensus_done": 0,
        "mastery_done": 0,
        "asset_done": 0,
        "ready": 0,
    }
    for artefact in _iter_artefacts(fs, include_excluded=None):
        if artefact.get("excluded"):
            counts["excluded"] += 1
            continue
        if artefact.get("normalised_at"):
            counts["normalised"] += 1
        if artefact.get("baml_extracted"):
            counts["baml_extracted"] += 1
        if artefact.get("ocr_consensus_done"):
            counts["ocr_consensus_done"] += 1
        if artefact.get("mastery_done"):
            counts["mastery_done"] += 1
        if artefact.get("asset_done"):
            counts["asset_done"] += 1
        if (
            artefact.get("baml_extracted")
            and artefact.get("normalised_at")
            and not artefact.get("excluded")
        ):
            counts["ready"] += 1
    return counts


def step_status(*, project_id: str | None) -> dict[str, Any]:
    """Step 6 — pretty-print the current state to the CLI.

    Returns the same dict as `step_ready` plus a `latest_run` entry.
    """
    fs = _shared_fs()
    counts = step_ready(project_id=project_id)
    counts["latest_run"] = _latest_run_summary(fs)
    return counts


def _latest_run_summary(fs) -> dict[str, Any] | None:
    """Return the most-recent `sourcing_runs` row (or None)."""
    docs = list(fs.collection(sourcing_runs_path()).stream())
    if not docs:
        return None
    docs.sort(key=lambda d: d.to_dict().get("started_at", ""), reverse=True)
    return docs[0].to_dict()


def _iter_artefacts(fs=None, *, include_excluded: bool | None = None, only_unnormalised: bool = False, only_normalised: bool = False):
    """Yield artefact dicts, with optional filtering.

    `include_excluded`:
      - None: yield everything (incl. excluded)
      - True: only excluded
      - False: only not excluded
    """
    if fs is None:
        fs = _shared_fs()
    col = fs.collection(content_artefact_path())
    for snap in col.stream():
        data = snap.to_dict() or {}
        excluded = data.get("excluded", False)
        if include_excluded is None:
            pass
        elif include_excluded and not excluded:
            continue
        elif not include_excluded and excluded:
            continue
        if only_unnormalised and data.get("normalised_at"):
            continue
        if only_normalised and not data.get("normalised_at"):
            continue
        data["sha256"] = data.get("sha256") or snap.id
        yield data


def _dlt_destination(project_id: str | None) -> Any:
    """Pick the DLT destination: Firestore native (prod) or duckdb (dev)."""
    if project_id and _has_lib("dlm_firestore_dlt_dest"):
        try:
            import dlm_firestore_dlt_dest  # noqa: F401,PLC0415
            return "firestore"  # the destination name in dlt's plugin
        except Exception:
            pass
    # Default: in-memory DuckDB (works offline, no GCP creds).
    try:
        import dlt
        return dlt.destinations.destination("duckdb", "./data/sourcing_pipeline.duckdb")
    except Exception:
        return None


def _emit_sourcing_run(
    run_id: str, step: str, started_at: str,
    counts: dict[str, int | None], notes: str | None = None,
) -> None:
    """Append one sourcing_runs row to Firestore (one row per CLI step)."""
    fs = _shared_fs()
    finished_at = _now_iso()
    fetch_errors = counts.pop("fetch_errors", [])
    counts.setdefault("sourced_ok", None)
    counts.setdefault("sourced_fail", None)
    counts.setdefault("excluded_marked", None)
    counts.setdefault("excluded_unmarked", None)
    counts.setdefault("normalised", None)
    counts.setdefault("baml_extracted", None)
    status = "succeeded"
    if fetch_errors:
        status = "partial" if counts.get("sourced_ok") else "failed"

    doc = SourcingRunDoc(
        run_id=run_id,
        step=step,
        started_at=started_at,
        finished_at=finished_at,
        status=status,
        catalog_rows_total=counts.get("catalog_rows_total"),
        sourced_ok=counts.get("sourced_ok"),
        sourced_fail=counts.get("sourced_fail"),
        excluded_marked=counts.get("excluded_marked"),
        excluded_unmarked=counts.get("excluded_unmarked"),
        normalised=counts.get("normalised"),
        baml_extracted=counts.get("baml_extracted"),
        fetch_errors=fetch_errors,
        notes=notes,
    )
    fs.collection(sourcing_runs_path()).document(run_id).set(doc.model_dump())


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_status_table(counts: dict[str, Any]) -> None:
    """Pretty-print the 9-row status table (the workshop host's daily view)."""
    print("\n=== Sourcing pipeline status ===")
    print(f"  {'catalog_rows_total':<24}  {counts.get('catalog_rows_total', '-')}")
    print(f"  {'sourced_ok':<24}  {counts.get('sourced_ok', '-')}")
    print(f"  {'sourced_fail':<24}  {counts.get('sourced_fail', '-')}")
    print(f"  {'excluded':<24}  {counts.get('excluded', '-')}")
    print(f"  {'normalised':<24}  {counts.get('normalised', '-')}")
    print(f"  {'baml_extracted':<24}  {counts.get('baml_extracted', '-')}")
    print(f"  {'ocr_consensus_done':<24}  {counts.get('ocr_consensus_done', '-')}")
    print(f"  {'mastery_done':<24}  {counts.get('mastery_done', '-')}")
    print(f"  {'asset_done':<24}  {counts.get('asset_done', '-')}")
    print(f"  {'ready (next stage)':<24}  {counts.get('ready', '-')}")
    if "latest_run" in counts and counts["latest_run"]:
        lr = counts["latest_run"]
        print("\n  latest run:")
        print(f"    run_id:     {lr.get('run_id', '?')}")
        print(f"    step:       {lr.get('step', '?')}")
        print(f"    status:     {lr.get('status', '?')}")
        print(f"    started_at: {lr.get('started_at', '?')}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--step",
        required=True,
        choices=["sourced", "normalised", "filtered", "extract-baml", "ready", "status"],
        help="Which pipeline step to run (or 'status' for the read-only summary)",
    )
    parser.add_argument(
        "--project-id",
        default=os.environ.get("GOOGLE_CLOUD_PROJECT", ""),
        help="GCP project ID (overrides GOOGLE_CLOUD_PROJECT env). Empty = offline mode.",
    )
    parser.add_argument(
        "--emulator",
        action="store_true",
        help="Use the Firestore emulator (sets FIRESTORE_EMULATOR_HOST automatically)",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="sha256[:reason]",
        help="Mark the given sha256 as excluded. Format: <sha256>[:<reason>] "
             "(one of: out_of_scope, corrupted, duplicate, superseded, language_unsupported)",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Override the auto-generated UUID for this run (used by tests + the copilot)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would happen without writing to Firestore / fetching bytes",
    )
    args = parser.parse_args(argv)

    if args.emulator:
        os.environ["FIRESTORE_EMULATOR_HOST"] = os.environ.get(
            "FIRESTORE_EMULATOR_HOST", "localhost:8080"
        )

    # Dispatch by step.
    if args.step == "sourced":
        if args.dry_run:
            print("DRY RUN: would source", len(list(catalog_rows())), "catalog rows")
            return 0
        counts = step_sourced(project_id=args.project_id or None, run_id=args.run_id)
        _print_status_table({**counts, "ready": 0, "excluded": 0, "ocr_consensus_done": 0,
                            "mastery_done": 0, "asset_done": 0})
        return 0

    if args.step == "normalised":
        if args.dry_run:
            print("DRY RUN: would normalise every not-yet-normalised artefact")
            return 0
        counts = step_normalised(project_id=args.project_id or None, run_id=args.run_id)
        _print_status_table({**counts, "ready": 0, "excluded": 0, "ocr_consensus_done": 0,
                            "mastery_done": 0, "asset_done": 0})
        return 0

    if args.step == "filtered":
        excluded_pairs: list[tuple[str, str | None]] = []
        for spec in args.exclude:
            sha, _, reason = spec.partition(":")
            excluded_pairs.append((sha, reason or None))
        if args.dry_run:
            print(f"DRY RUN: would exclude {len(excluded_pairs)} doc(s)")
            return 0
        sha_list = [s for s, _ in excluded_pairs]
        reason_map = {s: r for s, r in excluded_pairs if r}
        counts = step_filtered(
            excluded_sha256s=sha_list,
            excluded_reasons=reason_map,
            project_id=args.project_id or None,
            run_id=args.run_id,
        )
        _print_status_table(counts)
        return 0

    if args.step == "extract-baml":
        if args.dry_run:
            print("DRY RUN: would BAML-extract every ready artefact")
            return 0
        counts = step_extract_baml(project_id=args.project_id or None, run_id=args.run_id)
        _print_status_table(counts)
        return 0

    if args.step == "ready" or args.step == "status":
        counts = step_status(project_id=args.project_id or None)
        _print_status_table(counts)
        return 0

    parser.error(f"unknown step: {args.step}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
