"""`dlt_pipelines/` — the gemini_hackathon data plane.

The 13-source DLT ingestion layer that loads official jurisdiction +
safeguarding PDFs into the `gemini_hackathon.duckdb` lakehouse. Three
pipelines collaborate:

1. `official_doc_fetcher` — 8 `@dlt.resource`s for the 8 BI jurisdictions
   (Ireland + NCCA, England + AQA/OCR/Pearson, Scotland + SQA, Wales +
   WJEC, Northern Ireland + CCEA, Isle of Man). The Ireland NCCA
   resource is filesystem-based (scans the local BIEP corpus at
   `LC_SUBJECTS_PATH`); the other 7 jurisdictions emit catalog rows
   pointing at the official PDFs (to be downloaded by a downstream
   fetch pass). Writes to the `official_documents` table.

2. `safeguarding_fetcher` — 5 `@dlt.resource`s for the 5 government
   safeguarding bodies (gov.ie, gov.uk, gov.scot, gov.wales, CCEA).
   Each resource emits 3-4 catalog rows with policy_topic +
   publication_year + official_url. Writes to the
   `safeguarding_policies` table.

3. `pdf_page_metadata` — a downstream pipeline that reads the
   `official_documents` rows, opens each local PDF with `pypdf`, and
   extracts page_count + fonts_detected + image_count + has_text_layer.
   Writes to the `pdf_metadata` table (+ the auto-nested
   `pdf_metadata__fonts_detected` child table).

Per the project conventions:
- **Python 3.11+** syntax (`list[str]`, `str | None`, `dict[...]`)
- **Absolute imports** (`from dlt_pipelines.X import Y`)
- **dlt 1.x idioms** (`@dlt.resource`, `@dlt.source`, `dlt.pipeline`,
  `incremental=dlt.sources.incremental(...)`)
- **DuckDB destination** at `gemini_hackathon.duckdb` (override via
  the `DUCKDB_PATH` env var)
- **Dignified-Python-312** style (modern type hints, pathlib, explicit
  `if x is None`, narrow exceptions, no bare `except`)
- **FileNotFoundError-retry** decorator (`@with_retry`)

Run each pipeline from the repo root:
    python -m dlt_pipelines.official_doc_fetcher
    python -m dlt_pipelines.safeguarding_fetcher
    python -m dlt_pipelines.pdf_page_metadata
"""

from __future__ import annotations

# Absolute imports — per the project convention ("from dlt_pipelines.X
# import Y", not relative).
from dlt_pipelines._shared import (
    # Helpers
    DEFAULT_RETRY_ATTEMPTS,
    DEFAULT_RETRY_BACKOFF_SECONDS,
    # Project layout constants
    DUCKDB_PATH,
    # Registries
    JURISDICTION_BOARDS,
    LC_LANGUAGE_DIRS,
    LC_SUBJECT_DIRS,
    LC_SUBJECTS_PATH,
    # Column contracts
    OFFICIAL_DOC_COLUMNS,
    PDF_METADATA_COLUMNS,
    REPO_ROOT,
    SAFEGUARDING_BODIES,
    SAFEGUARDING_POLICY_COLUMNS,
    SHA256_CHUNK_BYTES,
    get_duckdb_destination,
    now_iso,
    safe_stat,
    sha256_file,
    with_retry,
)
from dlt_pipelines.official_doc_fetcher import (
    IRELAND_LC_LEVELS,
    JURISDICTION_LEVELS,
    JURISDICTION_SOURCE_NAMES,
    KNOWN_OFFICIAL_URLS,
    OFFICIAL_DOC_COLUMN_HINTS,
    RESOURCE_NAMES,
    england_aqa_documents,
    england_ocr_documents,
    england_pearson_documents,
    ireland_ncca_documents,
    isle_of_man_documents,
    northern_ireland_ccea_documents,
    official_documents_source,
    scotland_sqa_documents,
    wales_wjec_documents,
)
from dlt_pipelines.official_doc_fetcher import (
    PIPELINE_NAME as OFFICIAL_DOC_PIPELINE_NAME,
)
from dlt_pipelines.official_doc_fetcher import (
    build_pipeline as build_official_doc_pipeline,
)
from dlt_pipelines.official_doc_fetcher import (
    main as run_official_doc_main,
)
from dlt_pipelines.official_doc_fetcher import (
    run as run_official_doc,
)
from dlt_pipelines.pdf_page_metadata import (
    DEFAULT_DATABASE_PATH,
    PDF_METADATA_COLUMN_HINTS,
    UPSTREAM_DATASET_NAME,
    UPSTREAM_TABLE_NAME,
    _extract_pdf_metadata,
    _resolve_upstream_local_rows,
    pdf_metadata_resource,
    pdf_metadata_source,
)
from dlt_pipelines.pdf_page_metadata import (
    PIPELINE_NAME as PDF_METADATA_PIPELINE_NAME,
)
from dlt_pipelines.pdf_page_metadata import (
    build_pipeline as build_pdf_metadata_pipeline,
)
from dlt_pipelines.pdf_page_metadata import (
    main as run_pdf_metadata_main,
)
from dlt_pipelines.pdf_page_metadata import (
    run as run_pdf_metadata,
)
from dlt_pipelines.safeguarding_fetcher import (
    SAFEGUARDING_COLUMN_HINTS,
    SAFEGUARDING_POLICIES,
    SAFEGUARDING_RESOURCE_NAMES,
    SAFEGUARDING_SOURCE_NAMES,
    ireland_safeguarding,
    ni_ccea_safeguarding,
    safeguarding_policies_source,
    scotland_safeguarding,
    uk_dfe_safeguarding,
    wales_safeguarding,
)
from dlt_pipelines.safeguarding_fetcher import (
    build_pipeline as build_safeguarding_pipeline,
)
from dlt_pipelines.safeguarding_fetcher import (
    main as run_safeguarding_main,
)
from dlt_pipelines.safeguarding_fetcher import (
    run as run_safeguarding,
)

__version__: str = "0.1.0"

__all__ = [
    "DEFAULT_DATABASE_PATH",
    "DEFAULT_RETRY_ATTEMPTS",
    "DEFAULT_RETRY_BACKOFF_SECONDS",
    # Shared constants
    "DUCKDB_PATH",
    "IRELAND_LC_LEVELS",
    "JURISDICTION_BOARDS",
    "JURISDICTION_LEVELS",
    "JURISDICTION_SOURCE_NAMES",
    "KNOWN_OFFICIAL_URLS",
    "LC_LANGUAGE_DIRS",
    "LC_SUBJECTS_PATH",
    "LC_SUBJECT_DIRS",
    "OFFICIAL_DOC_COLUMNS",
    "OFFICIAL_DOC_COLUMN_HINTS",
    # official_doc_fetcher public surface
    "OFFICIAL_DOC_PIPELINE_NAME",
    "PDF_METADATA_COLUMNS",
    "PDF_METADATA_COLUMN_HINTS",
    # pdf_page_metadata public surface
    "PDF_METADATA_PIPELINE_NAME",
    "REPO_ROOT",
    "RESOURCE_NAMES",
    "SAFEGUARDING_BODIES",
    "SAFEGUARDING_COLUMN_HINTS",
    # safeguarding_fetcher public surface
    "SAFEGUARDING_POLICIES",
    "SAFEGUARDING_POLICY_COLUMNS",
    "SAFEGUARDING_RESOURCE_NAMES",
    "SAFEGUARDING_SOURCE_NAMES",
    "SHA256_CHUNK_BYTES",
    "UPSTREAM_DATASET_NAME",
    "UPSTREAM_TABLE_NAME",
    # Version
    "__version__",
    "_extract_pdf_metadata",
    "_resolve_upstream_local_rows",
    "build_official_doc_pipeline",
    "build_pdf_metadata_pipeline",
    "build_safeguarding_pipeline",
    "england_aqa_documents",
    "england_ocr_documents",
    "england_pearson_documents",
    # Shared helpers
    "get_duckdb_destination",
    "ireland_ncca_documents",
    "ireland_safeguarding",
    "isle_of_man_documents",
    "ni_ccea_safeguarding",
    "northern_ireland_ccea_documents",
    "now_iso",
    "official_documents_source",
    "pdf_metadata_resource",
    "pdf_metadata_source",
    "run_official_doc",
    "run_official_doc_main",
    "run_pdf_metadata",
    "run_pdf_metadata_main",
    "run_safeguarding",
    "run_safeguarding_main",
    "safe_stat",
    "safeguarding_policies_source",
    "scotland_safeguarding",
    "scotland_sqa_documents",
    "sha256_file",
    "uk_dfe_safeguarding",
    "wales_safeguarding",
    "wales_wjec_documents",
    "with_retry",
]
