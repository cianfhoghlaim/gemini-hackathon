"""cocoindex_flows.education.lc6_extraction_app — Phase 3 BAML extraction App.

Phase 3a of the multi-stage plan (see AGENTS.md). CocoIndex App that
reads every Markdown file under ``data/bi_ep/syllabi_md/`` and runs
all 5 LC6 BAML extraction functions (``ExtractCurriculumSyllabus``,
``ExtractExamPaperLayout``, ``ExtractMarkingSchemeGuideline``,
``ExtractCrossLinguisticConcept``, ``ExtractSyllabusDiagram``)
concurrently via ``asyncio.gather``.

The output rows land in the ``bi_ep.extracted_syllabi`` Postgres table
(via the shared ``VECTOR_TARGET`` abstraction; in dev with no DB
configured, rows are written to a local SQLite file at
``data/bi_ep/extracted_syllabi.sqlite``).

The App is per-(subject, language). The factory ``build_extraction_app(subject_slug, language)``
returns a configured ``coco.App`` (or a plain function ``run()`` when
cocoindex is missing — the canonical dev path).

Run (single subject, English)::

    python -m cocoindex_flows.education.lc6_extraction_app --subject mathematics --language en

Or programmatically via ``run(subject_slug="...", language="...")``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import pathlib
import sqlite3
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

#: Default Markdown root (matches the pdf_to_markdown_app output).
MD_ROOT: pathlib.Path = pathlib.Path(
    __import__("os").environ.get(
        "BI_EP_PDF_MD_ROOT",
        pathlib.Path.cwd() / "data" / "bi_ep" / "syllabi_md",
    )
)

#: Where the dev (SQLite) extracted_syllabi table lives.
SQLITE_PATH: pathlib.Path = pathlib.Path(
    __import__("os").environ.get(
        "BI_EP_EXTRACTED_SYLLABI_PATH",
        pathlib.Path.cwd() / "data" / "bi_ep" / "extracted_syllabi.sqlite",
    )
)


# ---------------------------------------------------------------------------
# BAML client wrapper — graceful degradation when baml_client is missing
# ---------------------------------------------------------------------------


@dataclass
class ExtractionRow:
    """One row per Markdown file. Maps to the bi_ep.extracted_syllabi schema."""

    subnation: str
    stage: str
    subject_slug: str
    language: str
    source_pdf: str
    syllabus_json: str | None = None
    exam_paper_json: str | None = None
    marking_json: str | None = None
    concepts_json: str | None = None
    diagrams_json: str | None = None
    fetched_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


def _extract_subnation_stage_subject_language(
    md_path: pathlib.Path, *, md_root: pathlib.Path
) -> tuple[str, str, str, str]:
    """Derive (subnation, stage, subject_slug, language) from the path layout.

    Layout: ``<md_root>/<source_key>/<subject_slug>/<lang>/<sha>.md``
    The "stage" is implicit (leaving_cycle for all 5 LC6 functions); the
    downstream BAML function uses ``stage`` as a context field.
    """
    relative = md_path.relative_to(md_root)
    parts = relative.parts  # (source_key, subject_slug, lang, sha.md)
    subnation = parts[0]
    subject_slug = parts[1] if len(parts) > 1 else "unknown"
    language = parts[2] if len(parts) > 2 else "en"
    # For Phase 3a we treat all subjects as LC (leaving_cycle). Phase 3b
    # would split per stage.
    return subnation, "leaving_cycle", subject_slug, language


def _baml_extract_all(md_text: str, *, subject_slug: str, language: str) -> dict[str, str | None]:
    """Call all 5 LC6 BAML functions and return the JSON-encoded results.

    Returns a dict with keys: syllabus, exam_paper, marking, concepts,
    diagrams. Each value is a JSON string (or None on failure).

    Falls back to a deterministic stub when ``baml_client`` is not
    importable (the canonical dev path — the same stub shape BAML
    returns in offline mode).
    """
    try:
        from baml_client import b  # type: ignore[import-not-found]
        from baml_client.types import (  # type: ignore[import-not-found]
            LCCrossLinguisticConcept,
            LCExamPaper,
            LCMarkingScheme,
            LCSyllabusDiagram,
            LCSyllabusDocument,
        )
    except ImportError:
        return _baml_extract_stub(md_text, subject_slug=subject_slug, language=language)

    async def _run_all() -> dict[str, Any]:
        return await asyncio.gather(
            b.ExtractCurriculumSyllabus(pdf_text=md_text, subject=subject_slug, language=language),
            b.ExtractExamPaperLayout(pdf_text=md_text, subject=subject_slug, language=language),
            b.ExtractMarkingSchemeGuideline(
                pdf_text=md_text, subject=subject_slug, language=language
            ),
            b.ExtractCrossLinguisticConcept(pdf_text_en=md_text, subject=subject_slug),
            b.ExtractSyllabusDiagram(pdf_text=md_text, subject=subject_slug),
            return_exceptions=True,
        )

    results = asyncio.run(_run_all())

    def _safe_json(value: Any) -> str | None:
        if isinstance(value, BaseException):
            logger.warning("lc6_extraction.baml_call_failed reason=%s", value)
            return None
        try:
            if hasattr(value, "model_dump_json"):
                return value.model_dump_json()
            return json.dumps(value, default=str)
        except Exception as exc:
            logger.warning("lc6_extraction.serialize_failed reason=%s", exc)
            return None

    keys = ("syllabus", "exam_paper", "marking", "concepts", "diagrams")
    return dict(zip(keys, (_safe_json(r) for r in results), strict=False))


def _baml_extract_stub(md_text: str, *, subject_slug: str, language: str) -> dict[str, str | None]:
    """Deterministic stub used when baml_client is not importable.

    The shape mirrors what BAML emits (5 named dicts) so downstream
    consumers don't have to special-case the dev path.
    """
    page_count = md_text.count("## Page")
    char_count = len(md_text)
    common_meta = {
        "subject_slug": subject_slug,
        "language": language,
        "source_chars": char_count,
        "source_pages": page_count,
    }
    return {
        "syllabus": json.dumps(
            {
                **common_meta,
                "stub": True,
                "module_topics": [],
                "cross_curricular": [],
                "assessment_objectives": [],
            }
        ),
        "exam_paper": json.dumps(
            {**common_meta, "stub": True, "sections": [], "total_marks": None}
        ),
        "marking": json.dumps({**common_meta, "stub": True, "criteria": []}),
        "concepts": json.dumps({**common_meta, "stub": True, "concepts": []}),
        "diagrams": json.dumps({**common_meta, "stub": True, "diagrams": []}),
    }


# ---------------------------------------------------------------------------
# Dev storage (SQLite when no Postgres available)
# ---------------------------------------------------------------------------

#: The columns `_upsert_sqlite_row` writes. A pre-existing `extracted_syllabi`
#: table missing any of these makes `CREATE TABLE IF NOT EXISTS` a silent
#: no-op and every subsequent insert fail one-by-one, which reads as
#: "extracted: 0, failed: N" with no obvious cause.
_REQUIRED_COLUMNS: frozenset[str] = frozenset(
    {
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
)


def _ensure_sqlite_table(path: pathlib.Path) -> None:
    """Create the dev extracted_syllabi table if it doesn't exist.

    Raises:
        RuntimeError: If an ``extracted_syllabi`` table already exists with an
            incompatible schema (e.g. written by a different producer). Left
            unchecked this degrades into a silent all-rows-failed run.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(path)) as conn:
        existing = {row[1] for row in conn.execute("PRAGMA table_info(extracted_syllabi)")}
        if existing and not _REQUIRED_COLUMNS.issubset(existing):
            missing = ", ".join(sorted(_REQUIRED_COLUMNS - existing))
            raise RuntimeError(
                f"{path}: table 'extracted_syllabi' exists but is missing "
                f"column(s): {missing}. It was most likely written by a "
                f"different producer. Rename it out of the way "
                f"(ALTER TABLE extracted_syllabi RENAME TO "
                f"extracted_syllabi_legacy) and re-run."
            )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS extracted_syllabi (
                subnation TEXT,
                stage TEXT,
                subject_slug TEXT,
                language TEXT,
                source_pdf TEXT,
                syllabus_json TEXT,
                exam_paper_json TEXT,
                marking_json TEXT,
                concepts_json TEXT,
                diagrams_json TEXT,
                fetched_at TEXT,
                PRIMARY KEY (subnation, stage, subject_slug, language, source_pdf)
            )
            """
        )
        conn.commit()


def _upsert_sqlite_row(path: pathlib.Path, row: ExtractionRow) -> None:
    """Upsert one row into the dev SQLite extracted_syllabi table."""
    with sqlite3.connect(str(path)) as conn:
        conn.execute(
            """
            INSERT INTO extracted_syllabi
                (subnation, stage, subject_slug, language, source_pdf,
                 syllabus_json, exam_paper_json, marking_json, concepts_json,
                 diagrams_json, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (subnation, stage, subject_slug, language, source_pdf)
            DO UPDATE SET
                syllabus_json = excluded.syllabus_json,
                exam_paper_json = excluded.exam_paper_json,
                marking_json = excluded.marking_json,
                concepts_json = excluded.concepts_json,
                diagrams_json = excluded.diagrams_json,
                fetched_at = excluded.fetched_at
            """,
            (
                row.subnation,
                row.stage,
                row.subject_slug,
                row.language,
                row.source_pdf,
                row.syllabus_json,
                row.exam_paper_json,
                row.marking_json,
                row.concepts_json,
                row.diagrams_json,
                row.fetched_at,
            ),
        )
        conn.commit()


# ---------------------------------------------------------------------------
# The run() function — the canonical dev path (no CocoIndex dependency)
# ---------------------------------------------------------------------------


def _process_one(
    md_path: pathlib.Path,
    *,
    md_root: pathlib.Path,
    sqlite_path: pathlib.Path,
    subject_slug: str,
    language: str,
) -> ExtractionRow:
    """Read one .md, run the 5 BAML functions, upsert one row."""
    _ensure_sqlite_table(sqlite_path)
    text = md_path.read_text(encoding="utf-8")
    subnation, stage, derived_subject, derived_lang = _extract_subnation_stage_subject_language(
        md_path, md_root=md_root
    )
    # Caller's subject_slug/language may differ from the path-derived ones;
    # honour the caller's args (per-app invocation pins subject + language).
    results = _baml_extract_all(text, subject_slug=subject_slug, language=language)
    row = ExtractionRow(
        subnation=subnation,
        stage=stage,
        subject_slug=derived_subject,
        language=derived_lang,
        source_pdf=str(md_path.relative_to(md_root)),
        syllabus_json=results.get("syllabus"),
        exam_paper_json=results.get("exam_paper"),
        marking_json=results.get("marking"),
        concepts_json=results.get("concepts"),
        diagrams_json=results.get("diagrams"),
    )
    _upsert_sqlite_row(sqlite_path, row)
    return row


def run(
    *,
    subject_slug: str,
    language: str,
    md_root: pathlib.Path | None = None,
    sqlite_path: pathlib.Path | None = None,
) -> dict[str, int]:
    """Run all 5 LC6 BAML functions on every .md under md_root.

    Returns {discovered, extracted, failed} stats.
    """
    md = md_root or MD_ROOT
    sqlite = sqlite_path or SQLITE_PATH
    _ensure_sqlite_table(sqlite)

    if not md.exists():
        logger.warning(
            "lc6_extraction_app.md_root_missing path=%s "
            "— run `python -m cocoindex_flows.pdf.pdf_to_markdown_app` first",
            md,
        )
        return {"discovered": 0, "extracted": 0, "failed": 0}

    mds = sorted(md.rglob("*.md"))
    stats = {"discovered": len(mds), "extracted": 0, "failed": 0}
    for md_path in mds:
        try:
            _process_one(
                md_path,
                md_root=md,
                sqlite_path=sqlite,
                subject_slug=subject_slug,
                language=language,
            )
            stats["extracted"] += 1
        except Exception as exc:
            logger.warning(
                "lc6_extraction_app.process_failed path=%s reason=%s",
                md_path,
                exc,
            )
            stats["failed"] += 1
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the LC6 BAML extraction over all .md files.")
    # Phase 1: `--subject` is now optional for the `make cocoindex-update`
    # bulk-run target. The default "*" matches every subject; the per-row
    # `subject_slug` is still derived from the path layout by the App.
    parser.add_argument(
        "--subject",
        default="*",
        help="subject slug (e.g. mathematics); default '*' matches all",
    )
    parser.add_argument("--language", default="en", choices=["en", "ga"])
    parser.add_argument("--md-root", type=pathlib.Path, default=None)
    parser.add_argument("--sqlite", type=pathlib.Path, default=None)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    started = time.monotonic()
    stats = run(
        subject_slug=args.subject,
        language=args.language,
        md_root=args.md_root,
        sqlite_path=args.sqlite,
    )
    elapsed_ms = int((time.monotonic() - started) * 1000)
    logger.info("lc6_extraction_app.summary stats=%s elapsed_ms=%d", stats, elapsed_ms)
    return 0 if stats["failed"] == 0 else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())


__all__ = [
    "MD_ROOT",
    "SQLITE_PATH",
    "ExtractionRow",
    "main",
    "run",
]
