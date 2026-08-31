"""gemini_hackathon.syllabus.storage — DuckDB + JSONL persistence for the comparison results."""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


# The canonical path for the syllabus comparison JSONL output.
SYLLABUS_RESULTS_PATH: Path = Path("./data/gemini_hackathon/syllabus/comparison_results.jsonl")


def write_extraction_to_jsonl(results: list[dict], path: Path | None = None) -> int:
    """Write the extraction results to a JSONL file.

    Returns the number of rows written.
    """
    target = path or SYLLABUS_RESULTS_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as fp:
        for r in results:
            fp.write(json.dumps(r, ensure_ascii=False) + "\n")
    logger.info("write_extraction_to_jsonl: %d rows → %s", len(results), target)
    return len(results)


def write_extraction_to_duckdb(results: list[dict], database_path: str | None = None) -> int:
    """Write the extraction results to the canonical DuckDB (Phase 1.9 named destination).

    Returns the number of rows written. Returns -1 if duckdb is not installed.
    """
    try:
        import duckdb  # type: ignore
    except ImportError:
        logger.warning("write_extraction_to_duckdb: duckdb not installed")
        return -1

    db_path = database_path or "./data/gemini_hackathon.duckdb"
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(database=db_path, read_only=False)

    # Create the table schema (idempotent)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS gemini_hackathon.syllabus_comparisons (
            subject              VARCHAR,
            extraction_method    VARCHAR,
            jaccard_vs_baml      DOUBLE,
            lo_coverage          DOUBLE,
            pydantic_conformance DOUBLE,
            judge_score          INTEGER,
            judge_rationale      VARCHAR,
            cost_usd             DOUBLE,
            latency_ms           INTEGER,
            found_topics         INTEGER,
            golden_topics        INTEGER,
            captured_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    rows_written = 0
    for r in results:
        conn.execute(
            "INSERT INTO gemini_hackathon.syllabus_comparisons (subject, extraction_method, jaccard_vs_baml, lo_coverage, pydantic_conformance, judge_score, judge_rationale, cost_usd, latency_ms, found_topics, golden_topics) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                r.get("subject"),
                r.get("extraction_method"),
                r.get("jaccard_vs_baml"),
                r.get("lo_coverage"),
                r.get("pydantic_conformance"),
                r.get("judge_score"),
                r.get("judge_rationale"),
                r.get("cost_usd"),
                r.get("latency_ms"),
                r.get("found_topics"),
                r.get("golden_topics"),
            ],
        )
        rows_written += 1

    conn.close()
    logger.info("write_extraction_to_duckdb: %d rows → %s", rows_written, db_path)
    return rows_written


__all__ = [
    "SYLLABUS_RESULTS_PATH",
    "write_extraction_to_duckdb",
    "write_extraction_to_jsonl",
]
