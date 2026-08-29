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

#: The GCS URI holding the canonical LC subject PDF corpus (Phase 1 — the
#: GCP-first data substrate). This is the deployed-path default; Cloud Run
#: Jobs and the ingestion pipeline read from here.
#: Override with `LC_SUBJECTS_GCS_URI`.
LC_SUBJECTS_GCS_URI: str = os.environ.get(
    "LC_SUBJECTS_GCS_URI",
    f"gs://{os.environ.get('GCP_PROJECT_ID', 'gemini-hackathon-prod')}-biep-raw/ireland/leaving_cert",
)

#: The local-filesystem fallback for offline dev (no GCP creds required).
#: Resolution order (see `resolve_lc_subjects_path()`):
#:   1. `LC_SUBJECTS_PATH` env var, if set (explicit override)
#:   2. `<repo_root>/data/ireland/leaving_certificate/` (committed sample)
#:   3. GCS via `LC_SUBJECTS_GCS_URI` (requires `gcsfs` + ADC)
#: There is deliberately no hardcoded absolute path to another developer's
#: home directory here anymore — that broke on every machine but the one
#: it was written on.
LC_SUBJECTS_PATH: Path = Path(
    os.environ.get("LC_SUBJECTS_PATH", "./data/ireland/leaving_certificate")
)


def resolve_lc_subjects_path() -> Path | str:
    """Resolve the LC subject PDF corpus location.

    Returns a local `Path` if a local copy exists (dev / CI / smoke-test
    fallback), else the `gs://` URI (the deployed-path default). Callers
    that need local bytes (e.g. `pypdfium2`) should check
    `isinstance(result, Path)` and fetch-to-tmp via `gcsfs` otherwise.
    """
    if LC_SUBJECTS_PATH.exists() and any(LC_SUBJECTS_PATH.iterdir()) if LC_SUBJECTS_PATH.exists() else False:
        return LC_SUBJECTS_PATH
    return LC_SUBJECTS_GCS_URI


# ---------------------------------------------------------------------------
# Canonical jurisdiction + subject registries
# ---------------------------------------------------------------------------

#: The 8 British Isles jurisdictions + 5 safeguarding bodies (13 sources).
#: Mirrors `gemini_hackathon.theming.JURISDICTION_SOURCES` + `SAFEGUARDING_SOURCES`.
#:
#: `gov.je/education` + `gov.gg/education` added (Phase 3 of the GCP-first
#: refactor) — completes the 8-jurisdiction British Isles set (Ireland,
#: England x3 boards, Scotland, Wales, Northern Ireland, Isle of Man,
#: Jersey, Guernsey).
JURISDICTION_BOARDS: dict[str, str] = {
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


# ---------------------------------------------------------------------------
# Named destinations factory (lifted from cianfhoghlaim/dlt_sources/common/named_destinations.py)
# ---------------------------------------------------------------------------

#: The canonical destinations for the gemini-hackathon.
#:
#: `duckdb_local` is the offline dev default (no GCP creds required — the
#: smoke tests and `scripts/backend_smoke.py` depend on this staying
#: reachable with zero configuration). `bigquery_biep` is the deployed-path
#: default (Phase 1 of the GCP-first refactor); `dlt`'s `bigquery`
#: destination handles credentials via ADC or `GOOGLE_APPLICATION_CREDENTIALS`.
#: `ducklake_gemini_hackathon` / `motherduck_gemini_hackathon` are kept for
#: local cianfhoghlaim-parity dev only — neither is used by the deployed
#: Cloud Run path.
NAMED_DESTINATIONS: dict[str, str] = {
    # Local DuckDB (the dev default — used by every DLT resource in this repo)
    "duckdb_local": "duckdb:///./data/gemini_hackathon.duckdb",
    # BigQuery (the deployed-path default — Phase 1 GCP-first data substrate)
    "bigquery_biep": f"bigquery://{os.environ.get('GCP_PROJECT_ID', '')}/biep",
    # DuckLake (local cianfhoghlaim-parity dev only; requires DuckLake setup)
    "ducklake_gemini_hackathon": "ducklake:///./data/gemini_hackathon.ducklake",
    # MotherDuck (local cianfhoghlaim-parity dev only; requires MOTHERDUCK_TOKEN)
    "motherduck_gemini_hackathon": "md:gemini_hackathon",
}

#: The 3 GCS bucket names (Phase 1 — provisioned by `cloud/terraform/cloud_run.tf`).
#: `raw` holds fetched PDFs/HTML, `derived` holds OCR/extraction output,
#: `assets` holds generated certificates + comparison images.
GCS_BUCKETS: dict[str, str] = {
    "raw": f"{os.environ.get('GCP_PROJECT_ID', 'gemini-hackathon-prod')}-biep-raw",
    "derived": f"{os.environ.get('GCP_PROJECT_ID', 'gemini-hackathon-prod')}-biep-derived",
    "assets": f"{os.environ.get('GCP_PROJECT_ID', 'gemini-hackathon-prod')}-biep-assets",
}


def gcs_uri(bucket: str, *parts: str) -> str:
    """Build a `gs://` URI for one of the 3 canonical buckets.

    Args:
        bucket: one of `GCS_BUCKETS` keys (`"raw"` / `"derived"` / `"assets"`).
        parts: path components, joined with `/`.

    Raises:
        KeyError: when `bucket` is not a known bucket key.
    """
    return f"gs://{GCS_BUCKETS[bucket]}/" + "/".join(p.strip("/") for p in parts)


def get_named_destination(name: str) -> str:
    """Resolve a named destination to its DLT credentials string.

    The canonical destinations for the gemini-hackathon:

      duckdb_local              → duckdb:///./data/gemini_hackathon.duckdb (default)
      ducklake_gemini_hackathon  → ducklake:///./data/gemini_hackathon.ducklake
      motherduck_gemini_hackathon → md:gemini_hackathon (requires MOTHERDUCK_TOKEN)

    Override any named destination via the env var
    `GEMINI_HACKATHON_DESTINATION_<NAME_UPPER>` (e.g.
    `GEMINI_HACKATHON_DESTINATION_DUCKLAKE_GEMINI_HACKATHON`).

    Raises:
        KeyError: when `name` is not a known destination.
    """
    if name not in NAMED_DESTINATIONS:
        raise KeyError(
            f"Unknown destination {name!r}. Known: {sorted(NAMED_DESTINATIONS.keys())}"
        )
    env_key = f"GEMINI_HACKATHON_DESTINATION_{name.upper()}"
    return os.environ.get(env_key, NAMED_DESTINATIONS[name])


def list_named_destinations() -> list[str]:
    """List all known destination names."""
    return list(NAMED_DESTINATIONS.keys())


__all__ = [
    "DEFAULT_RETRY_ATTEMPTS",
    "DEFAULT_RETRY_BACKOFF_SECONDS",
    "DUCKDB_PATH",
    # GCS (Phase 1 — GCP-first data substrate)
    "GCS_BUCKETS",
    "gcs_uri",
    # Registries
    "JURISDICTION_BOARDS",
    "LC_LANGUAGE_DIRS",
    "LC_SUBJECTS_GCS_URI",
    "LC_SUBJECTS_PATH",
    "LC_SUBJECT_DIRS",
    "resolve_lc_subjects_path",
    # Named destinations factory
    "NAMED_DESTINATIONS",
    "get_named_destination",
    "list_named_destinations",
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
