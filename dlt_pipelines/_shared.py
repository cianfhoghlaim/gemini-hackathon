"""Shared helpers for the `dlt_pipelines` package.

Per the canonical Cianfhoghlaim dlt_sources/ convention, common
helpers live in `dlt_pipelines/_shared.py` (rather than
`dlt_pipelines/common/`) so the package stays a flat sibling of the
`gemini_hackathon/` Python package.

Provides:
- `JURISDICTION_BOARDS` — the 8 BI jurisdiction → awarding-board mapping
- `LC_SUBJECT_DIRS` — the 17 leaving-certificate subject directories
- `LC_SUBJECTS_PATH` — the canonical parent of all LC subject PDFs
- `DUCKDB_PATH` — the canonical DuckDB destination filename
- `sha256_file()` — file-content SHA256 (chunked, large-file safe)
- `now_iso()` — UTC ISO-8601 timestamp
- `with_retry()` — exponential-backoff retry decorator
- `safe_stat()` — pathlib.stat() with FileNotFoundError → None
- `get_duckdb_destination()` — the canonical dlt duckdb destination factory
"""

from __future__ import annotations

import hashlib
import logging
import os
import time
from collections.abc import Callable
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from dlt.destinations.impl.duckdb.factory import duckdb

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

# ---------------------------------------------------------------------------
# Project layout constants
# ---------------------------------------------------------------------------

#: The repo root (the directory above `dlt_pipelines/`).
REPO_ROOT: Path = Path(__file__).resolve().parent.parent

#: The canonical DuckDB destination filename (per the user's spec).
#: Lives at the repo root, parallel to `dlt_pipelines/` and `gemini_hackathon/`.
DUCKDB_PATH: Path = REPO_ROOT / "gemini_hackathon.duckdb"

#: The canonical parent of all 134 leaving-certificate subject PDFs.
#: The user spec'd `/Users/cianmacdeisigh/dev/cianchosaint/leaving_certificate/`
#: but the actual canonical mirror on this workstation is at
#: `/Users/cianmacandeisigh/dev/biiep-hackathon-2026-08-31/leaving_certificate/`.
#: Override with `LC_SUBJECTS_PATH_OVERRIDE` env var.
LC_SUBJECTS_PATH: Path = Path(
    os.environ.get(
        "LC_SUBJECTS_PATH",
        "/Users/cianmacandeisigh/dev/biiep-hackathon-2026-08-31/leaving_certificate",
    )
)


# ---------------------------------------------------------------------------
# Canonical jurisdiction + subject registries
# ---------------------------------------------------------------------------

#: The 8 British Isles jurisdictions + 5 safeguarding bodies (13 sources).
#: Mirrors `gemini_hackathon.theming.JURISDICTION_SOURCES` + `SAFEGUARDING_SOURCES`.
JURISDICTION_BOARDS: dict[str, str] = {
    "ncca.ie": "Ireland",
    "aqa.org.uk": "England",
    "ocr.org.uk": "England",
    "qualifications.pearson.com": "England",
    "sqa.org.uk": "Scotland",
    "wjec.co.uk": "Wales",
    "ccea.org.uk": "Northern Ireland",
    "gov.im/education": "Isle of Man",
}

#: The 5 safeguarding bodies.
SAFEGUARDING_BODIES: dict[str, str] = {
    "gov.ie/education": "Ireland",
    "gov.uk/dfe": "England",
    "education.gov.scot": "Scotland",
    "gov.wales/education": "Wales",
    "ccea.org.uk/safeguarding": "Northern Ireland",
}

#: The 17 LC subject directories that hold the 134 official PDFs.
#: These match the canonical layout at `leaving_certificate/<subject>/`.
LC_SUBJECT_DIRS: tuple[str, ...] = (
    "accounting",
    "applied_mathematics",
    "art",
    "biology",
    "business",
    "chemistry",
    "computer_science",
    "english",
    "french",
    "gaeilge",
    "geography",
    "history",
    "mathematics",
    "music",
    "physics",
    "technology",
    "ukrainian",
)

#: The 2 LC language sub-directories under each subject.
LC_LANGUAGE_DIRS: tuple[str, ...] = ("en", "ga")


# ---------------------------------------------------------------------------
# Canonical resource fields
# ---------------------------------------------------------------------------

#: Column list for the `official_documents` table produced by
#: `official_doc_fetcher.py`. The contract is consumed downstream by
#: `pdf_page_metadata.py` and the BAML `ExtractSourcePalette` runner.
OFFICIAL_DOC_COLUMNS: tuple[str, ...] = (
    "source_key",
    "source_name",
    "jurisdiction",
    "level",
    "language",
    "subject",
    "pdf_path",
    "file_size_bytes",
    "page_count",
    "sha256_hash",
    "source_kind",
    "fetched_at",
)

#: Column list for the `safeguarding_policies` table produced by
#: `safeguarding_fetcher.py`.
SAFEGUARDING_POLICY_COLUMNS: tuple[str, ...] = (
    "source_key",
    "source_name",
    "jurisdiction",
    "policy_topic",
    "publication_year",
    "official_url",
    "local_pdf_path",
    "file_size_bytes",
    "page_count",
    "sha256_hash",
    "fetched_at",
)

#: Column list for the `pdf_metadata` table produced by
#: `pdf_page_metadata.py`.
PDF_METADATA_COLUMNS: tuple[str, ...] = (
    "pdf_path",
    "source_key",
    "sha256_hash",
    "page_count",
    "fonts_detected",
    "image_count",
    "has_text_layer",
    "file_size_bytes",
    "extracted_at",
)


# ---------------------------------------------------------------------------
# File / hashing helpers
# ---------------------------------------------------------------------------

#: SHA256 read chunk size (1 MiB). Big enough to be fast on modern SSDs.
SHA256_CHUNK_BYTES: int = 1024 * 1024


def sha256_file(path: Path, *, chunk_bytes: int = SHA256_CHUNK_BYTES) -> str:
    """Return the lowercase hex SHA256 digest of `path`.

    Reads in `chunk_bytes` chunks so it works for multi-GB files
    without loading the whole file into memory.

    Raises:
        FileNotFoundError: when `path` does not exist.
        OSError: for any other filesystem error (permissions, etc.).
    """
    if not path.exists():
        raise FileNotFoundError(f"sha256_file: path does not exist: {path}")
    if not path.is_file():
        raise OSError(f"sha256_file: not a regular file: {path}")

    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_bytes)
            if chunk == b"":
                break
            h.update(chunk)
    return h.hexdigest()


def safe_stat(path: Path) -> int | None:
    """Return `path.stat().st_size` if `path` is a regular file, else None.

    Per the dignified-python LBYL pattern: check existence + file-ness
    BEFORE calling `stat()`. Avoids the bare-except anti-pattern.
    """
    if path is None:
        return None
    if not path.exists() or not path.is_file():
        return None
    try:
        return path.stat().st_size
    except OSError as exc:
        logger.warning("safe_stat: %s failed: %s", path, exc)
        return None


def now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string (with `Z`)."""
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Retry decorator (FileNotFoundError → safe backoff)
# ---------------------------------------------------------------------------

DEFAULT_RETRY_ATTEMPTS: int = 3
DEFAULT_RETRY_BACKOFF_SECONDS: float = 0.25


def with_retry(
    *,
    attempts: int = DEFAULT_RETRY_ATTEMPTS,
    backoff_seconds: float = DEFAULT_RETRY_BACKOFF_SECONDS,
    retry_on: tuple[type[BaseException], ...] = (FileNotFoundError,),
) -> Callable[[F], F]:
    """Decorator: retry `retry_on` exceptions up to `attempts` times.

    Per the user's spec: "Add basic retry on file-not-found (use
    FileNotFoundError handling)". Exponential backoff doubles the
    delay each retry (capped at 8x the initial).

    Args:
        attempts: total attempt count including the first call.
        backoff_seconds: initial sleep before retry #2 (doubles each time).
        retry_on: tuple of exception classes that should trigger retry.
            Non-listed exceptions propagate immediately.
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = backoff_seconds
            last_exc: BaseException | None = None
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retry_on as exc:
                    last_exc = exc
                    if attempt >= attempts:
                        logger.error(
                            "with_retry: %s failed after %d attempts: %s",
                            func.__name__,
                            attempt,
                            exc,
                        )
                        raise
                    logger.warning(
                        "with_retry: %s attempt %d/%d failed (%s); retrying in %.2fs",
                        func.__name__,
                        attempt,
                        attempts,
                        exc,
                        delay,
                    )
                    time.sleep(delay)
                    delay = min(delay * 2, delay * 8)
            # Unreachable: the for-loop either returns or raises.
            if last_exc is not None:
                raise last_exc
            raise RuntimeError("with_retry: unreachable — no return or raise")

        return wrapper  # type: ignore[return-value]

    return decorator


# ---------------------------------------------------------------------------
# DLT destination factory
# ---------------------------------------------------------------------------


def get_duckdb_destination(database_path: Path | None = None) -> duckdb:
    """Return the canonical dlt `duckdb` destination pointing at `database_path`.

    Defaults to `DUCKDB_PATH` (the repo-root `gemini_hackathon.duckdb`).
    Honourable to override via the env var `DUCKDB_PATH` for the CI runner.
    """
    from dlt.destinations import duckdb  # noqa: PLC0415 — lazy for fast package import

    if database_path is None:
        env_override = os.environ.get("DUCKDB_PATH")
        database_path = Path(env_override) if env_override else DUCKDB_PATH

    # Ensure the parent dir exists (DLT doesn't mkdir for us).
    database_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(
        "get_duckdb_destination: using DuckDB at %s (dataset_name supplied by caller)",
        database_path,
    )
    return duckdb(credentials=str(database_path))


__all__ = [
    "DEFAULT_RETRY_ATTEMPTS",
    "DEFAULT_RETRY_BACKOFF_SECONDS",
    "DUCKDB_PATH",
    # Registries
    "JURISDICTION_BOARDS",
    "LC_LANGUAGE_DIRS",
    "LC_SUBJECTS_PATH",
    "LC_SUBJECT_DIRS",
    # Column contracts
    "OFFICIAL_DOC_COLUMNS",
    "PDF_METADATA_COLUMNS",
    # Layout constants
    "REPO_ROOT",
    "SAFEGUARDING_BODIES",
    "SAFEGUARDING_POLICY_COLUMNS",
    # SHA256 read chunk
    "SHA256_CHUNK_BYTES",
    # DLT destination factory
    "get_duckdb_destination",
    "now_iso",
    "safe_stat",
    # File helpers
    "sha256_file",
    # Retry
    "with_retry",
]
