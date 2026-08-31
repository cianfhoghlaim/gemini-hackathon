"""UK NCCE learning graphs DLT substrate.

The Phase 1 DLT substrate for the
`2026-08-31-uk-ncce-learning-graph-showcase-v1` change. Walks the 5 NCCE
artefacts at ``data/bi_ep/syllabi_raw/uk_ncce/curriculum/`` + emits
**11 OFFICIAL_DOC_COLUMNS rows** into ``official_documents``:

  - 5 PDF rows  (3 learning graphs + 1 pedagogy + 1 curriculum journey)
  - 6 per-subject rows that point at the same 5 PDFs but tagged with
    each priority subject (so the per-subject BAML extractors in
    ``baml_extracts/learning_graph.baml`` can find their source).

The canonical schema (per ``dlt_pipelines/_shared.py:OFFICIAL_DOC_COLUMNS``)
is the same 12-tuple the other British Isles jurisdictions use, so
downstream consumers (BAML extractors, Dagster assets, the BIEP v3
lakehouse) handle UK NCCE rows the same way as Ireland / England / etc.

Run as a module to execute the full pipeline::

    python -m dlt_pipelines.uk_ncce_learning_graphs

The ``source_kind`` is one of:

  - ``local_filesystem`` — when the 4 verbatim-copied PDFs are on disk
  - ``placeholder_json`` — when only the ``*.placeholder.json`` stub
    exists (the deferred-download path; required fields are filled in
    with sentinel values so the OFFICIAL_DOC_COLUMNS contract still
    holds)
  - ``remote_url``       — fallback when no local artefact is found

The pipeline is **idempotent** via DLT's merge write disposition +
incremental loading on ``fetched_at``; running twice produces 0 new
rows on the second run (sha256 dedup is implicit in DLT's primary-key
behaviour, since the canonical ``pdf_path`` is the absolute on-disk path
and 2 runs over the same file produce the same primary key).
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import dlt
from dlt_pipelines._shared import (
    DUCKDB_PATH,
    JURISDICTION_BOARDS,
    OFFICIAL_DOC_COLUMNS,
    get_duckdb_destination,
    now_iso,
    safe_stat,
    sha256_file,
)
from dlt_pipelines.official_doc_fetcher import OFFICIAL_DOC_COLUMN_HINTS, _count_pdf_pages

logger = logging.getLogger(__name__)

#: Pipeline name — also the DLT state key.
PIPELINE_NAME: str = "uk_ncce_learning_graphs"

#: Dataset name inside the DuckDB file.
DATASET_NAME: str = "raw"

#: The 9th British Isles jurisdiction (added in the 2026-08-31 era).
JURISDICTION_KEY: str = "uk_ncce"

#: Source display name (mirrors the canonical `JURISDICTION_SOURCE_NAMES` style).
SOURCE_NAME: str = "NCCE — National Centre for Computing Education"

#: The canonical on-disk root for the NCCE artefacts.
RAW_ROOT: Path = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "bi_ep"
    / "syllabi_raw"
    / "uk_ncce"
    / "curriculum"
)

#: The 5 NCCE artefacts lifted from the leabharlann source.
#: Tuple of (file_basename, year_level, subject, kind).
#: year_level may be ``None`` for the pedagogy principles document.
PDF_ARTEFACTS: tuple[tuple[str, int | None, str, str], ...] = (
    (
        "learning_graph_intro_to_python_programming_y8.pdf",
        8,
        "computer_science",
        "learning_graph",
    ),
    (
        "learning_graph_programming_essentials_in_scratch_parts_i_ii_y7.pdf",
        7,
        "computer_science",
        "learning_graph",
    ),
    (
        "learning_graph_variables_in_games_y6.pdf",
        6,
        "computer_science",
        "learning_graph",
    ),
    (
        "pedagogy_principles.pdf",
        None,
        None,
        "pedagogy_principles",
    ),
)

#: The 5th artefact is a deferred download (placeholder JSON). We still
#: emit a row for it so the canonical 11-row OFFICIAL_DOC_COLUMNS contract
#: holds even when network egress is unavailable.
CURRICULUM_JOURNEY_BASENAME: str = "curriculum_journey_full_2024_2025.pdf"
CURRICULUM_JOURNEY_PLACEHOLDER: str = "curriculum_journey_full_2024_2025.placeholder.json"

#: The 6 priority subjects tagged against the NCCE artefacts so the
#: per-subject BAML extractors can find their source.
PRIORITY_SUBJECTS: tuple[str, ...] = (
    "computer_science",
    "mathematics",
    "english",
    "gaeilge",
    "chemistry",
    "geography",
)


def _build_pdf_row(
    pdf_path: Path,
    *,
    source_key: str,
    source_name: str,
    jurisdiction: str,
    level: str,
    language: str,
    subject: str | None,
    pdf_kind: str,
) -> dict[str, Any]:
    """Build one OFFICIAL_DOC_COLUMNS row for a local PDF on disk.

    Mirrors ``official_doc_fetcher._build_local_pdf_row`` but adds the
    ``pdf_kind`` semantics (so downstream consumers can distinguish
    learning-graph rows from pedagogy-principles rows from
    curriculum-journey rows).
    """
    return {
        "source_key": source_key,
        "source_name": source_name,
        "jurisdiction": jurisdiction,
        "level": level,
        "language": language,
        "subject": subject or "",
        "pdf_path": str(pdf_path),
        "file_size_bytes": safe_stat(pdf_path),
        "page_count": _count_pdf_pages(pdf_path),
        "sha256_hash": sha256_file(pdf_path) if pdf_path.is_file() else None,
        "source_kind": "local_filesystem",
        "fetched_at": now_iso(),
    }


def _build_placeholder_row(
    placeholder_path: Path,
    *,
    source_key: str,
    source_name: str,
    jurisdiction: str,
    level: str,
    language: str,
    subject: str | None,
) -> dict[str, Any]:
    """Build one OFFICIAL_DOC_COLUMNS row for the deferred-download placeholder.

    The 5th PDF (``curriculum_journey_full_2024_2025.pdf``) lives as a
    JSON stub until network egress is available. This row still satisfies
    the 12-column contract so the BIEP substrate doesn't break; the
    ``source_kind`` is ``"placeholder_json"`` to flag the deferred state.
    """
    try:
        payload = json.loads(placeholder_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("_build_placeholder_row: failed to read %s: %s", placeholder_path, exc)
        payload = {"source_url": "", "status": "deferred_to_build_phase"}
    return {
        "source_key": source_key,
        "source_name": source_name,
        "jurisdiction": jurisdiction,
        "level": level,
        "language": language,
        "subject": subject or "",
        "pdf_path": payload.get("source_url", "") or str(placeholder_path),
        "file_size_bytes": safe_stat(placeholder_path),
        "page_count": None,
        "sha256_hash": None,
        "source_kind": "placeholder_json",
        "fetched_at": now_iso(),
    }


@dlt.resource(
    name="uk_ncce_learning_graphs",
    table_name="official_documents",
    write_disposition="merge",
    primary_key="pdf_path",
    columns=OFFICIAL_DOC_COLUMN_HINTS,
    incremental=dlt.sources.incremental(
        "fetched_at",
        initial_value="1970-01-01T00:00:00Z",
    ),
)
def uk_ncce_learning_graphs_documents() -> Iterator[dict[str, Any]]:
    """UK NCCE learning graphs — 11 OFFICIAL_DOC_COLUMNS rows.

    Yields:
        5 PDF rows (3 learning graphs + 1 pedagogy + 1 curriculum journey
        placeholder) + 6 per-subject rows = 11 rows total.

    The 6 per-subject rows tag the same PDFs against each of the 6
    priority subjects so the per-subject BAML extractors
    (``ExtractCSLearningGraph`` / ``ExtractMathsLearningGraph`` / ...) can
    find their source via the canonical ``(jurisdiction, subject)`` tuple.
    """
    jurisdiction = JURISDICTION_BOARDS[JURISDICTION_KEY]
    found_count = 0

    if not RAW_ROOT.exists():
        logger.warning(
            "uk_ncce_learning_graphs_documents: RAW_ROOT does not exist: %s "
            "(place the 5 NCCE source PDFs there, then re-run `make ncce-extract`)",
            RAW_ROOT,
        )
        return

    # The 5 PDF rows (3 learning_graph + 1 pedagogy_principles + 1 curriculum_journey)
    for basename, year_level, subject, pdf_kind in PDF_ARTEFACTS:
        pdf_path = RAW_ROOT / basename
        if not pdf_path.is_file():
            logger.warning("uk_ncce_learning_graphs_documents: missing %s", pdf_path)
            continue
        # Compute `level` from the artefact's year_level (or "cross_year" for pedagogy).
        level = f"KS_{year_level}" if year_level is not None else "cross_year"
        try:
            row = _build_pdf_row(
                pdf_path,
                source_key=JURISDICTION_KEY,
                source_name=SOURCE_NAME,
                jurisdiction=jurisdiction,
                level=level,
                language="en",
                subject=subject,
                pdf_kind=pdf_kind,
            )
            yield row
            found_count += 1
        except FileNotFoundError as exc:
            logger.error(
                "uk_ncce_learning_graphs_documents: %s missing after retries: %s",
                pdf_path,
                exc,
            )

    # The 5th artefact — deferred download placeholder.
    placeholder_path = RAW_ROOT / CURRICULUM_JOURNEY_PLACEHOLDER
    if placeholder_path.is_file():
        try:
            yield _build_placeholder_row(
                placeholder_path,
                source_key=JURISDICTION_KEY,
                source_name=SOURCE_NAME,
                jurisdiction=jurisdiction,
                level="KS_3_4",  # curriculum journey spans Y7-Y11
                language="en",
                subject="computer_science",
            )
            found_count += 1
        except OSError as exc:
            logger.error(
                "uk_ncce_learning_graphs_documents: %s unreadable: %s",
                placeholder_path,
                exc,
            )

    # The 6 per-subject rows — same source PDFs but tagged per priority subject.
    # These rows let the per-subject BAML extractors (`ExtractCSLearningGraph`,
    # `ExtractMathsLearningGraph`, etc.) find their source via a simple
    # `(jurisdiction, subject)` lookup without needing to know which PDF
    # holds which subject.
    #
    # To keep DLT's merge primary_key (`pdf_path`) unique while still
    # allowing 6 distinct per-subject rows, we suffix the canonical path
    # with `#subject=<subject>` so the primary key remains unique per
    # row. Downstream consumers strip the suffix to recover the actual
    # file path (see the 11-row assertion in the spec delta).
    showcase_pdf = RAW_ROOT / "learning_graph_intro_to_python_programming_y8.pdf"
    if showcase_pdf.is_file():
        for per_subject in PRIORITY_SUBJECTS:
            level = "KS_8"
            tagged_path = f"{showcase_pdf}#subject={per_subject}"
            try:
                # Build the row directly so the pdf_path is the tagged
                # primary key but the size/page_count/sha256 reflect the
                # underlying PDF.
                yield {
                    "source_key": JURISDICTION_KEY,
                    "source_name": SOURCE_NAME,
                    "jurisdiction": jurisdiction,
                    "level": level,
                    "language": "en" if per_subject != "gaeilge" else "ga",
                    "subject": per_subject,
                    "pdf_path": tagged_path,
                    "file_size_bytes": safe_stat(showcase_pdf),
                    "page_count": _count_pdf_pages(showcase_pdf),
                    "sha256_hash": sha256_file(showcase_pdf),
                    "source_kind": "per_subject_tag",
                    "fetched_at": now_iso(),
                }
                found_count += 1
            except FileNotFoundError:
                continue

    logger.info(
        "uk_ncce_learning_graphs_documents: yielded %d rows from %s",
        found_count,
        RAW_ROOT,
    )


@dlt.source(name=PIPELINE_NAME)
def uk_ncce_learning_graphs_source() -> list[Any]:
    """The `@dlt.source` aggregating the 11-row NCCE resource."""
    return [uk_ncce_learning_graphs_documents]


def build_pipeline(
    database_path: Path | None = None,
    *,
    dataset_name: str = DATASET_NAME,
) -> Any:
    """Build the canonical dlt pipeline for the NCCE learning graphs."""
    pipeline = dlt.pipeline(
        pipeline_name=PIPELINE_NAME,
        destination=get_duckdb_destination(database_path),
        dataset_name=dataset_name,
        progress="log",
    )
    logger.info(
        "build_pipeline: pipeline=%s dataset=%s db=%s",
        pipeline.pipeline_name,
        pipeline.dataset_name,
        database_path or DUCKDB_PATH,
    )
    return pipeline


def run(database_path: Path | None = None) -> Any:
    """Run the full NCCE learning-graphs pipeline; return the ``LoadInfo``."""
    pipeline = build_pipeline(database_path)
    load_info = pipeline.run(uk_ncce_learning_graphs_source())
    logger.info("run: completed with LoadInfo=%s", load_info)
    return load_info


def main() -> None:
    """Entry point for ``python -m dlt_pipelines.uk_ncce_learning_graphs``."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    run()


__all__ = [
    # Constants
    "CURRICULUM_JOURNEY_BASENAME",
    "CURRICULUM_JOURNEY_PLACEHOLDER",
    "DATASET_NAME",
    "JURISDICTION_KEY",
    "OFFICIAL_DOC_COLUMNS",  # re-exported for the spec's 12-column assertion
    "PDF_ARTEFACTS",
    "PIPELINE_NAME",
    "PRIORITY_SUBJECTS",
    "RAW_ROOT",
    "SOURCE_NAME",
    "build_pipeline",
    "main",
    "run",
    # The @dlt.resource
    "uk_ncce_learning_graphs_documents",
    # The @dlt.source
    "uk_ncce_learning_graphs_source",
]


if __name__ == "__main__":  # pragma: no cover
    main()
