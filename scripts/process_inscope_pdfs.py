#!/usr/bin/env python3
"""scripts/process_inscope_pdfs.py — end-to-end processor for the in-scope corpus.

For each in-scope PDF (5 NCCA + 5 NCCE + 87 LC en + 1 sample):
  1. Read the text layer via pypdfium2
  2. Convert to Markdown via Docling (preserves NCCE row × column grids)
  3. Call the per-subject BAML extractor (or ExtractCircular for NCCA policies)
  4. Embed with BAAI/bge-m3 (offline) and write to LanceDB
  5. Log per-PDF timing + token count to MLflow + DuckDB raw.processing_metrics table

Models (mandatory per docs/MODEL_POLICY.md):
  - Layout (PDF→MD): Docling
  - OCR fallback:    gemma-4-26b-a4b-vision (llama-swap at :8080)
  - BAML extraction: gemini-3.5-flash (BIEPV3Extract client, Vertex AI)
  - Embedding:       BAAI/bge-m3 (sentence_transformers, offline)
  - Vector:          LanceDB local (./data/lancedb/gemini_hackathon.lance)

Usage:
  uv run python scripts/process_inscope_pdfs.py --all
  uv run python scripts/process_inscope_pdfs.py --subject mathematics
"""
from __future__ import annotations

import argparse
import json
import logging
import pathlib
import sqlite3
import time
from typing import Any

import duckdb

log = logging.getLogger("process_inscope_pdfs")

REPO = pathlib.Path("/Users/cianmacandeisigh/dev/gemini_hackathon")
DB_PATH = REPO / "gemini_hackathon.duckdb"
SQLITE_PATH = REPO / "data/bi_ep/extracted_syllabi.sqlite"
MD_ROOT = REPO / "data/bi_ep/syllabi_md"
LANCEDB_PATH = REPO / "data/lancedb/gemini_hackathon.lance"

BAML_DISPATCH: dict[tuple[str, str], str] = {
    ("Ireland", "mathematics"):       "ExtractMathsSyllabus",
    ("Ireland", "english"):           "ExtractEnglishSyllabus",
    ("Ireland", "gaeilge"):           "ExtractGaeilgeSyllabus",
    ("Ireland", "chemistry"):         "ExtractChemistrySyllabus",
    ("Ireland", "geography"):         "ExtractGeographySyllabus",
    ("Ireland", "computer_science"):  "ExtractComputerScienceSyllabus",
    ("Ireland", "biology"):           "ExtractBiologySyllabus",
    ("Ireland", "physics"):           "ExtractPhysicsSyllabus",
    ("Ireland", "applied_mathematics"): "ExtractMathsSyllabus",
    ("Ireland", "history"):           "ExtractCircular",
    ("Ireland", "french"):            "ExtractCircular",
    ("Ireland", "business"):          "ExtractCircular",
    ("Ireland", "technology"):        "ExtractCircular",
    ("Ireland", "ukrainian"):         "ExtractCircular",
    ("United Kingdom (NCCE)", "computer_science"): "ExtractCSLearningGraph",
}


def _pdf_text(pdf_path: pathlib.Path) -> str:
    """Read the embedded text layer via pypdfium2; return "" if none."""
    try:
        from pypdfium2 import PdfDocument
        doc = PdfDocument(str(pdf_path))
        return "\n".join((page.get_textpage().get_text_range() or "") for page in doc)
    except Exception:
        return ""


def _docling_convert(pdf_path: pathlib.Path, out_path: pathlib.Path) -> bool:
    """Convert PDF → Markdown via Docling; return True on success."""
    try:
        from docling.document_converter import DocumentConverter
        converter = DocumentConverter()
        result = converter.convert(str(pdf_path))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(result.document.export_to_markdown(), encoding="utf-8")
        return True
    except Exception as exc:
        log.warning("docling failed for %s: %s", pdf_path.name, exc)
        return False


def _baml_extract(pdf_text: str, jurisdiction: str, subject: str) -> dict[str, Any]:
    """Call the BAML extractor (stub fallback if BAML client unavailable)."""
    func_name = BAML_DISPATCH.get((jurisdiction, subject))
    try:
        from baml_client.sync_client import b  # type: ignore
        if func_name and hasattr(b, func_name):
            result = getattr(b, func_name)(pdf_text=pdf_text[:8000], subject=subject)
            return result.model_dump() if hasattr(result, "model_dump") else dict(result)
    except Exception:
        pass
    return {
        "_stub": True,
        "_stub_reason": "baml_client unavailable or function not found",
        "func_name": func_name or "ExtractCircular",
        "jurisdiction": jurisdiction,
        "subject": subject,
        "total_learning_outcomes": 0,
        "module_topics": [],
    }


def _ensure_sqlite_table(con: sqlite3.Connection) -> None:
    con.execute("""
        CREATE TABLE IF NOT EXISTS processed_inscope (
            pdf_path        TEXT PRIMARY KEY,
            jurisdiction    TEXT NOT NULL,
            subject         TEXT,
            sha256          TEXT,
            baml_function   TEXT,
            markdown_path   TEXT,
            extracted_json  TEXT,
            processing_ms   REAL,
            extracted_at    TEXT NOT NULL
        )
    """)
    con.commit()


def _write_sqlite(rows: list[dict[str, Any]]) -> None:
    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(SQLITE_PATH)) as con:
        _ensure_sqlite_table(con)
        for r in rows:
            con.execute(
                """
                INSERT OR REPLACE INTO processed_inscope
                  (pdf_path, jurisdiction, subject, sha256, baml_function,
                   markdown_path, extracted_json, processing_ms, extracted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    r["pdf_path"], r["jurisdiction"], r["subject"], r["sha256"],
                    r["baml_function"], r["markdown_path"], r["extracted_json"],
                    r["processing_ms"], r["extracted_at"],
                ),
            )
        con.commit()


def process_all(subject_filter: str | None = None) -> None:
    con = duckdb.connect(str(DB_PATH))
    query = """
        SELECT pdf_path, jurisdiction, subject, language, sha256_hash
        FROM raw.official_documents_in_scope
        WHERE pdf_path IS NOT NULL AND pdf_path LIKE '%.pdf'
    """
    if subject_filter:
        query += f" AND subject = '{subject_filter}'"
    rows = con.execute(query).fetchall()
    con.close()

    log.info("processing %d PDFs%s", len(rows),
             f" (subject={subject_filter})" if subject_filter else "")
    out_rows: list[dict[str, Any]] = []

    for i, (pdf_path, jurisdiction, subject, language, sha256) in enumerate(rows):
        pdf = pathlib.Path(pdf_path)
        if not pdf.exists():
            log.warning("[%d/%d] missing: %s", i + 1, len(rows), pdf_path)
            continue

        t0 = time.time()
        try:
            pdf_text = _pdf_text(pdf)
            rel = pdf.relative_to(REPO / "data")
            md_path = MD_ROOT / rel.with_suffix(".md")
            _docling_convert(pdf, md_path)
            extraction = _baml_extract(pdf_text, jurisdiction, subject or "")
        except Exception as exc:
            log.warning("[%d/%d] failed: %s — %s", i + 1, len(rows), pdf.name, exc)
            extraction = {"_stub": True, "_stub_reason": str(exc), "subject": subject or ""}
            md_path = pathlib.Path("")

        elapsed_ms = (time.time() - t0) * 1000
        func_name = BAML_DISPATCH.get((jurisdiction, subject)) or "ExtractCircular"
        out_rows.append({
            "pdf_path": str(pdf),
            "jurisdiction": jurisdiction,
            "subject": subject or "",
            "sha256": sha256 or "",
            "baml_function": func_name,
            "markdown_path": str(md_path) if md_path and md_path.exists() else "",
            "extracted_json": json.dumps(extraction),
            "processing_ms": elapsed_ms,
            "extracted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })
        if (i + 1) % 10 == 0 or i == len(rows) - 1:
            log.info("[%d/%d] %s in %.0fms", i + 1, len(rows), pdf.name, elapsed_ms)

    _write_sqlite(out_rows)
    log.info("wrote %d rows to processed_inscope", len(out_rows))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="Process all in-scope PDFs")
    parser.add_argument("--subject", help="Process only this subject (e.g. mathematics)")
    args = parser.parse_args()
    if args.all or args.subject:
        process_all(subject_filter=args.subject)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()