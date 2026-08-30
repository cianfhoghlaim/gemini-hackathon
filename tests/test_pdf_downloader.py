"""test_pdf_downloader.py — Phase 2a verification of the remote-URL PDF downloader.

Tests:
  1. ``_safe_filename_part`` sanitizes directory names correctly.
  2. ``_page_count`` returns the correct page count for a valid PDF.
  3. ``_page_count`` returns ``None`` for invalid bytes.
  4. ``_compute_sha256`` matches hashlib directly.
  5. ``_already_downloaded`` returns False for an empty tree, True for
     a tree that already contains the file.
  6. ``_local_path_for`` builds the canonical path with the right shape.
  7. ``run_downloader`` is a no-op when the DuckDB file doesn't exist
     (returns the empty stats dict).
  8. ``run_downloader`` with a mock fetcher writes the PDF + updates the
     DuckDB row + is idempotent on re-run (skips on sha256 match).

The pdf_downloader module is loaded via ``importlib.util.spec_from_file_location``
to bypass the ``dlt_pipelines`` package's __init__.py (which eagerly imports
``dlt``). pdf_downloader.py itself has zero ``dlt`` dependency.
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import pathlib
import sqlite3

import pytest


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "_test_pd_mod",
        pathlib.Path(__file__).resolve().parent.parent
        / "dlt_pipelines" / "pdf_downloader.py",
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Module-level binding — single load per test session.
pd = _load_module()


def _minimal_pdf_bytes(page_count: int = 1) -> bytes:
    """Build a minimal valid PDF byte string with ``page_count`` pages."""
    objects: list[str] = []
    objects.append("<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(
        f"<< /Type /Pages /Kids [{ ' '.join(f'{3+i} 0 R' for i in range(page_count))} ] /Count {page_count} >>"
    )
    for i in range(page_count):
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>"
        )
    body_parts = ["%PDF-1.4\n"]
    offsets: list[int] = []
    for i, obj in enumerate(objects):
        offsets.append(sum(len(p.encode("latin-1")) for p in body_parts))
        body_parts.append(f"{i+1} 0 obj\n{obj}\nendobj\n")
    xref_offset = sum(len(p.encode("latin-1")) for p in body_parts)
    body_parts.append(
        f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n"
        + "".join(f"{o:010d} 00000 n \n" for o in offsets)
        + "trailer\n<< /Size "
        + str(len(objects)+1)
        + " /Root 1 0 R >>\nstartxref\n"
        + str(xref_offset)
        + "\n%%EOF\n"
    )
    return "".join(body_parts).encode("latin-1")


@pytest.fixture
def duckdb_path(tmp_path: pathlib.Path) -> pathlib.Path:
    """Create a fresh DuckDB-compatible sqlite3 file with one source_key."""
    path = tmp_path / "test.duckdb"
    with sqlite3.connect(str(path)) as conn:
        conn.execute(
            """
            CREATE TABLE official_documents (
                source_key TEXT,
                source_name TEXT,
                jurisdiction TEXT,
                level TEXT,
                language TEXT,
                subject TEXT,
                pdf_path TEXT,
                file_size_bytes INTEGER,
                page_count INTEGER,
                sha256_hash TEXT,
                source_kind TEXT,
                fetched_at TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO official_documents VALUES
                ('aqa.org.uk', 'AQA', 'England', 'a_level', 'en', 'mathematics',
                 'http://example.com/sample.pdf', NULL, NULL, NULL, 'remote_url',
                 '2026-08-30T12:00:00Z')
            """
        )
        conn.commit()
    return path


def test_safe_filename_part_basic() -> None:
    assert pd._safe_filename_part("AQA.org.uk") == "aqa-org-uk"
    assert pd._safe_filename_part("Mathematics A-Level") == "mathematics-a-level"
    assert pd._safe_filename_part("computer_science") == "computer-science"
    assert pd._safe_filename_part("  spaces  ") == "spaces"
    assert pd._safe_filename_part("!!!") == "unknown"
    assert pd._safe_filename_part("hello/world") == "hello-world"


def test_page_count_valid_pdf() -> None:
    pdf_bytes = _minimal_pdf_bytes(page_count=3)
    assert pd._page_count(pdf_bytes) == 3


def test_page_count_invalid_bytes() -> None:
    assert pd._page_count(b"not a pdf") is None
    assert pd._page_count(b"") is None


def test_compute_sha256_matches_hashlib() -> None:
    sample = b"the quick brown fox jumps over the lazy dog"
    assert pd._compute_sha256(sample) == hashlib.sha256(sample).hexdigest()


def test_already_downloaded_empty(tmp_path: pathlib.Path) -> None:
    root = tmp_path / "empty_root"
    root.mkdir()
    assert pd._already_downloaded("a" * 64, root) is False


def test_already_downloaded_present(tmp_path: pathlib.Path) -> None:
    sha = "b" * 64
    root = tmp_path / "raw"
    target = root / "aqa-org-uk" / "mathematics" / "en" / f"{sha}.pdf"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"fake pdf content")
    assert pd._already_downloaded(sha, root) is True


def test_local_path_for_shape() -> None:
    root = pathlib.Path("/tmp/raw")
    path = pd._local_path_for(
        source_key="aqa.org.uk",
        subject="Mathematics A-Level",
        language="en",
        sha256="abc123",
        root=root,
    )
    assert path == pathlib.Path(
        "/tmp/raw/aqa-org-uk/mathematics-a-level/en/abc123.pdf"
    )


def test_run_downloader_no_duckdb(tmp_path: pathlib.Path) -> None:
    """No DuckDB file -> empty stats, no crash."""
    stats = pd.run_downloader(
        duckdb_path=tmp_path / "missing.duckdb",
        raw_root=tmp_path / "raw",
    )
    assert stats == {"considered": 0, "downloaded": 0, "skipped": 0, "failed": 0}


def test_run_downloader_mock_fetch_writes_file(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, duckdb_path: pathlib.Path
) -> None:
    """Mock the fetcher; verify the file is written + the DuckDB row is updated."""
    fake_bytes = _minimal_pdf_bytes(page_count=2)
    fake_sha = hashlib.sha256(fake_bytes).hexdigest()

    def fake_fetch(url: str, *, timeout_seconds: int = 30) -> bytes:
        assert url == "http://example.com/sample.pdf"
        return fake_bytes

    monkeypatch.setattr(pd, "_fetch_bytes", fake_fetch)

    stats = pd.run_downloader(
        duckdb_path=duckdb_path,
        raw_root=tmp_path / "raw",
    )
    assert stats == {"considered": 1, "downloaded": 1, "skipped": 0, "failed": 0}

    target = tmp_path / "raw" / "aqa-org-uk" / "mathematics" / "en" / f"{fake_sha}.pdf"
    assert target.exists()
    assert target.read_bytes() == fake_bytes

    with sqlite3.connect(str(duckdb_path)) as conn:
        row = conn.execute(
            "SELECT pdf_path, file_size_bytes, page_count, sha256_hash, source_kind "
            "FROM official_documents WHERE source_key='aqa.org.uk'"
        ).fetchone()
    assert row[0] == str(target)
    assert row[1] == len(fake_bytes)
    assert row[2] == 2
    assert row[3] == fake_sha
    assert row[4] == "downloaded"


def test_run_downloader_idempotent_second_run(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, duckdb_path: pathlib.Path
) -> None:
    """Re-running the downloader with the file already on disk -> no-op.

    After the first run, the DuckDB row has source_kind='downloaded', so
    the second run's ``_iter_remote_url_rows`` query returns zero rows and
    ``run_downloader`` is effectively a no-op (considered=0). The PDF on
    disk is preserved.
    """
    fake_bytes = _minimal_pdf_bytes(page_count=1)
    fake_sha = hashlib.sha256(fake_bytes).hexdigest()

    call_count = {"n": 0}

    def fake_fetch(url: str, *, timeout_seconds: int = 30) -> bytes:
        call_count["n"] += 1
        return fake_bytes

    monkeypatch.setattr(pd, "_fetch_bytes", fake_fetch)

    raw_root = tmp_path / "raw"
    stats1 = pd.run_downloader(duckdb_path=duckdb_path, raw_root=raw_root)
    assert stats1 == {"considered": 1, "downloaded": 1, "skipped": 0, "failed": 0}

    stats2 = pd.run_downloader(duckdb_path=duckdb_path, raw_root=raw_root)
    assert stats2 == {"considered": 0, "downloaded": 0, "skipped": 0, "failed": 0}

    # The PDF on disk is preserved.
    target = raw_root / "aqa-org-uk" / "mathematics" / "en" / f"{fake_sha}.pdf"
    assert target.exists()
    assert target.read_bytes() == fake_bytes

    # The fetcher was only invoked once.
    assert call_count["n"] == 1


def test_run_downloader_handles_fetch_failure(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, duckdb_path: pathlib.Path
) -> None:
    """If the fetcher raises, the row stays as remote_url (not flipped)."""
    def fake_fetch(url: str, *, timeout_seconds: int = 30) -> bytes:
        raise RuntimeError("simulated network failure")

    monkeypatch.setattr(pd, "_fetch_bytes", fake_fetch)

    stats = pd.run_downloader(
        duckdb_path=duckdb_path,
        raw_root=tmp_path / "raw",
    )
    assert stats["failed"] == 1
    assert stats["downloaded"] == 0

    with sqlite3.connect(str(duckdb_path)) as conn:
        row = conn.execute(
            "SELECT source_kind, pdf_path FROM official_documents "
            "WHERE source_key='aqa.org.uk'"
        ).fetchone()
    assert row[0] == "remote_url"
    assert row[1] == "http://example.com/sample.pdf"


def test_run_downloader_skips_remote_url_zero_rows(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """DuckDB table exists but has zero remote_url rows -> considered=0."""
    db = tmp_path / "empty.duckdb"
    with sqlite3.connect(str(db)) as conn:
        conn.execute(
            """
            CREATE TABLE official_documents (
                source_key TEXT, source_name TEXT, jurisdiction TEXT,
                level TEXT, language TEXT, subject TEXT, pdf_path TEXT,
                file_size_bytes INTEGER, page_count INTEGER, sha256_hash TEXT,
                source_kind TEXT, fetched_at TEXT
            )
            """
        )
        conn.commit()

    def fail_fetch(url: str, *, timeout_seconds: int = 30) -> bytes:
        raise AssertionError("fetch should not be called when no rows")

    monkeypatch.setattr(pd, "_fetch_bytes", fail_fetch)

    stats = pd.run_downloader(duckdb_path=db, raw_root=tmp_path / "raw")
    assert stats == {"considered": 0, "downloaded": 0, "skipped": 0, "failed": 0}
