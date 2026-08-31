"""tests.dlt.test_gcs_substrate — verify the Phase 2 GCS PDF substrate helper.

Tests `dlt_pipelines._shared.write_pdf_to_gcs_or_local` against mocked
`google.cloud.storage.Client` calls.

Per Phase 2 of the polish plan (`openspec/changes/2026-08-31-gcp-data-plane-v1`):
- When `GCS_RAW_BUCKET` is set, the helper returns a `gs://` URI and
  uploads the content via `storage.Client().bucket(bucket).blob(rel).upload_from_string(...)`.
- When `GCS_RAW_BUCKET` is unset, the helper writes to local disk and
  does NOT construct the GCS client.

All tests are fully mocked — no live GCS calls.

Updated 2026-08-31 (Phase 6): tests now also mock `google.cloud.exceptions`
so the lazy `from google.cloud.exceptions import GoogleCloudError` resolves
to a MagicMock. Without it, previous tests that imported `google.cloud.*`
modules leave cached references that bypass the sys.modules patch.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _reload_shared() -> object:
    if "dlt_pipelines._shared" in sys.modules:
        importlib.reload(sys.modules["dlt_pipelines._shared"])
    return importlib.import_module("dlt_pipelines._shared")


def _invalidate_google_cloud_modules() -> None:
    """Drop ``google.cloud`` + ``google.cloud.storage`` so the lazy
    ``from google.cloud import storage`` in the helper goes through the
    normal import path (which respects ``sys.modules``).

    The cocoindex ``test_dual_write_target`` and ``test_vertex_target``
    tests transitively import the real ``google.cloud.storage`` (via
    Firestore + Vector Search's grpc deps), which caches the real module
    on the ``google.cloud`` namespace package. Subsequent ``from google.cloud
    import storage`` then bypasses ``patch.dict(sys.modules, ...)`` —
    PEP 562 namespace package ``__getattr__`` re-imports from disk even
    when ``sys.modules`` carries a mock.

    Clearing the cached entries here before ``patch.dict`` is the only
    reliable way to make the mock survive test ordering.
    """
    for mod_name in list(sys.modules):
        if mod_name == "google.cloud" or mod_name.startswith("google.cloud.storage"):
            del sys.modules[mod_name]


def _fake_google_cloud_modules() -> tuple[MagicMock, MagicMock]:
    """Build a (storage, exceptions) MagicMock pair for the lazy imports."""
    fake_storage = MagicMock(name="google.cloud.storage")
    fake_storage.Client.return_value = MagicMock(name="Client")
    fake_exceptions = MagicMock(name="google.cloud.exceptions")
    fake_exceptions.GoogleCloudError = type("GoogleCloudError", (Exception,), {})
    return fake_storage, fake_exceptions


def test_gcs_helper_returns_gs_uri_when_bucket_set(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When `GCS_RAW_BUCKET=test-bucket`, the helper returns a `gs://test-bucket/...` URI."""
    monkeypatch.setenv("GCS_RAW_BUCKET", "test-bucket")

    mod = _reload_shared()

    fake_storage, fake_exceptions = _fake_google_cloud_modules()
    fake_client = MagicMock(name="Client")
    fake_bucket = MagicMock(name="Bucket")
    fake_blob = MagicMock(name="Blob")
    fake_storage.Client.return_value = fake_client
    fake_client.bucket.return_value = fake_bucket
    fake_bucket.blob.return_value = fake_blob

    _invalidate_google_cloud_modules()
    with patch.dict(
        sys.modules,
        {
            "google.cloud.storage": fake_storage,
            "google.cloud.exceptions": fake_exceptions,
        },
    ):
        result = mod.write_pdf_to_gcs_or_local(
            b"%PDF-1.4 fake bytes",
            source_key="aqa.org.uk",
            subject="mathematics",
            language="en",
            sha256="deadbeefcafe1234",
            local_root=tmp_path,
        )

    assert result.startswith("gs://test-bucket/"), f"expected gs:// URI, got {result!r}"
    assert result == "gs://test-bucket/aqa.org.uk/mathematics/en/deadbeefcafe1234.pdf"
    fake_client.bucket.assert_called_once_with("test-bucket")
    fake_bucket.blob.assert_called_once_with("aqa.org.uk/mathematics/en/deadbeefcafe1234.pdf")
    fake_blob.upload_from_string.assert_called_once_with(b"%PDF-1.4 fake bytes")


def test_gcs_helper_falls_back_to_local_when_bucket_unset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When `GCS_RAW_BUCKET` is unset, the helper writes to local + does NOT call GCS."""
    monkeypatch.delenv("GCS_RAW_BUCKET", raising=False)

    mod = _reload_shared()

    fake_storage, _ = _fake_google_cloud_modules()

    # Even if `google.cloud.storage` is importable, the client must NOT
    # be instantiated when GCS_RAW_BUCKET is unset.
    with patch.dict(sys.modules, {"google.cloud.storage": fake_storage}):
        result = mod.write_pdf_to_gcs_or_local(
            b"%PDF-1.4 fake bytes",
            source_key="ncca.ie",
            subject="gaeilge",
            language="ga",
            sha256="abc123",
            local_root=tmp_path,
        )

    # The returned path is the local target.
    assert result.startswith(str(tmp_path))
    assert result.endswith("ncca.ie/gaeilge/ga/abc123.pdf")
    assert Path(result).exists()
    assert Path(result).read_bytes() == b"%PDF-1.4 fake bytes"

    # The GCS client was NOT constructed.
    fake_storage.Client.assert_not_called()


def test_gcs_helper_layout_matches_spec(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The path layout matches the spec: `<bucket>/<source_key>/<subject>/<lang>/<sha256>.<ext>`."""
    monkeypatch.setenv("GCS_RAW_BUCKET", "biep-raw")

    mod = _reload_shared()

    fake_storage, fake_exceptions = _fake_google_cloud_modules()
    fake_client = MagicMock(name="Client")
    fake_bucket = MagicMock(name="Bucket")
    fake_blob = MagicMock(name="Blob")
    fake_storage.Client.return_value = fake_client
    fake_client.bucket.return_value = fake_bucket
    fake_bucket.blob.return_value = fake_blob

    _invalidate_google_cloud_modules()
    with patch.dict(
        sys.modules,
        {
            "google.cloud.storage": fake_storage,
            "google.cloud.exceptions": fake_exceptions,
        },
    ):
        result = mod.write_pdf_to_gcs_or_local(
            b"x",
            source_key="wjec.co.uk",
            subject="chemistry",
            language="en",
            sha256="sha256hash",
            extension=".html",  # extension override
            local_root=tmp_path,
        )

    assert result == "gs://biep-raw/wjec.co.uk/chemistry/en/sha256hash.html"
    fake_bucket.blob.assert_called_once_with("wjec.co.uk/chemistry/en/sha256hash.html")


def test_gcs_helper_handles_missing_package_gracefully(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """When `google.cloud.storage` is NOT installed, the helper logs + falls back to local."""
    monkeypatch.setenv("GCS_RAW_BUCKET", "test-bucket")

    mod = _reload_shared()

    # Simulate "package not installed" — setting sys.modules entry to None
    # causes `import google.cloud.storage` to raise ImportError.
    with patch.dict(sys.modules, {"google.cloud.storage": None}):
        result = mod.write_pdf_to_gcs_or_local(
            b"fallback content",
            source_key="aqa.org.uk",
            subject="physics",
            language="en",
            sha256="missing_pkg",
            local_root=tmp_path,
        )

    # Local fallback path returned.
    assert result.startswith(str(tmp_path))
    assert "google-cloud-storage not installed" in caplog.text or "falling back" in caplog.text
    assert Path(result).exists()


def test_gcs_helper_handles_gcs_upload_failure_gracefully(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """When the GCS upload raises, the helper falls back to local + logs a warning."""
    monkeypatch.setenv("GCS_RAW_BUCKET", "test-bucket")

    mod = _reload_shared()

    fake_blob = MagicMock(name="Blob")
    fake_blob.upload_from_string.side_effect = RuntimeError("GCS 503")
    fake_bucket = MagicMock(name="Bucket")
    fake_bucket.blob.return_value = fake_blob
    fake_client = MagicMock(name="Client")
    fake_client.bucket.return_value = fake_bucket

    fake_storage = MagicMock(name="google.cloud.storage")
    fake_storage.Client.return_value = fake_client

    with patch.dict(sys.modules, {"google.cloud.storage": fake_storage}):
        result = mod.write_pdf_to_gcs_or_local(
            b"fallback content",
            source_key="ocr.org.uk",
            subject="biology",
            language="en",
            sha256="upload_fail",
            local_root=tmp_path,
        )

    # Local fallback path returned.
    assert result.startswith(str(tmp_path))
    assert "GCS upload failed" in caplog.text or "falling back" in caplog.text
    assert Path(result).exists()
