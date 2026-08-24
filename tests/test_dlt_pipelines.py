"""Smoke tests for the 3 DLT pipelines.

4 tests:

* :func:`dlt_pipelines.official_doc_fetcher` produces the
  ``official_documents`` table with the canonical columns.
* :func:`dlt_pipelines.official_doc_fetcher` handles missing PDFs
  gracefully (no exception, empty yield).
* :func:`dlt_pipelines.safeguarding_fetcher` produces the
  ``safeguarding_policies`` table with the canonical columns.
* :func:`dlt_pipelines.pdf_page_metadata._extract_pdf_metadata`
  extracts the page_count from a local PDF.

Tests do NOT exercise the live DuckDB destination — they verify
the resource functions yield well-formed rows and that the
shared helpers produce correct metadata. The full pipeline runs
are guarded by ``@pytest.mark.integration``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Attempt to import the dlt_pipelines modules. The DLT tests are
# skipped when the import fails (the project requires Python 3.11+
# but tests may run on 3.10; the dlt_pipelines/_shared.py module
# uses Python 3.11+ syntax). This ensures the test module is always
# importable, so pytest can collect the other tests.
try:
    from dlt_pipelines._shared import (  # noqa: PLC0415 — lazy for env compat
        DUCKDB_PATH,
        JURISDICTION_BOARDS,
        OFFICIAL_DOC_COLUMNS,
        PDF_METADATA_COLUMNS,
        REPO_ROOT,
        SAFEGUARDING_BODIES,
        SAFEGUARDING_POLICY_COLUMNS,
        sha256_file,
        safe_stat,
        with_retry,
    )
    _DLT_SHARED_AVAILABLE = True
except ImportError:
    # dlt_pipelines._shared uses Python 3.11+ syntax (e.g. ``from
    # datetime import UTC``). On older Pythons the import fails.
    # The DLT-specific tests below will skip via _has_dlt(); the
    # helper tests that don't touch DLT will be skipped via the
    # _DLT_SHARED_AVAILABLE flag.
    _DLT_SHARED_AVAILABLE = False
    DUCKDB_PATH = None  # type: ignore[assignment]
    JURISDICTION_BOARDS = {}  # type: ignore[assignment]
    OFFICIAL_DOC_COLUMNS = ()  # type: ignore[assignment]
    PDF_METADATA_COLUMNS = ()  # type: ignore[assignment]
    REPO_ROOT = None  # type: ignore[assignment]
    SAFEGUARDING_BODIES = {}  # type: ignore[assignment]
    SAFEGUARDING_POLICY_COLUMNS = ()  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _has_dlt() -> bool:
    """Return whether ``dlt`` is importable (it's an optional dependency in CI)."""
    try:
        import dlt  # noqa: F401
    except ImportError:
        return False
    return True


# ---------------------------------------------------------------------------
# official_doc_fetcher
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _DLT_SHARED_AVAILABLE or not _has_dlt(),
    reason="dlt not installed / Python 3.11+ required",
)
def test_official_doc_fetcher_creates_official_documents_table(tmp_path: Path) -> None:
    """The official_doc_fetcher resources yield rows with the canonical columns.

    Asserts:

    * The :data:`OFFICIAL_DOC_COLUMNS` tuple has all 12 canonical columns.
    * The :func:`official_documents_source` returns a list with one
      resource per jurisdiction.
    * Each row produced by the remote resources has the canonical
      column shape (no missing required keys).
    """
    from dlt_pipelines.official_doc_fetcher import (
        KNOWN_OFFICIAL_URLS,
        OFFICIAL_DOC_COLUMN_HINTS,
        england_aqa_documents,
        official_documents_source,
    )

    # The column contract.
    expected = {
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
    }
    assert set(OFFICIAL_DOC_COLUMNS) == expected
    assert set(OFFICIAL_DOC_COLUMN_HINTS.keys()) == expected

    # The 8-resource source.
    resources = official_documents_source()
    assert isinstance(resources, list)
    assert len(resources) == 8

    # The england_aqa resource yields the KNOWN_OFFICIAL_URLS rows.
    rows = list(england_aqa_documents())
    assert len(rows) == len(KNOWN_OFFICIAL_URLS["aqa.org.uk"])
    for row in rows:
        # Every row has the canonical columns (None is OK for the
        # remote-URL fields like file_size_bytes + page_count +
        # sha256_hash).
        for col in expected:
            assert col in row, f"missing column {col!r} in row {row!r}"
        assert row["source_key"] == "aqa.org.uk"
        assert row["jurisdiction"] == "England"
        assert row["source_kind"] == "remote_url"


@pytest.mark.skipif(
    not _DLT_SHARED_AVAILABLE or not _has_dlt(),
    reason="dlt not installed / Python 3.11+ required",
)
def test_official_doc_fetcher_handles_missing_pdfs_gracefully(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Ireland NCCA resource yields zero rows when LC_SUBJECTS_PATH is missing.

    The :func:`ireland_ncca_documents` resource is filesystem-based;
    when the configured ``LC_SUBJECTS_PATH`` does not exist, it must
    log a warning and yield zero rows (no exception).
    """
    monkeypatch.setenv("LC_SUBJECTS_PATH", str(tmp_path / "does-not-exist"))

    from dlt_pipelines.official_doc_fetcher import ireland_ncca_documents

    rows = list(ireland_ncca_documents())
    assert rows == []


# ---------------------------------------------------------------------------
# safeguarding_fetcher
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _DLT_SHARED_AVAILABLE or not _has_dlt(),
    reason="dlt not installed / Python 3.11+ required",
)
def test_safeguarding_fetcher_creates_safeguarding_policies_table(
    tmp_path: Path,
) -> None:
    """The safeguarding_fetcher resources yield rows with the canonical columns.

    Asserts:

    * The :data:`SAFEGUARDING_POLICY_COLUMNS` tuple has all 10
      canonical columns.
    * The :func:`safeguarding_policies_source` returns a list with
      one resource per safeguarding body.
    * The ie_safeguarding resource yields at least one row per
      published policy.
    """
    from dlt_pipelines.safeguarding_fetcher import (
        SAFEGUARDING_POLICIES,
        ireland_safeguarding,
        safeguarding_policies_source,
    )

    expected = {
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
    }
    assert set(SAFEGUARDING_POLICY_COLUMNS) == expected

    resources = safeguarding_policies_source()
    assert isinstance(resources, list)
    assert len(resources) == 5

    # The Ireland safeguarding resource yields at least one row.
    rows = list(ireland_safeguarding())
    assert len(rows) == len(SAFEGUARDING_POLICIES["gov.ie/education"])
    for row in rows:
        for col in expected:
            assert col in row, f"missing column {col!r} in row {row!r}"
        assert row["source_key"] == "gov.ie/education"
        assert row["jurisdiction"] == "Ireland"
        assert row["publication_year"] >= 2017  # the earliest known policy


# ---------------------------------------------------------------------------
# pdf_page_metadata
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _DLT_SHARED_AVAILABLE or not _has_dlt(),
    reason="dlt not installed / Python 3.11+ required",
)
def test_pdf_metadata_extracts_page_count(tmp_path: Path) -> None:
    """``_extract_pdf_metadata`` returns a page_count for a valid PDF.

    Uses a minimal PDF generated on the fly (a real PDF with one page
    via the ``pypdf`` writer, when available; otherwise an existing
    file from ``data/`` if it exists).
    """
    try:
        from pypdf import PdfWriter  # type: ignore[import-not-found]
    except ImportError:
        pytest.skip("pypdf is not installed in this environment")

    pdf_path = tmp_path / "one-page.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    with pdf_path.open("wb") as fh:
        writer.write(fh)

    from dlt_pipelines.pdf_page_metadata import _extract_pdf_metadata

    metadata = _extract_pdf_metadata(pdf_path)
    assert metadata["page_count"] == 1
    assert isinstance(metadata["fonts_detected"], list)
    assert metadata["image_count"] == 0
    # has_text_layer is False (blank page has no text).
    assert metadata["has_text_layer"] is False
    # file_size_bytes is > 0 (we just wrote the file).
    assert metadata["file_size_bytes"] > 0


# ---------------------------------------------------------------------------
# _shared helpers
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _DLT_SHARED_AVAILABLE,
    reason="dlt_pipelines._shared not importable (Python 3.11+ required)",
)
def test_shared_helpers_sha256_round_trip(tmp_path: Path) -> None:
    """``sha256_file`` returns a stable hex digest for the same file."""
    sample = tmp_path / "sample.txt"
    sample.write_bytes(b"hello world")
    digest = sha256_file(sample)
    # 64 hex chars = SHA256 length.
    assert len(digest) == 64
    assert digest == sha256_file(sample)  # idempotent
    # Known SHA256 of "hello world".
    assert digest == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"


@pytest.mark.skipif(
    not _DLT_SHARED_AVAILABLE,
    reason="dlt_pipelines._shared not importable (Python 3.11+ required)",
)
def test_shared_helpers_safe_stat_returns_none_for_missing(tmp_path: Path) -> None:
    """``safe_stat`` returns ``None`` for missing paths (graceful)."""
    assert safe_stat(tmp_path / "does-not-exist.txt") is None


@pytest.mark.skipif(
    not _DLT_SHARED_AVAILABLE,
    reason="dlt_pipelines._shared not importable (Python 3.11+ required)",
)
def test_shared_helpers_safe_stat_returns_size(tmp_path: Path) -> None:
    """``safe_stat`` returns the file size for an existing regular file."""
    sample = tmp_path / "size.txt"
    sample.write_bytes(b"abcde")  # 5 bytes
    assert safe_stat(sample) == 5


@pytest.mark.skipif(
    not _DLT_SHARED_AVAILABLE,
    reason="dlt_pipelines._shared not importable (Python 3.11+ required)",
)
def test_shared_helpers_with_retry_succeeds_after_retries() -> None:
    """``with_retry`` retries transient failures and returns the result."""
    call_count = {"n": 0}

    @with_retry(attempts=3, backoff_seconds=0.001)
    def flaky_function() -> str:
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise FileNotFoundError("not yet")
        return "ok"

    assert flaky_function() == "ok"
    assert call_count["n"] == 3


@pytest.mark.skipif(
    not _DLT_SHARED_AVAILABLE,
    reason="dlt_pipelines._shared not importable (Python 3.11+ required)",
)
def test_shared_helpers_with_retry_propagates_after_budget() -> None:
    """``with_retry`` raises the last exception when the budget is exhausted."""
    @with_retry(attempts=2, backoff_seconds=0.001)
    def always_fails() -> None:
        raise FileNotFoundError("permanent failure")

    with pytest.raises(FileNotFoundError):
        always_fails()


# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _DLT_SHARED_AVAILABLE,
    reason="dlt_pipelines._shared not importable (Python 3.11+ required)",
)
def test_jurisdiction_boards_has_8_entries() -> None:
    """The 8 canonical British Isles jurisdictions are in :data:`JURISDICTION_BOARDS`."""
    assert len(JURISDICTION_BOARDS) == 8
    assert "ncca.ie" in JURISDICTION_BOARDS
    assert "aqa.org.uk" in JURISDICTION_BOARDS
    assert "ccea.org.uk" in JURISDICTION_BOARDS


@pytest.mark.skipif(
    not _DLT_SHARED_AVAILABLE,
    reason="dlt_pipelines._shared not importable (Python 3.11+ required)",
)
def test_safeguarding_bodies_has_5_entries() -> None:
    """The 5 safeguarding bodies are in :data:`SAFEGUARDING_BODIES`."""
    assert len(SAFEGUARDING_BODIES) == 5
    assert "gov.ie/education" in SAFEGUARDING_BODIES
    assert "gov.uk/dfe" in SAFEGUARDING_BODIES
    assert "ccea.org.uk/safeguarding" in SAFEGUARDING_BODIES


@pytest.mark.skipif(
    not _DLT_SHARED_AVAILABLE,
    reason="dlt_pipelines._shared not importable (Python 3.11+ required)",
)
def test_duckdb_path_lives_at_repo_root() -> None:
    """The DuckDB destination path lives at the repo root."""
    assert DUCKDB_PATH.parent == REPO_ROOT
    assert DUCKDB_PATH.name == "gemini_hackathon.duckdb"


@pytest.mark.skipif(
    not _DLT_SHARED_AVAILABLE,
    reason="dlt_pipelines._shared not importable (Python 3.11+ required)",
)
def test_pdf_metadata_columns_contract() -> None:
    """The PDF metadata columns tuple has the canonical 9 fields."""
    expected = {
        "pdf_path",
        "source_key",
        "sha256_hash",
        "page_count",
        "fonts_detected",
        "image_count",
        "has_text_layer",
        "file_size_bytes",
        "extracted_at",
    }
    assert set(PDF_METADATA_COLUMNS) == expected