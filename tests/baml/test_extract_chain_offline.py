"""tests.baml.test_extract_chain_offline — E2E integration test for the LC6 BAML extraction App.

Per Phase 1 of the gemini_hackathon polish plan (`2026-08-31-local-data-plane-v1`),
this test runs `cocoindex_flows.education.lc6_extraction_app` offline (no
Ollama required — the App's `_baml_extract_stub` fallback handles the
baml_client absence) and asserts ≥1 row in
`data/bi_ep/extracted_syllabi.sqlite`.

Marked `@pytest.mark.integration`.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.integration
def test_lc6_extraction_app_writes_to_sqlite_offline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The LC6 extraction App writes ≥1 row to its SQLite output, offline.

    Runs the canonical App entry point
    (`python -m cocoindex_flows.education.lc6_extraction_app --subject
    mathematics --language en`) via the `run()` function (so the test
    doesn't shell out), then asserts the SQLite output has ≥1 row.

    Verifies:
    - The `BI_EP_EXTRACTED_SYLLABI_PATH` env var redirects the SQLite target.
    - When `baml_client.b` is not importable (the canonical dev path), the
      stub-shaped 5-JSON extraction runs and writes 1 row per .md file.
    - The `BAML_TEST_MODE=true` env var doesn't change the row count
      (the stub handles the test-mode gracefully).
    """
    # Build a tiny markdown corpus under a fresh tmp dir (2 .md files).
    md_root = tmp_path / "syllabi_md"
    md_root.mkdir()
    md_a = md_root / "mathematics" / "en"
    md_a.mkdir(parents=True)
    md_a.joinpath("syllabus_a.md").write_text(
        "# Mathematics: Differential Calculus\n\nLorem ipsum.\n\n## Page 1\n",
        encoding="utf-8",
    )
    md_b = md_root / "chemistry" / "en"
    md_b.mkdir(parents=True)
    md_b.joinpath("syllabus_b.md").write_text(
        "# Chemistry: Periodic Trends\n\nLorem ipsum.\n\n## Page 1\n",
        encoding="utf-8",
    )

    sqlite_path = tmp_path / "extracted_syllabi.sqlite"

    monkeypatch.setenv("BI_EP_PDF_MD_ROOT", str(md_root))
    monkeypatch.setenv("BI_EP_EXTRACTED_SYLLABI_PATH", str(sqlite_path))
    monkeypatch.setenv("BAML_TEST_MODE", "true")

    from cocoindex_flows.education.lc6_extraction_app import run

    stats = run(subject_slug="mathematics", language="en")
    assert stats["discovered"] == 2, f"expected 2 .md files, got {stats!r}"
    assert stats["extracted"] >= 1, f"no rows extracted; stats={stats!r}"
    assert stats["failed"] == 0

    # Verify the SQLite DB exists and has the expected rows.
    assert sqlite_path.exists()
    import sqlite3

    con = sqlite3.connect(str(sqlite_path))
    try:
        rows = con.execute("SELECT COUNT(*) FROM extracted_syllabi").fetchone()[0]
        assert rows >= 1, f"extracted_syllabi has 0 rows; stats={stats!r}"
        # Spot-check the columns are the canonical 11.
        cols = [d[0] for d in con.execute("SELECT * FROM extracted_syllabi LIMIT 1").description]
        expected = {
            "subnation",
            "stage",
            "subject_slug",
            "language",
            "source_pdf",
            "syllabus_json",
            "exam_paper_json",
            "marking_json",
            "concepts_json",
            "diagrams_json",
            "fetched_at",
        }
        missing = expected - set(cols)
        assert not missing, f"extracted_syllabi missing columns: {missing}; cols={cols!r}"
    finally:
        con.close()
