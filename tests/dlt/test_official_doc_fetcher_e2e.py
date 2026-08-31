"""tests.dlt.test_official_doc_fetcher_e2e — E2E integration test for the official_doc_fetcher DLT pipeline.

Per Phase 1 of the gemini_hackathon polish plan (`2026-08-31-local-data-plane-v1`),
this test exercises the full local data plane:
- sets `DUCKDB_PATH` to a `tmp_path` so we don't touch the repo-root DuckDB
- runs `dlt_pipelines.official_doc_fetcher.run()`
- asserts the `raw.official_documents` table has ≥1 row

Marked `@pytest.mark.integration` and skipped when `dlt` is not installed.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.integration
def test_official_doc_fetcher_writes_to_local_duckdb(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Running `dlt_pipelines.official_doc_fetcher.run()` populates a fresh DuckDB file.

    Verifies:
    - The DLT pipeline writes to the `DUCKDB_PATH` env-var target.
    - The `raw.official_documents` table is created and has ≥1 row.
    - The 35-row remote-URL catalog emits at least 1 row (the 8 non-Ireland
      jurisdictions + NCCE yield 35 rows even when the Ireland filesystem
      PDF cache is missing; this matches the Phase 0 baseline expectation).
    """
    try:
        import dlt  # noqa: F401  (verify dlt is importable)
    except ImportError:
        pytest.skip("dlt is not installed; skipping the data-plane E2E test")

    # Redirect the DLT destination to a fresh tmp file.
    db_path = tmp_path / "data_plane_smoke.duckdb"
    monkeypatch.setenv("DUCKDB_PATH", str(db_path))

    # Import here (after the env-var is set + dlt is verified) so the
    # `_shared.DUCKDB_PATH` lazy-resolves to our tmp file.
    from dlt_pipelines.official_doc_fetcher import run

    load_info = run(database_path=db_path)

    # The DuckDB file should now exist on disk.
    assert db_path.exists(), f"DuckDB file was not created at {db_path}"

    # Open it read-only and verify the `raw.official_documents` table
    # has ≥1 row.
    import duckdb

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        row_count = con.execute(
            "SELECT COUNT(*) FROM raw.official_documents"
        ).fetchone()[0]
        assert row_count >= 1, (
            f"raw.official_documents has 0 rows; load_info={load_info!r}"
        )
        # Also verify the schema contract (the 12 canonical columns).
        cols = [
            row[1]
            for row in con.execute(
                "PRAGMA table_info('raw.official_documents')"
            ).fetchall()
        ]
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
        missing = expected - set(cols)
        assert not missing, f"raw.official_documents missing columns: {missing}"
    finally:
        con.close()
