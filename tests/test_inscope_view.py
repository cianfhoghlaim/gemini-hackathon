"""tests/test_inscope_view.py — the canonical in-scope substrate view.

Per `openspec/changes/2026-08-31-submission-scope-realignment-v1/specs/in-scope-substrate/spec.md`:
  - `raw.official_documents_in_scope` MUST exist
  - Row count MUST be in [90, 110]
  - No rows MUST have language == 'ga' (Gaeilge deferred)

These tests are the guardrail for the SUBMISSION_SCOPE.md promises.
"""
from __future__ import annotations

import pathlib

import duckdb


REPO = pathlib.Path("/Users/cianmacandeisigh/dev/gemini_hackathon")
DB_PATH = REPO / "gemini_hackathon.duckdb"


def test_inscope_view_exists() -> None:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    rows = con.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'raw' AND table_name = 'official_documents_in_scope'"
    ).fetchall()
    con.close()
    assert len(rows) == 1, (
        f"raw.official_documents_in_scope view missing — run scripts/migrate_deferred_rows.py"
    )


def test_inscope_view_row_count() -> None:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    count = con.execute("SELECT COUNT(*) FROM raw.official_documents_in_scope").fetchone()[0]
    con.close()
    assert 90 <= count <= 110, (
        f"expected 90-110 in-scope rows (97 PDFs + ~6 NCCE per-subject tags), got {count}"
    )


def test_inscope_view_no_gaeilge() -> None:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    ga_count = con.execute(
        "SELECT COUNT(*) FROM raw.official_documents_in_scope "
        "WHERE jurisdiction = 'Ireland' AND UPPER(language) = 'GA'"
    ).fetchone()[0]
    con.close()
    assert ga_count == 0, (
        f"Gaeilge LC PDFs should be deferred; found {ga_count} ga/ rows in the in-scope view"
    )


def test_inscope_view_includes_ncca_policy() -> None:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    ncca_count = con.execute(
        "SELECT COUNT(*) FROM raw.official_documents_in_scope "
        "WHERE source_key LIKE 'ncca%' OR jurisdiction = 'Ireland' AND level = 'senior_cycle'"
    ).fetchone()[0]
    con.close()
    assert ncca_count >= 5, f"expected ≥5 NCCA policy rows, got {ncca_count}"


def test_inscope_view_includes_ncce() -> None:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    ncce_count = con.execute(
        "SELECT COUNT(*) FROM raw.official_documents_in_scope "
        "WHERE jurisdiction = 'United Kingdom (NCCE)'"
    ).fetchone()[0]
    con.close()
    assert ncce_count >= 5, f"expected ≥5 NCCE rows (5 artefacts), got {ncce_count}"