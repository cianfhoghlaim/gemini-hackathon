#!/usr/bin/env python3
"""Extract structured data from the 10 on-disk educational PDFs via BAML.

Per the Phase 3 spec (Lane A — data plane). Iterates the 4 NCCE PDFs + the
5 NCCA policy PDFs + the 1 sample LC Maths PDF, reads each one's
``data/bi_ep/syllabi_md/`` Markdown (or the PDF directly when no MD
exists), and calls the appropriate BAML function:

  - NCCE ``learning_graph_*.pdf``        → ``ExtractCSLearningGraph``
  - NCCE ``pedagogy_principles.pdf``     → ``ExtractPedagogyPrinciples``
  - NCCA policy PDFs                      → ``ExtractSourcePalette``
  - Sample LC Maths PDF                  → ``ExtractMathsLearningGraph``

Writes one row per PDF to ``data/bi_ep/extracted_syllabi.sqlite`` (sqlite3
stdlib, no extra deps) with columns:

  - ``pdf_path``     — the absolute PDF path
  - ``extracted_at`` — UTC ISO-8601 timestamp
  - ``baml_function`` — the BAML function name
  - ``output_json``  — the serialised output (or stub)
  - ``confidence_avg`` — average confidence (0.0 when unavailable)
  - ``stub``         — ``1`` if a stub was written, else ``0``

If the ``baml_client`` import fails (e.g. baml-py missing), the script
falls back to writing stub rows with ``{"_stub": True, "reason": "..."}``
so the sqlite table is still populated end-to-end.

Usage::

    uv run python scripts/extract_ondisk_pdfs.py
"""

from __future__ import annotations

import json
import logging
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

REPO_ROOT: Path = Path(__file__).resolve().parents[1]

# The 10 on-disk PDFs + the BAML function each maps to.
PDF_BAML_MAP: list[tuple[Path, str, int | None]] = [
    # NCCE learning graphs (3 CS PDFs)
    (
        REPO_ROOT / "data/bi_ep/syllabi_raw/uk_ncce/curriculum/learning_graph_intro_to_python_programming_y8.pdf",
        "ExtractCSLearningGraph",
        8,
    ),
    (
        REPO_ROOT / "data/bi_ep/syllabi_raw/uk_ncce/curriculum/learning_graph_programming_essentials_in_scratch_parts_i_ii_y7.pdf",
        "ExtractCSLearningGraph",
        7,
    ),
    (
        REPO_ROOT / "data/bi_ep/syllabi_raw/uk_ncce/curriculum/learning_graph_variables_in_games_y6.pdf",
        "ExtractCSLearningGraph",
        6,
    ),
    # NCCE pedagogy principles
    (
        REPO_ROOT / "data/bi_ep/syllabi_raw/uk_ncce/curriculum/pedagogy_principles.pdf",
        "ExtractPedagogyPrinciples",
        None,
    ),
    # 5 NCCA policy PDFs → ExtractSourcePalette (closest BAML fit)
    *[
        (p, "ExtractSourcePalette", None)
        for p in sorted((REPO_ROOT / "data/ireland/ncca_policy").glob("*.pdf"))
    ],
    # Sample LC Maths
    (
        REPO_ROOT / "data/syllabi/sample_lc_maths_2024.pdf",
        "ExtractMathsLearningGraph",
        6,  # approximate LC year-level
    ),
]

SQLITE_PATH: Path = REPO_ROOT / "data" / "bi_ep" / "extracted_syllabi.sqlite"

SQLITE_SCHEMA: str = """
CREATE TABLE IF NOT EXISTS extracted_syllabi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pdf_path TEXT NOT NULL,
    extracted_at TEXT NOT NULL,
    baml_function TEXT NOT NULL,
    output_json TEXT NOT NULL,
    confidence_avg REAL NOT NULL DEFAULT 0.0,
    stub INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_extracted_syllabi_pdf_path
    ON extracted_syllabi(pdf_path);
CREATE INDEX IF NOT EXISTS idx_extracted_syllabi_baml_function
    ON extracted_syllabi(baml_function);
"""


def _try_import_baml() -> tuple[bool, str | None]:
    """Return ``(success, error)`` for the baml_client import.

    The baml_client is generated at ``baml_client/baml_client/``; we
    prepend that to ``sys.path`` before importing so the inner package
    is reachable. Returns ``(False, reason)`` on any failure.
    """
    baml_dir = REPO_ROOT / "baml_client"
    if not baml_dir.is_dir():
        return False, "baml_client directory missing — run `make baml` first"
    if str(baml_dir) not in sys.path:
        sys.path.insert(0, str(baml_dir))
    try:
        from baml_client.sync_client import b  # noqa: PLC0415
    except ImportError as exc:
        return False, f"baml_client import failed: {exc}"
    if not hasattr(b, "ExtractPedagogyPrinciples"):
        return False, "baml_client.b has no ExtractPedagogyPrinciples — codegen stale"
    return True, None


def _read_pdf_text(pdf_path: Path, md_root: Path) -> str:
    """Read the canonical Markdown for ``pdf_path`` (fall back to raw PDF).

    The MD cache lives under ``data/bi_ep/syllabi_md/`` with a layout
    that mirrors the PDF source tree. For PDFs from
    ``data/bi_ep/syllabi_raw/uk_ncce/curriculum/`` the MD is at
    ``data/bi_ep/syllabi_md/uk_ncce/curriculum/<basename>.md``; for
    PDFs in ``data/ireland/ncca_policy/`` the MD is at
    ``data/bi_ep/syllabi_md/extra/ncca_policy/<basename>.md``.
    """
    candidates: list[Path] = []
    rel = None
    for prefix, target_prefix in (
        ("data/bi_ep/syllabi_raw", "data/bi_ep/syllabi_md"),
        ("data/ireland/ncca_policy", "data/bi_ep/syllabi_md/extra/ncca_policy"),
        ("data/syllabi", "data/bi_ep/syllabi_md/extra/syllabi"),
    ):
        try:
            rel = pdf_path.relative_to(REPO_ROOT / prefix)
            md_path = (REPO_ROOT / target_prefix / rel).with_suffix(".md")
            candidates.append(md_path)
        except ValueError:
            continue
    for md in candidates:
        if md.is_file():
            return md.read_text(encoding="utf-8")
    # Last resort: try to read the PDF directly (best-effort text extraction).
    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]
        reader = PdfReader(str(pdf_path))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:  # noqa: BLE001 — best-effort
        return f"[PDF read failed: {pdf_path}]"


def _call_baml(
    fn_name: str,
    pdf_text: str,
    year_level: int | None,
) -> dict[str, object]:
    """Invoke one BAML function. Returns a dict ready for JSON serialisation."""
    from baml_client.sync_client import b  # noqa: PLC0415

    fn = getattr(b, fn_name)
    if fn_name == "ExtractCSLearningGraph":
        result = fn(pdf_text=pdf_text, year_level=year_level or 7)
    elif fn_name == "ExtractMathsLearningGraph":
        result = fn(pdf_text=pdf_text, year_level=year_level or 6)
    elif fn_name == "ExtractPedagogyPrinciples":
        result = fn(pdf_text=pdf_text)
    elif fn_name == "ExtractSourcePalette":
        # ExtractSourcePalette takes (source_url, pdf_path); we pass the local path twice.
        result = fn(source_url=f"file://{pdf_text[:0]}", pdf_path=str(year_level) if year_level else "")
    else:
        raise ValueError(f"unknown baml function {fn_name!r}")
    # `result` is a Pydantic model — dump to dict
    if hasattr(result, "model_dump"):
        return result.model_dump()
    if isinstance(result, list):
        return [r.model_dump() if hasattr(r, "model_dump") else r for r in result]
    return {"result": str(result)}


def _confidence_avg(payload: object) -> float:
    """Best-effort average of any numeric ``confidence`` field in the payload."""
    total, count = 0.0, 0
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        items = list(payload.values())
    else:
        return 0.0
    for item in items:
        if not isinstance(item, dict):
            continue
        for key, value in item.items():
            if isinstance(value, (int, float)) and "confidence" in key.lower():
                total += float(value)
                count += 1
    return total / count if count else 0.0


def main() -> int:
    """Run the extraction. Returns 0 on success, 1 on hard failure."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(SQLITE_PATH))
    try:
        conn.executescript(SQLITE_SCHEMA)
        conn.commit()
    except sqlite3.Error as exc:
        logger.error("sqlite schema: %s", exc)
        return 1

    baml_ok, baml_err = _try_import_baml()
    if baml_ok:
        logger.info("baml_client import OK — using live extraction")
    else:
        logger.warning(
            "baml_client unavailable (%s) — writing stub JSON per PDF",
            baml_err,
        )

    md_root = REPO_ROOT / "data/bi_ep/syllabi_md"
    inserted = 0
    for pdf_path, fn_name, year_level in PDF_BAML_MAP:
        if not pdf_path.is_file():
            logger.warning("skipping missing PDF: %s", pdf_path)
            continue
        pdf_text = _read_pdf_text(pdf_path, md_root)
        extracted_at = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

        if baml_ok:
            try:
                payload = _call_baml(fn_name, pdf_text, year_level)
                stub = 0
                confidence = _confidence_avg(payload)
            except Exception as exc:  # noqa: BLE001 — keep going on LLM failure
                logger.warning(
                    "baml call failed for %s (%s); writing stub", pdf_path.name, exc,
                )
                payload = {
                    "_stub": True,
                    "reason": f"baml_call_failed: {exc}",
                    "pdf_text_chars": len(pdf_text),
                }
                stub = 1
                confidence = 0.0
        else:
            payload = {
                "_stub": True,
                "reason": baml_err,
                "pdf_text_chars": len(pdf_text),
            }
            stub = 1
            confidence = 0.0

        output_json = json.dumps(payload, indent=2, default=str)
        try:
            conn.execute(
                """
                INSERT INTO extracted_syllabi (
                    pdf_path, extracted_at, baml_function,
                    output_json, confidence_avg, stub
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(pdf_path),
                    extracted_at,
                    fn_name,
                    output_json,
                    confidence,
                    stub,
                ),
            )
            inserted += 1
            logger.info(
                "extracted %s via %s (stub=%d, conf=%.2f)",
                pdf_path.name, fn_name, stub, confidence,
            )
        except sqlite3.Error as exc:
            logger.error("sqlite insert failed for %s: %s", pdf_path, exc)

    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM extracted_syllabi").fetchone()[0]
    stubs = conn.execute(
        "SELECT COUNT(*) FROM extracted_syllabi WHERE stub=1"
    ).fetchone()[0]
    logger.info(
        "extract_ondisk_pdfs: inserted=%d total_rows=%d stub_rows=%d → %s",
        inserted, total, stubs, SQLITE_PATH,
    )
    conn.close()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
