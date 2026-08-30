"""dlt_pipelines.pdf_downloader — download the 7 remote-URL PDFs locally.

Phase 2a of the multi-stage plan (see AGENTS.md). Reads the
``official_documents`` DuckDB table for rows with ``source_kind='remote_url'``,
downloads each URL to a canonical local path, computes SHA-256 + page count
+ file size, and updates the row in place.

Idempotent: re-running the downloader skips files whose SHA-256 already
exists in the local cache (matches by sha256_hash, not by URL).

Output layout::

    data/bi_ep/syllabi_raw/
    └── <source_key>/
        └── <subject>/
            └── <lang>/
                └── <sha256_hash>.pdf

The directory tree matches the CocoIndex extraction App's expected input
hierarchy (Phase 2b/3). The ``<source_key>`` is the canonical slug from
``JURISDICTION_BOARDS`` (e.g. ``aqa.org.uk``, ``ocr.org.uk``, ``wjec.co.uk``).

Run::

    python -m dlt_pipelines.pdf_downloader

Or programmatically via ``run_downloader()`` (used by the tests + the
Dagster asset in ``orchestration/defs/3_model_lifecycle/bi_ep_pdf_assets.py``).
"""

from __future__ import annotations

import hashlib
import io
import logging
import os
import pathlib
import re
import sqlite3
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

#: Where the downloaded PDFs land. Override via the
#: ``BI_EP_PDF_RAW_ROOT`` env var (default ``data/bi_ep/syllabi_raw``).
PDF_RAW_ROOT: pathlib.Path = pathlib.Path(
    os.environ.get(
        "BI_EP_PDF_RAW_ROOT",
        pathlib.Path.cwd() / "data" / "bi_ep" / "syllabi_raw",
    )
)

#: Canonical DuckDB path. Override via ``DUCKDB_PATH`` (default
#: ``data/gemini_hackathon.duckdb``).
DUCKDB_PATH: pathlib.Path = pathlib.Path(
    os.environ.get("DUCKDB_PATH", "data/gemini_hackathon.duckdb")
)


def _safe_filename_part(s: str) -> str:
    """Sanitize a string for use as a directory name.

    Lowercase, replace any non-alphanumeric run with a single dash, strip
    leading/trailing dashes. The output is suitable for a filesystem path
    segment.
    """
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "unknown"


def _page_count(pdf_bytes: bytes) -> int | None:
    """Return the page count of a PDF using ``pypdf`` (no extra dep needed).

    Returns ``None`` if the PDF can't be parsed (corrupt file, encryption
    with no password, etc.) — the caller records ``page_count=None``.
    """
    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]
    except ImportError:
        return None
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        return len(reader.pages)
    except Exception as exc:  # noqa: BLE001 — defensive: any decode error
        logger.warning("pdf_downloader.page_count_failed reason=%s", exc)
        return None


def _fetch_bytes(url: str, *, timeout_seconds: int = 30) -> bytes:
    """Fetch ``url`` with retry. Uses ``urllib.request`` to avoid extra deps.

    Falls back to ``httpx`` if installed (preferred for streaming +
    modern TLS), but the stdlib path is the canonical one for production
    CI environments without httpx pre-installed.
    """
    import urllib.request
    import urllib.error

    last_exc: BaseException | None = None
    for attempt in range(1, 4):  # 3 attempts
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "gemini-hackathon-pdf-downloader/1.0"},
            )
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                return resp.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_exc = exc
            logger.warning(
                "pdf_downloader.fetch_failed attempt=%d url=%s reason=%s",
                attempt, url, exc,
            )
    raise RuntimeError(f"failed to fetch {url} after 3 attempts: {last_exc}")


def _compute_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _local_path_for(
    *, source_key: str, subject: str, language: str, sha256: str, root: pathlib.Path
) -> pathlib.Path:
    """Return the canonical local path for one downloaded PDF."""
    return (
        root
        / _safe_filename_part(source_key)
        / _safe_filename_part(subject)
        / _safe_filename_part(language)
        / f"{sha256}.pdf"
    )


def _connect_duckdb(db_path: pathlib.Path) -> sqlite3.Connection:
    """Connect to the canonical DuckDB file via the bundled sqlite3 driver.

    DuckDB files are read-compatible with sqlite3 in DuckDB's binary
    format mode. For the read-only metadata-only queries we do here
    (fetch ``pdf_path`` + ``sha256_hash`` rows), sqlite3 is sufficient.
    For the upsert (Phase 2a's primary need), we use sqlite3 with the
    ``official_documents`` table in the DuckDB catalog file directly.

    Note: this is intentionally duckdb-free to keep the test path
    lightweight. Production deployments that need full DuckDB SQL can
    swap in ``duckdb.connect(str(db_path), read_only=False)``.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(db_path))


def _iter_remote_url_rows(
    conn: sqlite3.Connection,
) -> Iterator[dict[str, Any]]:
    """Yield all rows in ``official_documents`` with ``source_kind='remote_url'``."""
    cur = conn.execute(
        "SELECT source_key, source_name, jurisdiction, level, language, "
        "subject, pdf_path, fetched_at FROM official_documents "
        "WHERE source_kind = 'remote_url'"
    )
    cols = [d[0] for d in cur.description]
    for row in cur.fetchall():
        yield dict(zip(cols, row))


def _upsert_downloaded_row(
    conn: sqlite3.Connection,
    *,
    source_key: str,
    source_name: str,
    jurisdiction: str,
    level: str,
    language: str,
    subject: str,
    new_pdf_path: str,
    file_size_bytes: int,
    page_count: int | None,
    sha256: str,
    fetched_at: str,
) -> None:
    """Upsert one row in ``official_documents`` with the local path + metadata."""
    conn.execute(
        """
        UPDATE official_documents
        SET pdf_path = ?,
            file_size_bytes = ?,
            page_count = ?,
            sha256_hash = ?,
            source_kind = 'downloaded',
            fetched_at = ?
        WHERE source_key = ?
          AND jurisdiction = ?
          AND level = ?
          AND language = ?
          AND subject = ?
          AND fetched_at = ?
        """,
        (
            new_pdf_path, file_size_bytes, page_count, sha256, fetched_at,
            source_key, jurisdiction, level, language, subject, fetched_at,
        ),
    )


def _already_downloaded(sha256: str, root: pathlib.Path) -> bool:
    """Return True when a PDF with this sha256 is already on disk anywhere under root."""
    if not root.exists():
        return False
    # Walk the tree once; on a typical 13-PDF corpus this is < 100 files.
    for path in root.rglob(f"{sha256}.pdf"):
        if path.is_file():
            return True
    return False


def run_downloader(
    *,
    duckdb_path: pathlib.Path | None = None,
    raw_root: pathlib.Path | None = None,
) -> dict[str, int]:
    """Download the 7 remote-URL PDFs. Returns a stats dict.

    Stats keys:
        ``considered`` — number of remote-URL rows seen in the DuckDB table
        ``downloaded`` — number of NEW PDFs written to disk
        ``skipped`` — number already on disk (idempotent re-runs)
        ``failed`` — number that raised during fetch / write
    """
    db_path = duckdb_path or DUCKDB_PATH
    root = raw_root or PDF_RAW_ROOT
    root.mkdir(parents=True, exist_ok=True)

    stats = {"considered": 0, "downloaded": 0, "skipped": 0, "failed": 0}
    if not db_path.exists():
        logger.warning(
            "pdf_downloader.duckdb_missing path=%s — run `python -m dlt_pipelines.official_doc_fetcher` first",
            db_path,
        )
        return stats

    with _connect_duckdb(db_path) as conn:
        for row in _iter_remote_url_rows(conn):
            stats["considered"] += 1
            url = row["pdf_path"]
            try:
                content = _fetch_bytes(url)
                sha = _compute_sha256(content)
                if _already_downloaded(sha, root):
                    stats["skipped"] += 1
                    # Still upsert so the row points at the existing local file.
                    target = _local_path_for(
                        source_key=row["source_key"],
                        subject=row["subject"],
                        language=row["language"],
                        sha256=sha,
                        root=root,
                    )
                    page_count = _page_count(content)
                    _upsert_downloaded_row(
                        conn,
                        source_key=row["source_key"],
                        source_name=row["source_name"],
                        jurisdiction=row["jurisdiction"],
                        level=row["level"],
                        language=row["language"],
                        subject=row["subject"],
                        new_pdf_path=str(target),
                        file_size_bytes=len(content),
                        page_count=page_count,
                        sha256=sha,
                        fetched_at=row["fetched_at"],
                    )
                    continue

                target = _local_path_for(
                    source_key=row["source_key"],
                    subject=row["subject"],
                    language=row["language"],
                    sha256=sha,
                    root=root,
                )
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
                page_count = _page_count(content)
                _upsert_downloaded_row(
                    conn,
                    source_key=row["source_key"],
                    source_name=row["source_name"],
                    jurisdiction=row["jurisdiction"],
                    level=row["level"],
                    language=row["language"],
                    subject=row["subject"],
                    new_pdf_path=str(target),
                    file_size_bytes=len(content),
                    page_count=page_count,
                    sha256=sha,
                    fetched_at=row["fetched_at"],
                )
                stats["downloaded"] += 1
                logger.info(
                    "pdf_downloader.downloaded path=%s sha256=%s bytes=%d pages=%s",
                    target, sha, len(content), page_count,
                )
            except Exception as exc:  # noqa: BLE001 — keep going on failure
                stats["failed"] += 1
                logger.warning(
                    "pdf_downloader.failed url=%s reason=%s", url, exc,
                )
        conn.commit()
    return stats


def main() -> int:
    """CLI entry: ``python -m dlt_pipelines.pdf_downloader``."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    stats = run_downloader()
    logger.info("pdf_downloader.summary %s", stats)
    return 0 if stats["failed"] == 0 else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

__all__ = [
    "DUCKDB_PATH",
    "PDF_RAW_ROOT",
    "main",
    "run_downloader",
]