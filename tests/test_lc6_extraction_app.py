"""test_lc6_extraction_app.py — Phase 3a verification of the LC6 BAML extraction App.

Tests:
  1. ``_extract_subnation_stage_subject_language`` derives the 4 fields correctly.
  2. ``_baml_extract_stub`` returns 5 stub JSON strings.
  3. ``_ensure_sqlite_table`` creates the table.
  4. ``_upsert_sqlite_row`` inserts + updates (idempotent).
  5. ``_process_one`` reads a .md, calls _baml_extract_all (stub), upserts.
  6. ``run`` returns stats + writes to SQLite when given a real .md.
  7. ``run`` returns the no-md stats when md_root is missing.
  8. ``_baml_extract_all`` gracefully falls back to stub when baml_client missing.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sqlite3
from dataclasses import asdict


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "_test_lc6_mod",
        pathlib.Path(__file__).resolve().parent.parent
        / "cocoindex_flows"
        / "education"
        / "lc6_extraction_app.py",
    )
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    # Register in sys.modules so dataclasses can resolve cls.__module__
    # (the @dataclass decorator looks up the module via sys.modules
    # at class-creation time).
    import sys as _sys

    _sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


# Module-level binding — single load per test session.
mod = _load_module()


def _fake_md(
    tmp_path: pathlib.Path,
    subnation: str = "aqa.org.uk",
    subject: str = "mathematics",
    lang: str = "en",
) -> pathlib.Path:
    """Write a fake .md file with one page of content under the canonical layout."""
    md_dir = tmp_path / subnation / subject / lang
    md_dir.mkdir(parents=True)
    path = md_dir / "abc123def456.md"
    path.write_text(
        f"# {subject} Syllabus ({lang})\n\n## Page 1\n\nThis is a stub.\n",
        encoding="utf-8",
    )
    return path


def test_extract_subnation_stage_subject_language_derives_correctly(tmp_path: pathlib.Path) -> None:
    md = _fake_md(tmp_path)
    subnation, stage, subject, lang = mod._extract_subnation_stage_subject_language(
        md, md_root=tmp_path
    )
    assert subnation == "aqa.org.uk"
    assert subject == "mathematics"
    assert lang == "en"
    # Stage defaults to leaving_cycle (Phase 3a treats all subjects as LC).
    assert stage == "leaving_cycle"


def test_baml_extract_stub_returns_5_json_strings() -> None:
    results = mod._baml_extract_stub(
        "## Page 1\n\nstub content",
        subject_slug="mathematics",
        language="en",
    )
    assert set(results.keys()) == {"syllabus", "exam_paper", "marking", "concepts", "diagrams"}
    for key, value in results.items():
        assert value is not None, f"{key} is None"
        parsed = json.loads(value)
        assert parsed["subject_slug"] == "mathematics"
        assert parsed["language"] == "en"
        assert parsed["stub"] is True


def test_baml_extract_all_falls_back_to_stub() -> None:
    """When baml_client is missing, returns the stub shape."""
    results = mod._baml_extract_all(
        "## Page 1\n\nstub content",
        subject_slug="chemistry",
        language="ga",
    )
    assert set(results.keys()) == {"syllabus", "exam_paper", "marking", "concepts", "diagrams"}
    for value in results.values():
        assert value is not None
        json.loads(value)  # Must be valid JSON


def test_ensure_sqlite_table_creates_table(tmp_path: pathlib.Path) -> None:
    db = tmp_path / "test.sqlite"
    mod._ensure_sqlite_table(db)
    with sqlite3.connect(str(db)) as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='extracted_syllabi'"
        ).fetchone()
    assert row is not None
    assert row[0] == "extracted_syllabi"


def test_upsert_sqlite_row_inserts_and_updates(tmp_path: pathlib.Path) -> None:
    db = tmp_path / "test.sqlite"
    mod._ensure_sqlite_table(db)
    row = mod.ExtractionRow(
        subnation="aqa.org.uk",
        stage="leaving_cycle",
        subject_slug="mathematics",
        language="en",
        source_pdf="aqa.org.uk/mathematics/en/abc.md",
        syllabus_json='{"syllabus": "v1"}',
    )
    mod._upsert_sqlite_row(db, row)

    # Read back
    with sqlite3.connect(str(db)) as conn:
        stored = conn.execute(
            "SELECT syllabus_json FROM extracted_syllabi WHERE source_pdf='aqa.org.uk/mathematics/en/abc.md'"
        ).fetchone()
    assert stored[0] == '{"syllabus": "v1"}'

    # Second insert with updated syllabus_json should upsert (not duplicate)
    row.syllabus_json = '{"syllabus": "v2"}'
    mod._upsert_sqlite_row(db, row)
    with sqlite3.connect(str(db)) as conn:
        rows = conn.execute(
            "SELECT syllabus_json FROM extracted_syllabi WHERE source_pdf='aqa.org.uk/mathematics/en/abc.md'"
        ).fetchall()
    assert len(rows) == 1
    assert rows[0][0] == '{"syllabus": "v2"}'


def test_process_one_reads_md_and_writes_row(tmp_path: pathlib.Path) -> None:
    md_root = tmp_path
    sqlite_path = tmp_path / "extract.sqlite"
    md = _fake_md(md_root)

    row = mod._process_one(
        md,
        md_root=md_root,
        sqlite_path=sqlite_path,
        subject_slug="mathematics",
        language="en",
    )
    assert row.subnation == "aqa.org.uk"
    assert row.subject_slug == "mathematics"
    assert row.language == "en"
    assert row.source_pdf == "aqa.org.uk/mathematics/en/abc123def456.md"
    # All 5 JSON fields populated (stub values).
    for field_name in (
        "syllabus_json",
        "exam_paper_json",
        "marking_json",
        "concepts_json",
        "diagrams_json",
    ):
        assert getattr(row, field_name) is not None, f"{field_name} is None"
        json.loads(getattr(row, field_name))  # Valid JSON

    # SQLite row was upserted.
    with sqlite3.connect(str(sqlite_path)) as conn:
        stored = conn.execute("SELECT syllabus_json FROM extracted_syllabi").fetchone()
    assert stored[0] is not None


def test_run_no_md_root(tmp_path: pathlib.Path) -> None:
    """Missing md_root -> empty stats, no crash."""
    stats = mod.run(
        subject_slug="mathematics",
        language="en",
        md_root=tmp_path / "missing",
        sqlite_path=tmp_path / "extract.sqlite",
    )
    assert stats == {"discovered": 0, "extracted": 0, "failed": 0}


def test_run_writes_row_per_md(tmp_path: pathlib.Path) -> None:
    md_root = tmp_path / "md"
    sqlite_path = tmp_path / "extract.sqlite"
    _fake_md(md_root, subnation="aqa.org.uk", subject="mathematics", lang="en")
    _fake_md(md_root, subnation="ocr.org.uk", subject="chemistry", lang="en")

    stats = mod.run(
        subject_slug="mathematics",
        language="en",
        md_root=md_root,
        sqlite_path=sqlite_path,
    )
    assert stats["discovered"] == 2
    assert stats["extracted"] == 2
    assert stats["failed"] == 0

    with sqlite3.connect(str(sqlite_path)) as conn:
        rows = conn.execute("SELECT subnation, subject_slug FROM extracted_syllabi").fetchall()
    subnations = {r[0] for r in rows}
    assert subnations == {"aqa.org.uk", "ocr.org.uk"}


def test_run_handles_empty_md_root(tmp_path: pathlib.Path) -> None:
    md_root = tmp_path / "empty"
    md_root.mkdir()
    stats = mod.run(
        subject_slug="mathematics",
        language="en",
        md_root=md_root,
        sqlite_path=tmp_path / "extract.sqlite",
    )
    assert stats == {"discovered": 0, "extracted": 0, "failed": 0}


def test_extraction_row_dataclass_serializes() -> None:
    row = mod.ExtractionRow(
        subnation="aqa.org.uk",
        stage="leaving_cycle",
        subject_slug="mathematics",
        language="en",
        source_pdf="x.md",
        syllabus_json="{}",
    )
    as_dict = asdict(row)
    assert as_dict["subnation"] == "aqa.org.uk"
    assert as_dict["syllabus_json"] == "{}"
    assert "fetched_at" in as_dict
