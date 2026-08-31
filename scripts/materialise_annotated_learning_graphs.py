#!/usr/bin/env python3
"""Materialise the 6 annotated learning graphs to disk + SQLite mirror.

Per Phase 5 of the gemini_hackathon polish plan (the
[2026-08-31-ncce-showcase-complete-v1](../../openspec/changes/2026-08-31-ncce-showcase-complete-v1/proposal.md)
change).

Reads the per-subject learning graphs from ``data/bi_ep/learning_graphs/``,
loads the 12 cached pedagogy principles from
``data/bi_ep/syllabi_md/uk_ncce/pedagogy_principles.json``, applies the
overlay (via the canonical `pedagogy_overlay` Dagster asset helpers),
and writes the resulting ``AnnotatedLearningGraph`` to:

  1. JSON file at ``data/bi_ep/annotated_learning_graphs/<subject>.json``
  2. SQLite row in ``annotated_learning_graphs`` table at
     ``data/bi_ep/extracted_syllabi.sqlite``

Idempotent — safe to re-run; re-runs that find the disk JSON files
unchanged are no-ops (the SQLite UPSERT refreshes the
``generated_at`` timestamp).

Usage::

    uv run python scripts/materialise_annotated_learning_graphs.py
    # or:
    BAML_TEST_MODE=true uv run python scripts/materialise_annotated_learning_graphs.py
"""

from __future__ import annotations

import datetime as _dt
import importlib.util as _iu
import json
import logging
import pathlib
import sqlite3
import sys
from typing import Any

REPO_ROOT: pathlib.Path = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "orchestration" / "defs"))

logger = logging.getLogger(__name__)

PRIORITY_SUBJECTS: tuple[str, ...] = (
    "computer_science",
    "mathematics",
    "english",
    "gaeilge",
    "chemistry",
    "geography",
)

LEARNING_GRAPHS_ROOT: pathlib.Path = REPO_ROOT / "data" / "bi_ep" / "learning_graphs"
ANNOTATED_GRAPHS_ROOT: pathlib.Path = REPO_ROOT / "data" / "bi_ep" / "annotated_learning_graphs"
SQLITE_PATH: pathlib.Path = REPO_ROOT / "data" / "bi_ep" / "extracted_syllabi.sqlite"


def _load_pedagogy_overlay() -> Any:
    """Lazy-import the pedagogy_overlay module via importlib (no full Dagster)."""
    spec = _iu.spec_from_file_location(
        "pedagogy_overlay",
        REPO_ROOT / "orchestration" / "defs" / "3_model_lifecycle" / "pedagogy_overlay.py",
    )
    if spec is None or spec.loader is None:
        raise ImportError("pedagogy_overlay module spec not found")
    mod = _iu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _stub_graph(subject: str) -> dict[str, Any]:
    """Build a stub source graph when no Change A materialisation exists."""
    rows = [
        {"id": "row_algos", "label": "Algorithms"},
        {"id": "row_select", "label": "Selection"},
        {"id": "row_iter", "label": "Iteration"},
        {"id": "row_vars", "label": "Variables"},
    ]
    cols = [{"id": f"col_lesson_{i + 1}", "label": f"Lesson {i + 1}"} for i in range(7)]
    cells = [
        {
            "id": f"cell_{rows[ri]['id']}_{cols[ci]['id']}",
            "row_id": rows[ri]["id"],
            "column_id": cols[ci]["id"],
            "skill_description": f"Skill {ri}-{ci}: introduce concept",
            "confidence": 0.95,
        }
        for ri in range(len(rows))
        for ci in range(len(cols))
    ]
    return {
        "id": f"uk_ncce_{subject}_y8",
        "jurisdiction": "United Kingdom (NCCE)",
        "jurisdiction_slug": "uk_ncce",
        "subject": subject,
        "year_level": 8,
        "rows": rows,
        "columns": cols,
        "cells": cells,
        "prerequisite_edges": [],
        "pedagogy_principle_ids": [],
        "skill_ribbons": [],
        "source_pdf": str(
            REPO_ROOT
            / "data"
            / "bi_ep"
            / "syllabi_raw"
            / "uk_ncce"
            / "curriculum"
            / "learning_graph_intro_to_python_programming_y8.pdf"
        ),
        "source_pages": [1],
        "generated_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),  # noqa: UP017
    }


def _load_per_subject_graph(subject: str) -> dict[str, Any]:
    """Read the per-subject extracted graph JSON (or fall back to a stub).

    The Change A `uk_ncce_learning_graphs` module uses short slugs
    (`cs`, `maths`) in its filename convention, so we check both the
    full subject slug and the short slug.
    """
    short = {
        "computer_science": "cs",
        "mathematics": "maths",
    }.get(subject, subject)
    candidates = [
        LEARNING_GRAPHS_ROOT / f"uk_ncce_{short}_extracted_graph.json",
        LEARNING_GRAPHS_ROOT / f"uk_ncce_{short}_y8.json",
        LEARNING_GRAPHS_ROOT / f"uk_ncce_{subject}_extracted_graph.json",
        LEARNING_GRAPHS_ROOT / f"uk_ncce_{subject}_y8.json",
    ]
    for p in candidates:
        if p.is_file():
            try:
                payload = json.loads(p.read_text(encoding="utf-8"))
                if payload.get("cells"):
                    return payload
                logger.info(
                    "materialise: stub_payload subject=%s path=%s (no cells — using rich stub)",
                    subject,
                    p,
                )
                return _stub_graph(subject)
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning("materialise: parse_failed path=%s reason=%s", p, exc)
    logger.info(
        "materialise: stub_graph subject=%s — no Change A JSON found at %s",
        subject,
        candidates,
    )
    return _stub_graph(subject)


def main() -> int:
    """Materialise the 6 annotated learning graphs."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    mod = _load_pedagogy_overlay()
    ANNOTATED_GRAPHS_ROOT.mkdir(parents=True, exist_ok=True)
    mod._ensure_overlay_table(SQLITE_PATH)
    principles = mod._load_principles_from_cache()
    logger.info("principles_loaded=%d", len(principles))

    n_annotated = 0
    for subject in PRIORITY_SUBJECTS:
        source_graph = _load_per_subject_graph(subject)
        annotated = mod._call_apply_pedagogy_principles(graph=source_graph, principles=principles)
        mod._persist(
            annotated_graph=annotated,
            subject=subject,
            source_jurisdiction="United Kingdom (NCCE)",
            sqlite_path=SQLITE_PATH,
        )
        ann_path = ANNOTATED_GRAPHS_ROOT / f"{subject}.json"
        ann_path.write_text(json.dumps(annotated, indent=2, sort_keys=True), encoding="utf-8")
        n_cells = len(annotated.get("cell_annotations", {}))
        logger.info(
            "annotated_materialised subject=%s path=%s n_cells=%d bytes=%d",
            subject,
            ann_path,
            n_cells,
            ann_path.stat().st_size,
        )
        n_annotated += 1

    with sqlite3.connect(str(SQLITE_PATH)) as conn:
        rows = list(
            conn.execute("SELECT graph_id, subject, pedagogy_source FROM annotated_learning_graphs")
        )
    logger.info("sqlite_mirror_rows=%d", len(rows))
    for r in rows:
        logger.info("  - %s (%s) source=%s", r[0], r[1], r[2])
    return 0 if n_annotated == len(PRIORITY_SUBJECTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ANNOTATED_GRAPHS_ROOT",
    "LEARNING_GRAPHS_ROOT",
    "PRIORITY_SUBJECTS",
    "SQLITE_PATH",
    "_load_per_subject_graph",
    "_stub_graph",
    "main",
]
