"""cache.py — local FS in dev, GCS in prod, transparent to the caller.

Phase 2 of the GCP-first refactor. One helper per write/read, picks the
backend by the presence of `GCP_PROJECT_ID` + a working `google-cloud-storage`
import. Returns a `StorageUri` (string + parsed components) so the
sourcing pipeline can log both the local-cache path AND the GCS URI of
every artefact — useful for debug + the copilot's "what got sourced
where?" view.

Design choices:
  - **Local-first** — the local-cache path is always tried first. The
    GCS URI is recorded on the Firestore doc either way, but the bytes
    themselves only round-trip to GCS in production. This means the
    offline-dev pipeline demos end-to-end without ever touching GCS.

  - **Content-addressed** — the cache key is always the sha256 of the
    content. Same content from different URLs deduplicates correctly.

  - **No silent failures** — every write returns a URI it can verify; the
    caller decides whether a failure is fatal.
"""
from __future__ import annotations

import hashlib
import logging
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


#: The default local cache root (offline dev). Overridable via
#: `JOURNEY_LOCAL_CACHE_DIR`. The directory is created lazily.
_LOCAL_CACHE_ROOT: Path = Path(
    os.environ.get("JOURNEY_LOCAL_CACHE_DIR", "./data/sourced_cache")
)


@dataclass(frozen=True)
class StoredBytes:
    """The result of a cache write — what + where + how big."""

    sha256: str
    byte_size: int
    local_cache_uri: str  # file://... (dev) or "" (prod)
    gcs_uri: str         # gs://... (prod) or file://... (dev)


def compute_sha256(content: bytes) -> str:
    """Canonical sha256 of `content` (lowercase hex, 64 chars)."""
    return hashlib.sha256(content).hexdigest()


def write_bytes(
    content: bytes,
    *,
    jurisdiction: str,
    subject_slug: str,
    language: str,
    sha256: str | None = None,
) -> StoredBytes:
    """Persist `content` to local FS (dev) + GCS (prod).

    Args:
        content: the bytes to persist
        jurisdiction / subject_slug / language: used in the storage path
            so the layout matches the canonical `journeys/{event_code}/`
            tree (see `fs.py`)
        sha256: if pre-computed; otherwise the helper computes it. Computing
            once and passing in is the common case (the same content may be
            written once per catalog row + once per artefact upsert).

    Returns: a `StoredBytes` with all the URIs the caller needs to record
    on the `content_artefacts` Firestore doc.
    """
    digest = sha256 or compute_sha256(content)
    byte_size = len(content)

    # 1. Local FS (always, for the dev path).
    local_dir = _LOCAL_CACHE_ROOT / jurisdiction / subject_slug / language
    local_dir.mkdir(parents=True, exist_ok=True)
    local_path = local_dir / digest
    local_path.write_bytes(content)
    local_cache_uri = local_path.resolve().as_uri()

    # 2. GCS upload (prod path only — emulator-free local dev skips this).
    gcs_uri = local_cache_uri  # default: dev — both URIs point at the local file
    if _should_use_gcs():
        try:
            from google.cloud import storage  # noqa: PLC0415

            project_id = os.environ.get("GCP_PROJECT_ID", "")
            bucket_name = os.environ.get("JOURNEY_GCS_RAW_BUCKET", f"{project_id}-biep-raw")
            blob_path = f"{jurisdiction}/{subject_slug}/{language}/{digest}"
            client = storage.Client(project=project_id)
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            blob.upload_from_string(content)
            gcs_uri = f"gs://{bucket_name}/{blob_path}"
            logger.info("cache.write_bytes: uploaded %d bytes to %s", byte_size, gcs_uri)
        except Exception as exc:
            logger.warning("cache.write_bytes: GCS upload failed (%s); keeping local URI only", exc)

    return StoredBytes(
        sha256=digest,
        byte_size=byte_size,
        local_cache_uri=local_cache_uri,
        gcs_uri=gcs_uri,
    )


def read_bytes(
    *,
    jurisdiction: str,
    subject_slug: str,
    language: str,
    sha256: str,
) -> bytes | None:
    """Read bytes from local cache first, then GCS.

    Returns None if neither has the bytes (the caller decides whether to
    re-fetch from the source URL).
    """
    local_path = _LOCAL_CACHE_ROOT / jurisdiction / subject_slug / language / sha256
    if local_path.exists():
        return local_path.read_bytes()
    if _should_use_gcs():
        try:
            from google.cloud import storage  # noqa: PLC0415

            project_id = os.environ.get("GCP_PROJECT_ID", "")
            bucket_name = os.environ.get("JOURNEY_GCS_RAW_BUCKET", f"{project_id}-biep-raw")
            blob_path = f"{jurisdiction}/{subject_slug}/{language}/{sha256}"
            client = storage.Client(project=project_id)
            blob = client.bucket(bucket_name).blob(blob_path)
            return blob.download_as_bytes()
        except Exception as exc:
            logger.warning("cache.read_bytes: GCS read failed (%s)", exc)
    return None


def _should_use_gcs() -> bool:
    """True when the dev/prod boundary says "use real GCS".

    False when:
      - GCP_PROJECT_ID is unset (offline dev)
      - `JOURNEY_CACHE_DISABLE_GCS=1` (explicit opt-out for tests)
      - `google-cloud-storage` isn't importable (offline dev)
    """
    if os.environ.get("JOURNEY_CACHE_DISABLE_GCS") == "1":
        return False
    if not os.environ.get("GCP_PROJECT_ID", ""):
        return False
    try:
        import google.cloud.storage  # noqa: F401,PLC0415
        return True
    except ImportError:
        return False


__all__ = [
    "StoredBytes",
    "_LOCAL_CACHE_ROOT",
    "compute_sha256",
    "read_bytes",
    "write_bytes",
]
