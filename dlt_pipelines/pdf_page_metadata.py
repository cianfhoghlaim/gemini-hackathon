"""PDF page metadata extractor — downstream of `official_doc_fetcher`.

Reads the rows already written by `official_doc_fetcher.run()` (the
`official_documents` table in `gemini_hackathon.duckdb`), opens each
local PDF with `pypdf`, and extracts:

- `page_count`        — number of pages
- `fonts_detected`    — set of font names referenced across all pages
- `image_count`       — number of embedded `XObject` images
- `has_text_layer`    — True if any page has extractable text
- `file_size_bytes`   — from pathlib.stat
- `extracted_at`      — UTC ISO-8601

The output is one row per PDF into the `pdf_metadata` table. Run as a
module to execute the full pipeline:

    python -m dlt_pipelines.pdf_page_metadata

The extractor only processes **local filesystem PDFs** (i.e.
`source_kind == "local_filesystem"`). Remote-URL rows are skipped — they
need to be downloaded first by a separate fetch pass.

Honours:
- Per dignified-python-312: narrow exceptions, explicit `if x is None`,
  no bare `except`.
- Uses `pypdf` lazily (declared in `requirements.txt`).
- Falls back gracefully when a PDF is corrupt / locked / has no text layer.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import dlt

from dlt_pipelines._shared import (
    DUCKDB_PATH,
    get_duckdb_destination,
    now_iso,
    safe_stat,
    sha256_file,
    with_retry,
)

logger = logging.getLogger(__name__)

#: Pipeline name — also the DLT state key.
PIPELINE_NAME: str = "pdf_metadata"

#: Dataset name inside the DuckDB file.
DATASET_NAME: str = "raw"

#: Default DuckDB filename — same file the official_doc_fetcher writes to.
DEFAULT_DATABASE_PATH: Path = DUCKDB_PATH

#: DuckDB dataset/schema holding the upstream `official_documents` rows.
UPSTREAM_DATASET_NAME: str = "raw"

#: Upstream table name produced by `official_doc_fetcher`.
UPSTREAM_TABLE_NAME: str = "official_documents"

#: Explicit per-column type hints for the `pdf_metadata` table.
#: Prevents dlt from warning about column types on partial-data loads.
#: NOTE: `fonts_detected` is intentionally NOT hinted — it's a list of
#: strings, which dlt auto-nests into a child table `pdf_metadata__fonts_detected`.
PDF_METADATA_COLUMN_HINTS: dict[str, dict[str, str]] = {
    "pdf_path": {"data_type": "text"},
    "source_key": {"data_type": "text"},
    "sha256_hash": {"data_type": "text"},
    "page_count": {"data_type": "bigint"},
    "image_count": {"data_type": "bigint"},
    "has_text_layer": {"data_type": "bool"},
    "file_size_bytes": {"data_type": "bigint"},
    "extracted_at": {"data_type": "timestamp"},
}


# ---------------------------------------------------------------------------
# pypdf-based metadata extraction
# ---------------------------------------------------------------------------


def _scan_page_for_fonts(page: Any, pdf_path: Path) -> set[str]:
    """Return the set of font names referenced in this PDF page.

    Returns an empty set if the page has no readable `/Resources` or no
    `/Font` dictionary. Logs (at debug) and swallows any structural error.
    """
    try:
        resources = page.get("/Resources", {}) or {}
    except (KeyError, AttributeError, ValueError) as exc:
        logger.debug(
            "_scan_page_for_fonts: /Resources missing for %s page %s: %s",
            pdf_path,
            page,
            exc,
        )
        return set()

    if not isinstance(resources, dict):
        return set()
    fonts_obj = resources.get("/Font", {}) or {}
    if not isinstance(fonts_obj, dict):
        return set()
    return {name for name in fonts_obj if isinstance(name, str)}


def _count_images_in_page(page: Any) -> int:
    """Return the number of embedded `/Image` XObjects on this PDF page."""
    if not hasattr(page, "get"):
        return 0
    try:
        resources = page.get("/Resources", {}) or {}
    except (KeyError, AttributeError, ValueError):
        return 0
    if not isinstance(resources, dict):
        return 0
    xobjects = resources.get("/XObject", {}) or {}
    if not isinstance(xobjects, dict):
        return 0
    return sum(
        1 for v in xobjects.values() if isinstance(v, dict) and v.get("/Subtype") == "/Image"
    )


def _page_has_text(page: Any) -> bool:
    """Return True if the PDF page has any extractable text content."""
    if not hasattr(page, "extract_text"):
        return False
    try:
        text = page.extract_text() or ""
    except (KeyError, ValueError, OSError):
        return False
    return text.strip() != ""


def _extract_pdf_metadata(
    pdf_path: Path,
) -> dict[str, Any]:
    """Open `pdf_path` with pypdf and extract the canonical PDF_METADATA_COLUMNS fields.

    Returns a partial dict with the fields that could be extracted; missing
    fields default to `None` or empty list. Never raises — failures are
    logged + swallowed so a corrupt PDF doesn't kill the whole pipeline.
    """
    metadata: dict[str, Any] = {
        "page_count": None,
        "fonts_detected": [],
        "image_count": 0,
        "has_text_layer": False,
        "file_size_bytes": safe_stat(pdf_path),
    }

    try:
        from pypdf import PdfReader  # noqa: PLC0415 — pypdf is an optional dependency
    except ImportError:
        logger.warning("_extract_pdf_metadata: pypdf not installed — fields will be empty")
        return metadata

    try:
        reader = PdfReader(str(pdf_path))
    except (OSError, ValueError) as exc:
        logger.warning("_extract_pdf_metadata: cannot open %s: %s", pdf_path, exc)
        return metadata

    pages = reader.pages
    metadata["page_count"] = len(pages)

    fonts_seen: set[str] = set()
    image_count = 0
    has_text = False
    for page in pages:
        fonts_seen |= _scan_page_for_fonts(page, pdf_path)
        image_count += _count_images_in_page(page)
        if _page_has_text(page):
            has_text = True

    metadata["fonts_detected"] = sorted(fonts_seen)
    metadata["image_count"] = image_count
    metadata["has_text_layer"] = has_text
    return metadata


# ---------------------------------------------------------------------------
# Upstream-row resolver
# ---------------------------------------------------------------------------


@with_retry(attempts=3, backoff_seconds=0.1, retry_on=(FileNotFoundError, OSError))
def _resolve_upstream_local_rows(
    database_path: Path,
    *,
    dataset_name: str,
    table_name: str,
) -> list[dict[str, Any]]:
    """Read the `source_kind == 'local_filesystem'` rows from the upstream DuckDB table.

    Returns a list of dicts with at minimum: `pdf_path`, `source_key`,
    `sha256_hash`. Connects to the DuckDB file directly via `duckdb`
    (NOT via MotherDuck — this runs on a workstation).
    """
    try:
        import duckdb  # noqa: PLC0415 — duckdb is an optional dependency
    except ImportError:
        logger.error(
            "_resolve_upstream_local_rows: duckdb not installed; install with `uv add duckdb`"
        )
        return []

    if not database_path.exists():
        logger.error(
            "_resolve_upstream_local_rows: DuckDB file not found: %s "
            "(did you run `official_doc_fetcher.run()` first?)",
            database_path,
        )
        return []

    conn = duckdb.connect(str(database_path), read_only=True)
    try:
        # Fully-qualify the schema + table to avoid DuckDB ambiguity.
        rows = conn.execute(
            f"""
            SELECT source_key, pdf_path, sha256_hash, file_size_bytes
            FROM {dataset_name}.{table_name}
            WHERE source_kind = 'local_filesystem'
            ORDER BY pdf_path
            """
        ).fetchall()
    finally:
        conn.close()

    out: list[dict[str, Any]] = []
    for source_key, pdf_path, sha256_hash, file_size_bytes in rows:
        out.append(
            {
                "source_key": source_key,
                "pdf_path": pdf_path,
                "sha256_hash": sha256_hash,
                "file_size_bytes": file_size_bytes,
            }
        )
    return out


# ---------------------------------------------------------------------------
# The @dlt.resource
# ---------------------------------------------------------------------------


@dlt.resource(
    name="pdf_metadata",
    table_name="pdf_metadata",
    write_disposition="merge",
    primary_key="pdf_path",
    columns=PDF_METADATA_COLUMN_HINTS,
    incremental=dlt.sources.incremental(
        "extracted_at",
        initial_value="1970-01-01T00:00:00Z",
    ),
)
def pdf_metadata_resource(
    database_path: Path | None = None,
    *,
    dataset_name: str = UPSTREAM_DATASET_NAME,
    table_name: str = UPSTREAM_TABLE_NAME,
) -> Iterator[dict[str, Any]]:
    """Read upstream `official_documents` rows and emit one row per local PDF.

    Args:
        database_path: Path to the DuckDB file (defaults to `DEFAULT_DATABASE_PATH`).
        dataset_name: DuckDB dataset/schema (defaults to `UPSTREAM_DATASET_NAME`).
        table_name: Upstream table name (defaults to `UPSTREAM_TABLE_NAME`).
    """
    db_path = database_path or DEFAULT_DATABASE_PATH

    upstream_rows = _resolve_upstream_local_rows(
        db_path,
        dataset_name=dataset_name,
        table_name=table_name,
    )
    logger.info(
        "pdf_metadata_resource: %d local-FS PDFs to process from %s",
        len(upstream_rows),
        db_path,
    )

    for upstream in upstream_rows:
        pdf_path_str = upstream.get("pdf_path")
        if pdf_path_str is None:
            continue
        pdf_path = Path(pdf_path_str)
        if not pdf_path.exists() or not pdf_path.is_file():
            logger.warning("pdf_metadata_resource: skipping missing file %s", pdf_path)
            continue

        # Verify SHA256 still matches — protects against silent file mutation.
        try:
            observed_hash = sha256_file(pdf_path)
        except (FileNotFoundError, OSError) as exc:
            logger.warning("pdf_metadata_resource: sha256 failed for %s: %s", pdf_path, exc)
            continue

        upstream_hash = upstream.get("sha256_hash")
        if upstream_hash is not None and observed_hash != upstream_hash:
            logger.warning(
                "pdf_metadata_resource: sha256 mismatch for %s "
                "(upstream=%s observed=%s) — file was mutated since fetch",
                pdf_path,
                upstream_hash,
                observed_hash,
            )

        meta = _extract_pdf_metadata(pdf_path)
        yield {
            "pdf_path": str(pdf_path),
            "source_key": upstream.get("source_key"),
            "sha256_hash": observed_hash,
            "page_count": meta["page_count"],
            "fonts_detected": meta["fonts_detected"],
            "image_count": meta["image_count"],
            "has_text_layer": meta["has_text_layer"],
            "file_size_bytes": meta["file_size_bytes"],
            "extracted_at": now_iso(),
        }


# ---------------------------------------------------------------------------
# The @dlt.source
# ---------------------------------------------------------------------------


@dlt.source(name="pdf_metadata")
def pdf_metadata_source(
    database_path: Path | None = None,
    *,
    dataset_name: str = UPSTREAM_DATASET_NAME,
    table_name: str = UPSTREAM_TABLE_NAME,
) -> list[Any]:
    """The `@dlt.source` wrapping the single `pdf_metadata_resource`."""
    return [
        pdf_metadata_resource(
            database_path,
            dataset_name=dataset_name,
            table_name=table_name,
        )
    ]


# ---------------------------------------------------------------------------
# Pipeline factory + __main__ entrypoint
# ---------------------------------------------------------------------------


def build_pipeline(
    database_path: Path | None = None,
    *,
    dataset_name: str = DATASET_NAME,
) -> Any:
    """Build the canonical `dlt.pipeline` for the pdf_metadata source.

    Note the destination DuckDB file is the SAME file as the official_doc_fetcher
    pipeline uses — they share the lakehouse.
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
        database_path or DEFAULT_DATABASE_PATH,
    )
    return pipeline


def run(
    database_path: Path | None = None,
    *,
    upstream_dataset: str = UPSTREAM_DATASET_NAME,
    upstream_table: str = UPSTREAM_TABLE_NAME,
) -> Any:
    """Run the pdf_metadata pipeline; return the `LoadInfo`."""
    pipeline = build_pipeline(database_path)
    load_info = pipeline.run(
        pdf_metadata_source(
            database_path,
            dataset_name=upstream_dataset,
            table_name=upstream_table,
        )
    )
    logger.info("run: completed with LoadInfo=%s", load_info)
    return load_info


def main() -> None:
    """Entry point for `python -m dlt_pipelines.pdf_page_metadata`."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    run()


__all__ = [
    "DATASET_NAME",
    "DEFAULT_DATABASE_PATH",
    "PDF_METADATA_COLUMN_HINTS",
    # Constants
    "PIPELINE_NAME",
    "UPSTREAM_DATASET_NAME",
    "UPSTREAM_TABLE_NAME",
    # PDF extractor helper (re-exported for testing)
    "_extract_pdf_metadata",
    "_resolve_upstream_local_rows",
    # Pipeline factory + runner
    "build_pipeline",
    "main",
    # The single @dlt.resource
    "pdf_metadata_resource",
    # The @dlt.source wrapper
    "pdf_metadata_source",
    "run",
]


if __name__ == "__main__":  # pragma: no cover
    main()
