"""corpus_downloader — turns the `official_documents` catalog into a real corpus.

Phase 3 of the GCP-first refactor: `official_doc_fetcher.py` yields
`source_kind="remote_url"` catalog rows (a URL + subject + jurisdiction),
but until now nothing actually fetched those URLs — the "corpus" for 7 of
the 8 non-Ireland jurisdictions was catalog-only. This module is the
missing fetch step, designed to run as the **Cloud Run Job** referenced in
`docs/DEPLOYMENT.md` (Phase 7 wires the actual Job + Cloud Scheduler
trigger).

For each `remote_url` row:
    1. GET the URL (httpx, retried via `with_retry`)
    2. Detect PDF vs HTML by `Content-Type` (a PDF-vs-landing-page split
       matters downstream — the OCR ensemble only runs on PDFs; HTML pages
       feed BAML text extraction directly)
    3. Write the bytes to `gs://<project>-biep-raw/<jurisdiction>/<subject>/
       <sha256[:16]>.<ext>` (falls back to `./data/<jurisdiction>/...` when
       `GCP_PROJECT_ID` is unset — the offline-dev path)
    4. Yield one `downloaded_documents` row (sha256, byte_size,
       content_type, storage_uri, http_status, fetched_at)

Honest about what this fetches: several crown-dependency source rows are
intentionally landing/framework pages, not per-subject specification PDFs
(see the `_index` / `_curriculum` / `_qualifications` subject slugs in
`official_doc_fetcher.KNOWN_OFFICIAL_URLS` — Jersey and Guernsey in
particular do not publish their own subject specs; they deliver
GCSE/A-Level via UK awarding bodies against a local curriculum framework).
This module fetches whatever is actually there rather than fabricating a
richer corpus than exists.

Run as a module:
    python -m dlt_pipelines.corpus_downloader
"""
from __future__ import annotations

import hashlib
import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import dlt

from dlt_pipelines._shared import (
    DUCKDB_PATH,
    gcs_uri,
    get_duckdb_destination,
    now_iso,
    with_retry,
)

logger = logging.getLogger(__name__)

PIPELINE_NAME: str = "corpus_downloader"
DATASET_NAME: str = "raw"

#: HTTP timeout per fetch (seconds). Government sites are often slow;
#: generous but bounded so a single hung request can't stall the whole job.
FETCH_TIMEOUT_SECONDS: float = 30.0

#: Requests identify themselves — several of these sites 403 bare-UA bots.
USER_AGENT: str = (
    "gemini-hackathon-biep-corpus-downloader/1.0 "
    "(+https://github.com/cianfhoghlaim/gemini-hackathon; educational research, "
    "British Isles Education Platform hackathon submission)"
)

DOWNLOADED_DOC_COLUMN_HINTS: dict[str, dict[str, str]] = {
    "source_key": {"data_type": "text"},
    "jurisdiction": {"data_type": "text"},
    "subject": {"data_type": "text"},
    "language": {"data_type": "text"},
    "source_url": {"data_type": "text"},
    "content_type": {"data_type": "text", "nullable": True},
    "byte_size": {"data_type": "bigint", "nullable": True},
    "sha256_hash": {"data_type": "text", "nullable": True},
    "storage_uri": {"data_type": "text", "nullable": True},
    "http_status": {"data_type": "bigint", "nullable": True},
    "fetch_error": {"data_type": "text", "nullable": True},
    "fetched_at": {"data_type": "timestamp"},
}


def _ext_for_content_type(content_type: str) -> str:
    """Map a Content-Type header to a file extension. Defaults to `.html`
    (most crown-dependency framework pages are HTML, not PDF)."""
    normalised = content_type.split(";", maxsplit=1)[0].strip().lower()
    return {
        "application/pdf": ".pdf",
        "text/html": ".html",
        "application/xhtml+xml": ".html",
        "text/plain": ".txt",
    }.get(normalised, ".bin")


def _write_bytes(jurisdiction: str, subject: str, sha256_prefix: str, ext: str, content: bytes) -> str:
    """Write `content` to GCS (if `GCP_PROJECT_ID` is set) or local disk
    (offline-dev fallback). Returns the storage URI (`gs://...` or a local
    path string).
    """
    filename = f"{sha256_prefix}{ext}"
    try:
        import os

        from google.cloud import storage  # noqa: PLC0415

        project_id = os.environ.get("GCP_PROJECT_ID")
        if project_id:
            uri = gcs_uri("raw", jurisdiction, subject, filename)
            bucket_name, blob_path = uri.removeprefix("gs://").split("/", 1)
            client = storage.Client(project=project_id)
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            blob.upload_from_string(content)
            logger.info("_write_bytes: wrote %d bytes to %s", len(content), uri)
            return uri
    except ImportError:
        logger.debug("_write_bytes: google-cloud-storage not installed, using local fallback")
    except Exception:
        logger.exception("_write_bytes: GCS upload failed, falling back to local disk")

    local_dir = Path("./data") / jurisdiction / subject
    local_dir.mkdir(parents=True, exist_ok=True)
    local_path = local_dir / filename
    local_path.write_bytes(content)
    logger.info("_write_bytes: wrote %d bytes to %s (local fallback)", len(content), local_path)
    return str(local_path)


@with_retry(attempts=3, backoff_seconds=1.0, retry_on=(ConnectionError, TimeoutError))
def _fetch(url: str) -> Any:
    """GET `url` with a browser-like UA + generous timeout. Retried up to
    3x on connection/timeout errors (not on 4xx/5xx — a 403/404 won't fix
    itself on retry).
    """
    import httpx  # noqa: PLC0415

    return httpx.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=FETCH_TIMEOUT_SECONDS,
        follow_redirects=True,
    )


def _build_row(source_key: str, url_row: dict[str, str], jurisdiction: str) -> dict[str, Any]:
    """Fetch one catalog row's URL and build the corresponding
    `downloaded_documents` row. Never raises — a fetch failure is recorded
    in `fetch_error`, not propagated (one bad government website must not
    abort the whole job).
    """
    url = url_row["official_url"]
    subject = url_row.get("subject", "")
    language = url_row.get("language", "en")

    base_row: dict[str, Any] = {
        "source_key": source_key,
        "jurisdiction": jurisdiction,
        "subject": subject,
        "language": language,
        "source_url": url,
        "content_type": None,
        "byte_size": None,
        "sha256_hash": None,
        "storage_uri": None,
        "http_status": None,
        "fetch_error": None,
        "fetched_at": now_iso(),
    }

    try:
        response = _fetch(url)
    except Exception as exc:
        logger.warning("_build_row: %s failed after retries: %s", url, exc)
        base_row["fetch_error"] = str(exc)
        return base_row

    base_row["http_status"] = response.status_code
    if response.status_code >= 400:
        base_row["fetch_error"] = f"HTTP {response.status_code}"
        return base_row

    content = response.content
    content_type = response.headers.get("content-type", "text/html")
    sha256_hash = hashlib.sha256(content).hexdigest()
    ext = _ext_for_content_type(content_type)

    base_row["content_type"] = content_type
    base_row["byte_size"] = len(content)
    base_row["sha256_hash"] = sha256_hash
    base_row["storage_uri"] = _write_bytes(jurisdiction, subject or "_uncategorised", sha256_hash[:16], ext, content)
    return base_row


@dlt.resource(
    name="downloaded_documents",
    table_name="downloaded_documents",
    write_disposition="merge",
    primary_key="sha256_hash",
    columns=DOWNLOADED_DOC_COLUMN_HINTS,
)
def downloaded_documents() -> Iterator[dict[str, Any]]:
    """Fetch every `remote_url` catalog row from `official_documents_source()`
    (Ireland's `ireland_ncca` resource is filesystem-based and already has
    real bytes on disk, so it's skipped here) and yield the fetched-corpus
    row for each.
    """
    from dlt_pipelines._shared import JURISDICTION_BOARDS  # noqa: PLC0415
    from dlt_pipelines.official_doc_fetcher import KNOWN_OFFICIAL_URLS  # noqa: PLC0415

    total = 0
    for source_key, url_rows in KNOWN_OFFICIAL_URLS.items():
        jurisdiction = JURISDICTION_BOARDS.get(source_key, source_key)
        for url_row in url_rows:
            yield _build_row(source_key, url_row, jurisdiction)
            total += 1
    logger.info("downloaded_documents: fetched %d catalog rows", total)


@dlt.source(name="corpus_downloader")
def corpus_downloader_source() -> list[Any]:
    return [downloaded_documents]


def build_pipeline(database_path: Path | None = None, *, dataset_name: str = DATASET_NAME) -> Any:
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
    """Run the full corpus_downloader pipeline; return the `LoadInfo`."""
    pipeline = build_pipeline(database_path)
    load_info = pipeline.run(corpus_downloader_source())
    logger.info("run: completed with LoadInfo=%s", load_info)
    return load_info


def main() -> None:
    """Entry point for `python -m dlt_pipelines.corpus_downloader` (the
    Cloud Run Job command — see `cloud/terraform/cloud_run_jobs.tf`, Phase 7).
    """
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    run()


if __name__ == "__main__":
    main()


__all__ = [
    "DATASET_NAME",
    "DOWNLOADED_DOC_COLUMN_HINTS",
    "FETCH_TIMEOUT_SECONDS",
    "PIPELINE_NAME",
    "USER_AGENT",
    "build_pipeline",
    "corpus_downloader_source",
    "downloaded_documents",
    "main",
    "run",
]
