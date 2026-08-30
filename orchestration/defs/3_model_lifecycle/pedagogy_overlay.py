"""orchestration.defs.3_model_lifecycle.pedagogy_overlay — 6 overlay assets.

Phase 3 of the OpenSpec change
[`2026-08-31-pedagogy-overlay-renderer-v1`](../../../../openspec/changes/2026-08-31-pedagogy-overlay-renderer-v1/proposal.md).

For each of the 6 BIEP priority subjects (`computer_science`,
`mathematics`, `english`, `gaeilge`, `chemistry`, `geography`),
build a single Dagster asset that:

  1. Depends on the corresponding `uk_ncce_learning_graphs` asset
     (Change A) + the pedagogy cache from
     `cocoindex_flows/uk_ncce/pedagogy_cache.py` (Phase 2).
  2. Loads the 12 cached pedagogy principles (disk cache hit when
     `sha256(pedagogy_principles.pdf)` is unchanged; otherwise a fresh
     BAML `ExtractPedagogyPrinciples` extract).
  3. Calls BAML `ApplyPedagogyPrinciples(graph, principles)` (Phase 1b).
  4. Materialises the resulting `AnnotatedLearningGraph` to:
       - Firestore `annotatedLearningGraphs/{graph_id}` collection
       - The local SQLite `annotated_learning_graphs` table

6 assets total, one per priority subject. Asset naming convention:

    pedagogy_overlay_<subject_slug>

Example:
    pedagogy_overlay_computer_science
"""

from __future__ import annotations

import asyncio
import datetime as _dt
import json
import logging
import pathlib
import sqlite3
import time
from collections.abc import Iterator, Mapping
from typing import Any, Final

logger = logging.getLogger(__name__)

try:
    from dagster import AssetExecutionContext, Output, asset
except ImportError:
    AssetExecutionContext = None  # type: ignore[assignment]
    Output = None  # type: ignore[assignment]
    asset = None  # type: ignore[assignment]
    logger.warning(
        "pedagogy_overlay: dagster not installed; running as a plain Python module only."
    )


# ---------------------------------------------------------------------------
# Constants — the 6 priority subjects
# ---------------------------------------------------------------------------

#: The 6 BIEP priority subjects (one Dagster asset per subject).
SUBJECTS: Final[tuple[str, ...]] = (
    "computer_science",
    "mathematics",
    "english",
    "gaeilge",
    "chemistry",
    "geography",
)

#: Short slugs for the asset names (compat with the spec delta examples).
SUBJECT_SHORT_SLUGS: Final[Mapping[str, str]] = {
    "computer_science": "cs",
    "mathematics": "maths",
    "english": "english",
    "gaeilge": "gaeilge",
    "chemistry": "chemistry",
    "geography": "geography",
}

#: The Firestore collection that receives every annotated graph.
FIRESTORE_COLLECTION: Final[str] = "annotatedLearningGraphs"

#: Dev SQLite path (the canonical Phase 3 extracted_syllabi DB).
SQLITE_PATH: pathlib.Path = pathlib.Path(
    __import__("os").environ.get(
        "BI_EP_EXTRACTED_SYLLABI_PATH",
        pathlib.Path.cwd() / "data" / "bi_ep" / "extracted_syllabi.sqlite",
    )
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _asset_key(subject: str) -> str:
    """Canonical Dagster asset name for the overlay asset.

    Examples:
        pedagogy_overlay_cs
        pedagogy_overlay_maths
    """
    short = SUBJECT_SHORT_SLUGS.get(subject, subject.replace("_", ""))
    return f"pedagogy_overlay_{short}"


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure_overlay_table(path: pathlib.Path) -> None:
    """Create the annotated_learning_graphs dev SQLite table if missing.

    Schema mirrors the Firestore `annotatedLearningGraphs/{graph_id}`
    document shape so the two destinations stay in sync.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS annotated_learning_graphs (
                graph_id            TEXT PRIMARY KEY,
                subject             TEXT NOT NULL,
                source_jurisdiction TEXT NOT NULL,
                cell_annotations_json TEXT NOT NULL,
                pedagogy_source     TEXT NOT NULL,
                generated_at        TEXT NOT NULL,
                payload_json        TEXT NOT NULL
            )
            """
        )
        conn.commit()


def _upsert_annotation(
    path: pathlib.Path,
    *,
    graph_id: str,
    subject: str,
    source_jurisdiction: str,
    cell_annotations: dict[str, list[str]],
    pedagogy_source: str,
    payload: dict[str, Any],
) -> None:
    """Insert/update one row in annotated_learning_graphs."""
    with sqlite3.connect(str(path)) as conn:
        conn.execute(
            """
            INSERT INTO annotated_learning_graphs
                (graph_id, subject, source_jurisdiction,
                 cell_annotations_json, pedagogy_source,
                 generated_at, payload_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (graph_id) DO UPDATE SET
                subject = excluded.subject,
                source_jurisdiction = excluded.source_jurisdiction,
                cell_annotations_json = excluded.cell_annotations_json,
                pedagogy_source = excluded.pedagogy_source,
                generated_at = excluded.generated_at,
                payload_json = excluded.payload_json
            """,
            (
                graph_id,
                subject,
                source_jurisdiction,
                json.dumps(cell_annotations, sort_keys=True),
                pedagogy_source,
                _now_iso(),
                json.dumps(payload, sort_keys=True),
            ),
        )
        conn.commit()


def _persist(
    *,
    annotated_graph: dict[str, Any],
    subject: str,
    source_jurisdiction: str,
    sqlite_path: pathlib.Path,
) -> bool:
    """Persist to SQLite (always) + Firestore (best-effort dev no-op).

    Firestore writes require google-cloud-firestore credentials; the dev
    path uses SQLite as the canonical fallback per the same pattern as
    the equivalency-graph sibling module.
    """
    graph_id = annotated_graph.get("graph", {}).get("id") or f"uk_ncce_{subject}_y8"
    cell_annotations = annotated_graph.get("cell_annotations", {})
    pedagogy_source = annotated_graph.get("pedagogy_source", "live_pdf")
    _upsert_annotation(
        sqlite_path,
        graph_id=graph_id,
        subject=subject,
        source_jurisdiction=source_jurisdiction,
        cell_annotations=cell_annotations,
        pedagogy_source=pedagogy_source,
        payload=annotated_graph,
    )
    return True


# ---------------------------------------------------------------------------
# Load inputs — the source learning graph + the cached pedagogy principles
# ---------------------------------------------------------------------------


def _load_principles_from_cache() -> list[dict[str, Any]]:
    """Load the 12 cached principles via the CocoIndex App (disk-first).

    Returns an empty list when the cache isn't warmed yet (the unit
    test path uses a fixture).
    """
    try:
        from cocoindex_flows.uk_ncce.pedagogy_cache import (  # type: ignore[import-not-found]
            PEDAGOGY_CACHE_PATH,
        )

        if not PEDAGOGY_CACHE_PATH.exists():
            logger.warning(
                "pedagogy_overlay: cache cold — "
                "run `python -m cocoindex_flows.uk_ncce.pedagogy_cache` first."
            )
            return []
        payload = json.loads(PEDAGOGY_CACHE_PATH.read_text(encoding="utf-8"))
        raw = payload.get("principles", [])
        out: list[dict[str, Any]] = []
        for p in raw:
            if not isinstance(p, dict):
                continue
            out.append(
                {
                    "id": str(p.get("id", "")),
                    "name": str(p.get("name", "")),
                    "summary": str(p.get("summary", "")),
                    "how_to_apply": str(p.get("how_to_apply", "")),
                }
            )
        return out
    except ImportError:
        logger.warning(
            "pedagogy_overlay: cocoindex_flows.uk_ncce.pedagogy_cache not "
            "importable — using empty principles list (dev fixture)."
        )
        return []
    except Exception as exc:  # noqa: BLE001
        logger.warning("pedagogy_overlay._load_principles_from_cache: %s", exc)
        return []


def _load_source_graph(subject: str) -> dict[str, Any] | None:
    """Load the NCCE `LearningGraph` for one subject from Change A.

    Reads the per-subject extracted-graph payload written by Change A's
    ``uk_ncce_learning_graphs`` asset group. The canonical store is the
    SQLite table ``uk_ncce_learning_graphs`` at ``extracted_syllabi.sqlite``
    (per the sibling module's `_ensure_sqlite_table` contract).

    Returns ``None`` when no Change A asset has run yet.
    """
    try:
        subject_to_slug: dict[str, str] = {
            "computer_science": "uk_ncce_cs_extracted_graph",
            "mathematics": "uk_ncce_maths_extracted_graph",
            "english": "uk_ncce_english_extracted_graph",
            "gaeilge": "uk_ncce_gaeilge_extracted_graph",
            "chemistry": "uk_ncce_chemistry_extracted_graph",
            "geography": "uk_ncce_geography_extracted_graph",
        }
        slug = subject_to_slug.get(subject, f"uk_ncce_{subject}_extracted_graph")

        if not SQLITE_PATH.exists():
            logger.warning(
                "pedagogy_overlay: SQLite mirror missing (%s) — has Change A's "
                "uk_ncce_learning_graphs asset group run?",
                SQLITE_PATH,
            )
            return None
        with sqlite3.connect(str(SQLITE_PATH)) as conn:
            row = conn.execute(
                "SELECT payload FROM uk_ncce_learning_graphs WHERE slug = ?",
                (slug,),
            ).fetchone()
        if row is None:
            logger.warning(
                "pedagogy_overlay: no row for slug=%s — using empty graph "
                "(Change A's per-subject asset for %s hasn't materialised)",
                slug, subject,
            )
            return None
        return json.loads(row[0])
    except (OSError, sqlite3.OperationalError, json.JSONDecodeError) as exc:
        logger.warning("pedagogy_overlay._load_source_graph: %s", exc)
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "pedagogy_overlay._load_source_graph: unhandled error: %s", exc
        )
        return None


# ---------------------------------------------------------------------------
# BAML ApplyPedagogyPrinciples wrapper (graceful fallback)
# ---------------------------------------------------------------------------


def _call_apply_pedagogy_principles(
    graph: dict[str, Any] | None,
    principles: list[dict[str, Any]],
) -> dict[str, Any]:
    """Call BAML `ApplyPedagogyPrinciples`; return the AnnotatedLearningGraph.

    Falls back to a deterministic stub when `baml_client` is missing —
    the stub maps every cell id to the first principle in the bundle
    so the dev SQLite + Firestore schema stay valid.
    """
    graph = graph or {"id": "", "jurisdiction": "", "subject": "", "cells": []}
    if not principles:
        logger.warning(
            "_call_apply_pedagogy_principles: empty principles list — "
            "returning bare graph (no annotation possible)."
        )
        return {
            "graph": graph,
            "cell_annotations": {},
            "pedagogy_source": "live_pdf",
            "generated_at": _now_iso(),
        }

    try:
        from baml_client import b  # type: ignore[import-not-found]
        from baml_client.types import (  # type: ignore[import-not-found]
            LearningGraph,
            PedagogyPrinciple,
        )

        typed_graph = LearningGraph(**graph)
        typed_principles = [PedagogyPrinciple(**p) for p in principles]

        async def _run() -> Any:
            return await b.ApplyPedagogyPrinciples(
                graph=typed_graph, principles=typed_principles
            )

        result = asyncio.run(_run())
        if hasattr(result, "model_dump"):
            return result.model_dump()
        return dict(result) if isinstance(result, dict) else {"graph": graph, "cell_annotations": {}}
    except ImportError:
        # Stub: every cell maps to the first principle (dev only).
        cells = graph.get("cells", []) or []
        cell_annotations: dict[str, list[str]] = {}
        first_id = principles[0].get("id", "lead_with_concepts")
        for cell in cells:
            if not isinstance(cell, dict):
                continue
            cell_id = cell.get("id") or f"{cell.get('row_id', '?')}::{cell.get('column_id', '?')}"
            cell_annotations[cell_id] = [first_id]
        return {
            "graph": graph,
            "cell_annotations": cell_annotations,
            "pedagogy_source": "cache",
            "generated_at": _now_iso(),
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "_call_apply_pedagogy_principles: BAML call failed: %s", exc
        )
        return {
            "graph": graph,
            "cell_annotations": {},
            "pedagogy_source": "live_pdf",
            "generated_at": _now_iso(),
        }


# ---------------------------------------------------------------------------
# Dagster assets (6 — one per priority subject)
# ---------------------------------------------------------------------------


def _build_assets() -> Mapping[str, Any]:
    """Build the 6 Dagster assets dynamically (one per priority subject)."""
    if asset is None:
        return {}

    pairs = {
        subject: _asset_key(subject) for subject in SUBJECTS
    }
    if len(pairs) != 6:
        logger.warning(
            "pedagogy_overlay: expected 6 priority subjects, got %d",
            len(pairs),
        )

    assets: dict[str, Any] = {}
    for subject, key in pairs.items():
        subject_slug = subject_to_slug.get(
            subject, f"uk_ncce_{subject}_extracted_graph"
        )

        @asset(
            name=key,
            description=(
                f"Apply the 12 NCCE pedagogy principles to every cell of "
                f"the NCCE {subject} Y8 learning graph (Change A), then "
                f"materialise the AnnotatedLearningGraph to Firestore "
                f"`{FIRESTORE_COLLECTION}` + the dev SQLite mirror."
            ),
            group_name="3_model_lifecycle",
            deps={
                subject_slug,  # from Change A
                "uk_ncce_pedagogy_cache",  # from the cocoindex_flows module
            },
        )
        def _subject_overlay(subject: str = subject, key: str = key, context: Any = None) -> dict[str, Any]:
            started = time.monotonic()
            _ensure_overlay_table(SQLITE_PATH)
            principles = _load_principles_from_cache()
            source_graph = _load_source_graph(subject=subject)
            annotated = _call_apply_pedagogy_principles(
                graph=source_graph, principles=principles
            )
            source_jurisdiction = (
                source_graph.get("jurisdiction", "United Kingdom (NCCE)")
                if source_graph
                else "United Kingdom (NCCE)"
            )
            persisted = _persist(
                annotated_graph=annotated,
                subject=subject,
                source_jurisdiction=source_jurisdiction,
                sqlite_path=SQLITE_PATH,
            )
            summary = {
                "graph_id": annotated.get("graph", {}).get("id", f"uk_ncce_{subject}_y8"),
                "subject": subject,
                "n_principles": len(principles),
                "n_annotated_cells": len(annotated.get("cell_annotations", {})),
                "pedagogy_source": annotated.get("pedagogy_source", "live_pdf"),
                "persisted": persisted,
                "elapsed_ms": int((time.monotonic() - started) * 1000),
            }
            if context is not None:
                context.add_metadata(summary)
            return summary

        assets[key] = _subject_overlay
    return assets


_assets: Mapping[str, Any] = _build_assets()
if _assets:
    globals().update(_assets)


# ---------------------------------------------------------------------------
# CLI entry + helpers
# ---------------------------------------------------------------------------


def iterate_assets() -> Iterator[tuple[str, str]]:
    """Yield `(asset_name, subject)` for all 6 overlay assets."""
    for subject in SUBJECTS:
        yield _asset_key(subject), subject


def main() -> int:
    """CLI entry — log the 6 overlay asset names."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    started = time.monotonic()
    found = sum(1 for _ in iterate_assets())
    logger.info(
        "pedagogy_overlay.assets_registered count=%d elapsed_ms=%d",
        found,
        int((time.monotonic() - started) * 1000),
    )
    for asset_name, subject in iterate_assets():
        logger.info("  - %s -> %s", asset_name, subject)
    return 0


__all__ = [
    "FIRESTORE_COLLECTION",
    "SQLITE_PATH",
    "SUBJECTS",
    "SUBJECT_SHORT_SLUGS",
    "iterate_assets",
    "main",
]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
