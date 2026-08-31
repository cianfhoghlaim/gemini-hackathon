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
- `get_duckdb_destination()` — the legacy dlt duckdb destination factory
  (Phase 2 kept as a thin wrapper around `get_destination("duckdb")`
  for backwards compat with every Phase 0/1 caller)
- `get_destination()` — the Phase 2 polymorphic 4-backend factory
  (`duckdb` / `ducklake` / `motherduck` / `bigquery`). The new
  production-target entry point — BigQuery is selected by passing
  `name="bigquery"` (or by setting `BIGQUERY_DATASET`).
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
from typing import TYPE_CHECKING, Any, Literal, TypeVar

if TYPE_CHECKING:
    from dlt.destinations.impl.duckdb.factory import duckdb

# Literal type alias for the 4 supported DLT destinations (Phase 2).
DestinationName = Literal["duckdb", "ducklake", "motherduck", "bigquery"]

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

#: The 9 British Isles jurisdictions + 5 safeguarding bodies (14 sources).
#: Mirrors `gemini_hackathon.theming.JURISDICTION_SOURCES` + `SAFEGUARDING_SOURCES`.
#:
#: `gov.je/education` + `gov.gg/education` added (Phase 3 of the GCP-first
#: refactor) — completes the 8-jurisdiction British Isles set (Ireland,
#: England x3 boards, Scotland, Wales, Northern Ireland, Isle of Man,
#: Jersey, Guernsey).
#:
#: `uk_ncce` added in the 2026-08-31 Learning Graph era
#: (`2026-08-31-uk-ncce-learning-graph-showcase-v1`) as the 9th jurisdiction.
#: The rich metadata (covers, priority_subjects, s3_bucket, curriculum_source)
#: lives in the companion `JURISDICTION_DETAILS` dict below.
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
    "uk_ncce": "United Kingdom (NCCE)",
}

#: Per-jurisdiction rich metadata. Holds the extended fields (name,
#: country, awarding_body, covers, curriculum_source, s3_bucket,
#: priority_subjects) for jurisdictions that publish structured curricula
#: (currently just `uk_ncce` per the 2026-08-31 Learning Graph era
#: showcase). Other jurisdictions get an empty dict so `detail_for(key)`
#: never raises.
JURISDICTION_DETAILS: dict[str, dict[str, object]] = {
    "uk_ncce": {
        "name": "United Kingdom (NCCE)",
        "country": "UK",
        "awarding_body": "NCCE",
        "covers": ["England", "Wales", "Northern Ireland", "Isle of Man"],
        "curriculum_source": "https://teachcomputing.org/curriculum",
        "s3_bucket": "ncce-curriculum-production.s3.eu-west-1.amazonaws.com",
        "priority_subjects": [
            "computer_science",
            "mathematics",
            "english",
            "gaeilge",  # cross-walked via the NCCA Gaeilge LC curriculum
            "chemistry",
            "geography",
        ],
    },
}


def jurisdiction_detail(source_key: str) -> dict[str, object]:
    """Return the rich metadata dict for `source_key`, or ``{}`` if absent.

    Companion to :data:`JURISDICTION_BOARDS`. The simple
    ``JURISDICTION_BOARDS[key]`` lookup returns the country name;
    ``jurisdiction_detail(key)`` returns the full structured metadata
    (priority_subjects, s3_bucket, etc.) when present.
    """
    return JURISDICTION_DETAILS.get(source_key, {})

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
# DLT destination factory (Phase 2 — polymorphic 4-backend factory)
# ---------------------------------------------------------------------------

#: The default BigQuery dataset name. Overridden via the `BIGQUERY_DATASET`
#: env var or the `bigquery_dataset=` kwarg to `get_destination()`.
BIGQUERY_DEFAULT_DATASET: str = os.environ.get("BIGQUERY_DATASET", "biep")


def get_destination(
    name: DestinationName = "duckdb",
    database_path: Path | None = None,
    *,
    bigquery_dataset: str | None = None,
) -> Any:
    """Return the canonical dlt destination for `name`.

    Phase 2 of the GCP-first refactor. Polymorphic factory selecting
    one of 4 backends:

    - ``duckdb`` (default): local DuckDB at `DUCKDB_PATH` (or
      `database_path` when provided). Offline-safe.
    - ``ducklake``: DuckLake-backed DuckDB. Phase 2 keeps the local
      DuckDB fallback (the real `ducklake:///...` URL lives behind
      a Phase 3 follow-up — see KNOWN_ISSUES.md).
    - ``motherduck``: MotherDuck cloud via
      `duckdb.connect("md:...")`. Phase 2 keeps the local DuckDB
      fallback (the real `md:...` connection string requires a
      Phase 3 follow-up with `MOTHERDUCK_TOKEN`).
    - ``bigquery``: Google Cloud BigQuery via
      `dlt.destinations.bigquery(dataset_name=...)`. Requires the
      `dlt[bigquery]` extra; the import is wrapped in
      `try/except ImportError` so this module stays importable
      without it (raises `ImportError` at call time when the extra
      isn't installed — fail-fast, not silent).

    Args:
        name: One of ``"duckdb"``, ``"ducklake"``, ``"motherduck"``,
            ``"bigquery"``. Anything else raises `ValueError`.
        database_path: Optional override for the DuckDB file path
            (only used by the `duckdb`/`ducklake`/`motherduck`
            branches; ignored by `bigquery`).
        bigquery_dataset: The BigQuery dataset name. Falls back to
            the `BIGQUERY_DATASET` env var (default ``"biep"``).
            Ignored by every non-BigQuery branch.

    Returns:
        The dlt destination instance (a `dlt.destinations` factory
        product). Callers pass it to `dlt.pipeline(destination=...)`.

    Raises:
        ValueError: when `name` is not one of the 4 supported
            backends.
        ImportError: when `name="bigquery"` and `dlt[bigquery]` is
            not installed.
    """
    if name not in ("duckdb", "ducklake", "motherduck", "bigquery"):
        raise ValueError(
            f"get_destination: unknown name {name!r}; "
            "valid: 'duckdb' | 'ducklake' | 'motherduck' | 'bigquery'"
        )

    if name == "bigquery":
        # Lazy import — the `dlt[bigquery]` extra is part of the
        # optional `[dependency-groups] gcp` group (see pyproject.toml).
        # Phase 2 keeps the default `uv sync` install GCP-free, so this
        # import is the one that needs the guard.
        try:
            import dlt  # noqa: PLC0415 — lazy import
            from dlt.destinations import bigquery as _bigquery  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover — defensive
            raise ImportError(
                "get_destination('bigquery') requires the `dlt[bigquery]` "
                "extra (the GCP data-plane group). Install with "
                "`uv sync --group gcp` and retry."
            ) from exc

        dataset = bigquery_dataset or os.environ.get("BIGQUERY_DATASET", BIGQUERY_DEFAULT_DATASET)
        logger.info(
            "get_destination: using BigQuery dataset=%s (credentials via ADC)",
            dataset,
        )
        return _bigquery(dataset_name=dataset)

    # Local DuckDB branch (duckdb + ducklake + motherduck all share
    # the local DuckDB file in Phase 2; Phase 3 splits them out).
    from dlt.destinations import duckdb as _duckdb  # noqa: PLC0415

    if database_path is None:
        env_override = os.environ.get("DUCKDB_PATH")
        database_path = Path(env_override) if env_override else DUCKDB_PATH

    database_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(
        "get_destination: using DuckDB at %s (backend=%s, dataset_name supplied by caller)",
        database_path,
        name,
    )
    # `ducklake` + `motherduck` share the local DuckDB file in Phase 2;
    # Phase 3 splits them into their real URLs (`ducklake:///...` and
    # `md:...`) without changing the call site.
    return _duckdb(credentials=str(database_path))


def get_duckdb_destination(database_path: Path | None = None) -> duckdb:
    """Backwards-compat wrapper around `get_destination("duckdb", ...)`.

    Phase 2 keeps this function as a thin alias so every Phase 0/1
    caller (`corpus_downloader.py`, `pdf_downloader.py`, etc.) continues
    to work without modification. New code SHOULD use
    `get_destination()` directly so the backend selection is explicit
    at the call site.

    Defaults to `DUCKDB_PATH` (the repo-root `gemini_hackathon.duckdb`).
    Override via the env var `DUCKDB_PATH` for the CI runner, or pass
    `database_path=` explicitly.
    """
    result = get_destination("duckdb", database_path=database_path)
    # The TYPE_CHECKING import is `duckdb` (the class); the runtime
    # return value is a destination instance — duckdb in the type stub
    # is the closest match. Cast via `Any` in callers if needed.
    return result  # type: ignore[return-value]


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


def write_pdf_to_gcs_or_local(
    content: bytes,
    *,
    source_key: str,
    subject: str,
    language: str,
    sha256: str,
    extension: str = ".pdf",
    local_root: Path | None = None,
) -> str:
    """Write PDF bytes to GCS (when `GCS_RAW_BUCKET` is set) or local disk.

    Phase 2 of the GCP-first refactor. The Phase 1 `corpus_downloader`
    already writes to GCS via `storage.Client` (gated on
    `GCP_PROJECT_ID`); this helper introduces a **simpler**
    `GCS_RAW_BUCKET`-only mechanism that doesn't require the project-id
    derivation. Both call sites can use it; the Phase 1 wiring stays
    for backwards compat with any Cloud Run Job that sets
    `GCP_PROJECT_ID` but not `GCS_RAW_BUCKET`.

    Path layout (matches the spec snippet at
    `openspec/changes/2026-08-31-gcp-data-plane-v1/proposal.md`):

        GCS set:     gs://<bucket>/<source_key>/<subject>/<language>/<sha256><ext>
        GCS unset:   <local_root>/<source_key>/<subject>/<language>/<sha256><ext>
                     (default local_root = REPO_ROOT/data/bi_ep/syllabi_raw/)

    Args:
        content: The PDF (or HTML) bytes to write.
        source_key: The jurisdiction slug (`aqa.org.uk`, `ncca.ie`, ...).
        subject: The subject slug (`mathematics`, `english`, ...).
        language: The 2-letter language code (`en` / `ga`).
        sha256: The content sha256 (used as the filename).
        extension: File extension (`.pdf`, `.html`, `.txt`, `.bin`).
        local_root: Override for the local-filesystem root. Defaults
            to `<repo_root>/data/bi_ep/syllabi_raw/`.

    Returns:
        The storage URI:
        - `gs://<bucket>/<rel>` when `GCS_RAW_BUCKET` is set + upload succeeds
        - A local `Path` string when the env var is unset (or the GCS
          upload fails for any reason — best-effort fallback)
    """
    bucket = os.environ.get("GCS_RAW_BUCKET")
    rel = f"{source_key}/{subject}/{language}/{sha256}{extension}"

    if bucket:
        try:
            from google.cloud import storage  # noqa: PLC0415 — lazy import
            from google.cloud.exceptions import GoogleCloudError  # noqa: PLC0415 — lazy

            client = storage.Client()
            client_bucket = client.bucket(bucket)
            blob = client_bucket.blob(rel)
            blob.upload_from_string(content)
            logger.info(
                "write_pdf_to_gcs_or_local: uploaded %d bytes to gs://%s/%s",
                len(content),
                bucket,
                rel,
            )
            return f"gs://{bucket}/{rel}"
        except ImportError:
            logger.warning(
                "write_pdf_to_gcs_or_local: google-cloud-storage not installed, "
                "falling back to local disk for %s/%s/%s/%s",
                source_key,
                subject,
                language,
                sha256,
            )
        except Exception as exc:  # noqa: BLE001 — best-effort fallback
            logger.warning(
                "write_pdf_to_gcs_or_local: GCS upload failed (%s), falling back to local",
                exc,
            )

    if local_root is None:
        local_root = REPO_ROOT / "data" / "bi_ep" / "syllabi_raw"
    target = local_root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    logger.info(
        "write_pdf_to_gcs_or_local: wrote %d bytes to %s (local fallback)",
        len(content),
        target,
    )
    return str(target)


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
    # GCS PDF substrate (Phase 2 — `GCS_RAW_BUCKET` env-var gated)
    "write_pdf_to_gcs_or_local",
    # Registries
    "JURISDICTION_BOARDS",
    "JURISDICTION_DETAILS",
    "jurisdiction_detail",
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
    # DLT destination factory (Phase 2 — polymorphic 4-backend)
    "BIGQUERY_DEFAULT_DATASET",
    "DestinationName",
    "get_destination",
    # Legacy wrapper (kept for Phase 0/1 caller compatibility)
    "get_duckdb_destination",
    "now_iso",
    "safe_stat",
    # File helpers
    "sha256_file",
    # Retry
    "with_retry",
]
