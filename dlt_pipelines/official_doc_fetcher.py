"""Official document fetcher — the 8 British Isles jurisdiction pipelines.

The flagship `dlt_pipelines/official_doc_fetcher.py` module.

For each of the **8 BI jurisdictions + 5 safeguarding bodies** (13 sources
total; this file owns the 8 jurisdictional ones — see
`dlt_pipelines/safeguarding_fetcher.py` for the 5 safeguarding ones), this
module emits one DLT `@dlt.resource` that yields the canonical
`OFFICIAL_DOC_COLUMNS` row schema:

    source_key, source_name, jurisdiction, level, language,
    subject, pdf_path, file_size_bytes, page_count, sha256_hash,
    source_kind, fetched_at

The Ireland (NCCA) resource is **filesystem-based** — it scans the local
`leaving_certificate/{subject}/{en|ga}/*.pdf` directory tree (the canonical
BIEP corpus) and computes SHA256 + page_count per PDF.

The remaining 7 jurisdictions are **remote-URL-based** — they yield
catalog rows from a curated `KNOWN_OFFICIAL_URLS` dict so the schema is
uniform and downstream BAML extraction can resolve them later.

Run as a module to execute the full pipeline:
    python -m dlt_pipelines.official_doc_fetcher
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import dlt

from dlt_pipelines._shared import (
    DUCKDB_PATH,
    JURISDICTION_BOARDS,
    LC_LANGUAGE_DIRS,
    LC_SUBJECT_DIRS,
    LC_SUBJECTS_PATH,
    get_duckdb_destination,
    now_iso,
    safe_stat,
    sha256_file,
    with_retry,
)

logger = logging.getLogger(__name__)

#: Pipeline name — also the DLT state key.
PIPELINE_NAME: str = "official_documents"

#: Dataset name inside the DuckDB file.
DATASET_NAME: str = "raw"


# ---------------------------------------------------------------------------
# Column type hints (silence dlt's "no data" warning on remote-URL rows)
# ---------------------------------------------------------------------------

#: Explicit per-column type hints for the `official_documents` table.
#: Prevents dlt from warning about columns that are always-None on
#: remote-URL rows (e.g. `file_size_bytes`, `page_count`, `sha256_hash`).
OFFICIAL_DOC_COLUMN_HINTS: dict[str, dict[str, str]] = {
    "source_key": {"data_type": "text"},
    "source_name": {"data_type": "text"},
    "jurisdiction": {"data_type": "text"},
    "level": {"data_type": "text"},
    "language": {"data_type": "text"},
    "subject": {"data_type": "text"},
    "pdf_path": {"data_type": "text"},
    "file_size_bytes": {"data_type": "bigint"},
    "page_count": {"data_type": "bigint"},
    "sha256_hash": {"data_type": "text"},
    "source_kind": {"data_type": "text"},
    "fetched_at": {"data_type": "timestamp"},
}


# ---------------------------------------------------------------------------
# Canonical metadata for the 8 jurisdictional sources
# ---------------------------------------------------------------------------

#: Per-source display name (mirrors `gemini_hackathon.theming.themes/*.json`).
JURISDICTION_SOURCE_NAMES: dict[str, str] = {
    "ncca.ie": "NCCA — National Council for Curriculum and Assessment",
    "aqa.org.uk": "AQA — Assessment and Qualifications Alliance",
    "ocr.org.uk": "OCR — Oxford Cambridge and RSA Examinations",
    "qualifications.pearson.com": "Pearson Edexcel",
    "sqa.org.uk": "SQA — Scottish Qualifications Authority",
    "wjec.co.uk": "WJEC — Welsh Joint Education Committee",
    "ccea.org.uk": "CCEA — Council for the Curriculum, Examinations & Assessment",
    "gov.im/education": "Isle of Man Department of Education, Sport and Culture",
}

#: Per-source canonical curriculum level.
JURISDICTION_LEVELS: dict[str, str] = {
    "ncca.ie": "LC",
    "aqa.org.uk": "A-Level",
    "ocr.org.uk": "GCSE-A",
    "qualifications.pearson.com": "A-Level",
    "sqa.org.uk": "National_5",
    "wjec.co.uk": "A-Level",
    "ccea.org.uk": "A-Level",
    "gov.im/education": "GCSE",
}

#: Per-resource short name (the DLT resource.name + table_name).
RESOURCE_NAMES: dict[str, str] = {
    "ncca.ie": "ireland_ncca",
    "aqa.org.uk": "england_aqa",
    "ocr.org.uk": "england_ocr",
    "qualifications.pearson.com": "england_pearson",
    "sqa.org.uk": "scotland_sqa",
    "wjec.co.uk": "wales_wjec",
    "ccea.org.uk": "northern_ireland_ccea",
    "gov.im/education": "isle_of_man",
}

#: Ireland NCCA LC subject directories + canonical level for each.
IRELAND_LC_LEVELS: dict[str, str] = {
    "accounting": "LC",
    "applied_mathematics": "LC",
    "art": "LC",
    "biology": "LC",
    "business": "LC",
    "chemistry": "LC",
    "computer_science": "LC",
    "english": "LC",
    "french": "LC",
    "gaeilge": "LC",
    "geography": "LC",
    "history": "LC",
    "mathematics": "LC",
    "music": "LC",
    "physics": "LC",
    "technology": "LC",
    "ukrainian": "LC",
}


# ---------------------------------------------------------------------------
# Known-URL catalog for the 7 non-Ireland jurisdictions
# ---------------------------------------------------------------------------

#: Canonical "specification" PDFs per jurisdiction. These are NOT downloaded
#: by this pipeline — they're yielded as catalog rows so the BAML
#: `ExtractSourcePalette` runner can fetch them later. Tuple per source:
#: `(subject, language, official_url, source_name_override)`.
KNOWN_OFFICIAL_URLS: dict[str, list[dict[str, str]]] = {
    "aqa.org.uk": [
        {
            "subject": "mathematics",
            "language": "en",
            "official_url": (
                "https://www.aqa.org.uk/subjects/mathematics/a-level/mathematics-7357"
            ),
        },
        {
            "subject": "chemistry",
            "language": "en",
            "official_url": ("https://www.aqa.org.uk/subjects/chemistry/a-level/chemistry-7404"),
        },
        {
            "subject": "biology",
            "language": "en",
            "official_url": ("https://www.aqa.org.uk/subjects/biology/a-level/biology-7401"),
        },
        {
            "subject": "english",
            "language": "en",
            "official_url": (
                "https://www.aqa.org.uk/subjects/english/a-level/english-literature-b-7716"
            ),
        },
    ],
    "ocr.org.uk": [
        {
            "subject": "computer_science",
            "language": "en",
            "official_url": (
                "https://www.ocr.org.uk/qualifications/as-and-a-level/"
                "computer-science-h046-h446-from-2015/"
            ),
        },
        {
            "subject": "geography",
            "language": "en",
            "official_url": (
                "https://www.ocr.org.uk/qualifications/as-and-a-level/"
                "geography-h081-h481-from-2016/"
            ),
        },
    ],
    "qualifications.pearson.com": [
        {
            "subject": "mathematics",
            "language": "en",
            "official_url": (
                "https://qualifications.pearson.com/en/qualifications/"
                "edexcel-a-levels/mathematics-2017.html"
            ),
        },
        {
            "subject": "history",
            "language": "en",
            "official_url": (
                "https://qualifications.pearson.com/en/qualifications/"
                "edexcel-a-levels/history-2015.html"
            ),
        },
    ],
    "sqa.org.uk": [
        {
            "subject": "mathematics",
            "language": "en",
            "official_url": ("https://www.sqa.org.uk/sqa/56950.html"),
        },
        {
            "subject": "english",
            "language": "en",
            "official_url": ("https://www.sqa.org.uk/sqa/56955.html"),
        },
        {
            "subject": "gaeilge",
            "language": "en",
            "official_url": ("https://www.sqa.org.uk/sqa/64766.html"),
        },
    ],
    "wjec.co.uk": [
        {
            "subject": "mathematics",
            "language": "en",
            "official_url": ("https://www.wjec.co.uk/qualifications/mathematics/a-level/"),
        },
        {
            "subject": "geography",
            "language": "en",
            "official_url": ("https://www.wjec.co.uk/qualifications/geography/a-level/"),
        },
        {
            "subject": "welsh",
            "language": "cy",
            "official_url": (
                "https://www.wjec.co.uk/qualifications/welsh-second-language/a-level/"
            ),
        },
    ],
    "ccea.org.uk": [
        {
            "subject": "mathematics",
            "language": "en",
            "official_url": ("https://ccea.org.uk/qualifications/gce/as-a-level-mathematics"),
        },
        {
            "subject": "chemistry",
            "language": "en",
            "official_url": ("https://ccea.org.uk/qualifications/gce/as-a-level-chemistry"),
        },
        {
            "subject": "gaeilge",
            "language": "ga",
            "official_url": ("https://ccea.org.uk/qualifications/gce/as-a-level-irish"),
        },
    ],
    "gov.im/education": [
        {
            "subject": "english",
            "language": "en",
            "official_url": ("https://www.gov.im/education/curriculum/secondary-curriculum/"),
        },
        {
            "subject": "mathematics",
            "language": "en",
            "official_url": (
                "https://www.gov.im/education/curriculum/secondary-curriculum/mathematics/"
            ),
        },
    ],
}


# ---------------------------------------------------------------------------
# PDF page-count helper (uses pypdf lazily — declared optional below)
# ---------------------------------------------------------------------------


def _count_pdf_pages(path: Path) -> int | None:
    """Return the PDF page count for `path`, or None if the PDF is unreadable.

    Uses pypdf (declared optional — see try/except ImportError). Per
    dignified-python: narrow the exception to ImportError; do not swallow
    general Exception.
    """
    try:
        from pypdf import PdfReader  # noqa: PLC0415 — pypdf is an optional dependency
    except ImportError:
        logger.warning("_count_pdf_pages: pypdf not installed — page_count will be None")
        return None
    if not path.exists() or not path.is_file():
        return None
    try:
        reader = PdfReader(str(path))
        return len(reader.pages)
    except (OSError, ValueError) as exc:
        logger.warning("_count_pdf_pages: %s failed: %s", path, exc)
        return None


@with_retry(attempts=3, backoff_seconds=0.1, retry_on=(FileNotFoundError,))
def _build_local_pdf_row(
    pdf_path: Path,
    *,
    source_key: str,
    source_name: str,
    jurisdiction: str,
    level: str,
    language: str,
    subject: str,
) -> dict[str, Any]:
    """Build one OFFICIAL_DOC_COLUMNS row for a local Ireland LC PDF."""
    return {
        "source_key": source_key,
        "source_name": source_name,
        "jurisdiction": jurisdiction,
        "level": level,
        "language": language,
        "subject": subject,
        "pdf_path": str(pdf_path),
        "file_size_bytes": safe_stat(pdf_path),
        "page_count": _count_pdf_pages(pdf_path),
        "sha256_hash": sha256_file(pdf_path),
        "source_kind": "local_filesystem",
        "fetched_at": now_iso(),
    }


def _build_remote_url_row(
    url: str,
    *,
    source_key: str,
    source_name: str,
    jurisdiction: str,
    level: str,
    language: str,
    subject: str,
) -> dict[str, Any]:
    """Build one OFFICIAL_DOC_COLUMNS row for a remote (not-yet-downloaded) URL."""
    return {
        "source_key": source_key,
        "source_name": source_name,
        "jurisdiction": jurisdiction,
        "level": level,
        "language": language,
        "subject": subject,
        "pdf_path": url,
        "file_size_bytes": None,
        "page_count": None,
        "sha256_hash": None,
        "source_kind": "remote_url",
        "fetched_at": now_iso(),
    }


# ---------------------------------------------------------------------------
# The 8 @dlt.resources (one per source_key)
# ---------------------------------------------------------------------------


@dlt.resource(
    name="ireland_ncca",
    table_name="official_documents",
    write_disposition="merge",
    primary_key="pdf_path",
    columns=OFFICIAL_DOC_COLUMN_HINTS,
    incremental=dlt.sources.incremental(
        "fetched_at",
        initial_value="1970-01-01T00:00:00Z",
    ),
)
def ireland_ncca_documents() -> Iterator[dict[str, Any]]:
    """Ireland (NCCA) — local filesystem scan of `leaving_certificate/{subject}/{en|ga}/*.pdf`.

    Walks every LC subject directory + language subdirectory and yields one
    row per PDF. Skips subject directories that don't exist (the canonical
    BIEP corpus has 17 LC subjects, but a fresh clone may have a subset).
    """
    source_key = "ncca.ie"
    source_name = JURISDICTION_SOURCE_NAMES[source_key]
    jurisdiction = JURISDICTION_BOARDS[source_key]

    subjects_root = Path(LC_SUBJECTS_PATH)
    if not subjects_root.exists():
        logger.warning(
            "ireland_ncca_documents: LC_SUBJECTS_PATH does not exist: %s "
            "(set the LC_SUBJECTS_PATH env var to override)",
            subjects_root,
        )
        return

    found_count = 0
    for subject in LC_SUBJECT_DIRS:
        subject_dir = subjects_root / subject
        if not subject_dir.exists():
            logger.debug("ireland_ncca_documents: skipping missing subject dir %s", subject_dir)
            continue

        # Try the canonical {subject}/{en|ga}/ structure first.
        pdf_dirs: list[tuple[Path, str]] = []
        for lang in LC_LANGUAGE_DIRS:
            candidate = subject_dir / lang
            if candidate.exists() and candidate.is_dir():
                pdf_dirs.append((candidate, lang))

        # Fallback: PDFs at the subject-dir level (no language subdir).
        if not pdf_dirs:
            pdf_dirs.append((subject_dir, "en"))

        for pdf_dir, language in pdf_dirs:
            for pdf_path in sorted(pdf_dir.glob("*.pdf")):
                if not pdf_path.is_file():
                    continue
                level = IRELAND_LC_LEVELS.get(subject, "LC")
                try:
                    row = _build_local_pdf_row(
                        pdf_path,
                        source_key=source_key,
                        source_name=source_name,
                        jurisdiction=jurisdiction,
                        level=level,
                        language=language,
                        subject=subject,
                    )
                    yield row
                    found_count += 1
                except FileNotFoundError as exc:
                    # Retry decorator handled the retries; this is the terminal
                    # raise. Log and continue to the next PDF.
                    logger.error(
                        "ireland_ncca_documents: %s missing after retries: %s",
                        pdf_path,
                        exc,
                    )

    logger.info(
        "ireland_ncca_documents: yielded %d rows from %s",
        found_count,
        subjects_root,
    )


def _make_remote_resource(source_key: str) -> Any:
    """Factory: build a `@dlt.resource` for one non-Ireland jurisdiction.

    Yields one catalog row per `KNOWN_OFFICIAL_URLS[source_key]` entry.
    The remote URL is recorded as `pdf_path`; size + page_count + hash are
    filled in by a downstream fetch pass.
    """
    resource_name = RESOURCE_NAMES[source_key]
    source_name = JURISDICTION_SOURCE_NAMES[source_key]
    jurisdiction = JURISDICTION_BOARDS[source_key]
    level = JURISDICTION_LEVELS[source_key]
    url_rows = KNOWN_OFFICIAL_URLS.get(source_key, [])

    @dlt.resource(
        name=resource_name,
        table_name="official_documents",
        write_disposition="merge",
        primary_key="pdf_path",
        columns=OFFICIAL_DOC_COLUMN_HINTS,
        incremental=dlt.sources.incremental(
            "fetched_at",
            initial_value="1970-01-01T00:00:00Z",
        ),
    )
    def remote_resource() -> Iterator[dict[str, Any]]:
        for url_row in url_rows:
            yield _build_remote_url_row(
                url_row["official_url"],
                source_key=source_key,
                source_name=source_name,
                jurisdiction=jurisdiction,
                level=level,
                language=url_row.get("language", "en"),
                subject=url_row.get("subject", ""),
            )
        logger.info("%s: yielded %d remote-URL catalog rows", resource_name, len(url_rows))

    return remote_resource


# Build the 7 non-Ireland resources eagerly so they're introspectable.
england_aqa_documents = _make_remote_resource("aqa.org.uk")
england_ocr_documents = _make_remote_resource("ocr.org.uk")
england_pearson_documents = _make_remote_resource("qualifications.pearson.com")
scotland_sqa_documents = _make_remote_resource("sqa.org.uk")
wales_wjec_documents = _make_remote_resource("wjec.co.uk")
northern_ireland_ccea_documents = _make_remote_resource("ccea.org.uk")
isle_of_man_documents = _make_remote_resource("gov.im/education")


# ---------------------------------------------------------------------------
# The 8-resource @dlt.source
# ---------------------------------------------------------------------------


@dlt.source(name="official_documents")
def official_documents_source() -> list[Any]:
    """The `@dlt.source` aggregating all 8 jurisdictional resources.

    Returns a list so `dlt.pipeline.run(source)` iterates every resource.
    """
    return [
        ireland_ncca_documents,
        england_aqa_documents,
        england_ocr_documents,
        england_pearson_documents,
        scotland_sqa_documents,
        wales_wjec_documents,
        northern_ireland_ccea_documents,
        isle_of_man_documents,
    ]


# ---------------------------------------------------------------------------
# Pipeline factory + __main__ entrypoint
# ---------------------------------------------------------------------------


def build_pipeline(
    database_path: Path | None = None,
    *,
    dataset_name: str = DATASET_NAME,
) -> Any:
    """Build the canonical `dlt.pipeline` for the official_documents source.

    Honourable to override `database_path` (defaults to `DUCKDB_PATH`) and
    `dataset_name` (defaults to `raw`).
    """
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
    """Run the full official_documents pipeline; return the `LoadInfo`."""
    pipeline = build_pipeline(database_path)
    load_info = pipeline.run(official_documents_source())
    logger.info("run: completed with LoadInfo=%s", load_info)
    return load_info


def main() -> None:
    """Entry point for `python -m dlt_pipelines.official_doc_fetcher`."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    run()


__all__ = [
    "DATASET_NAME",
    "IRELAND_LC_LEVELS",
    "JURISDICTION_LEVELS",
    "JURISDICTION_SOURCE_NAMES",
    "KNOWN_OFFICIAL_URLS",
    "OFFICIAL_DOC_COLUMN_HINTS",
    # Constants
    "PIPELINE_NAME",
    "RESOURCE_NAMES",
    # Pipeline factory + runner
    "build_pipeline",
    "england_aqa_documents",
    "england_ocr_documents",
    "england_pearson_documents",
    # The 8 @dlt.resources
    "ireland_ncca_documents",
    "isle_of_man_documents",
    "main",
    "northern_ireland_ccea_documents",
    # The aggregating @dlt.source
    "official_documents_source",
    "run",
    "scotland_sqa_documents",
    "wales_wjec_documents",
]
