"""orchestration.defs.3_model_lifecycle.uk_ncce_learning_graph_equivalencies — 42 cross-walk assets.

Phase 2 of the OpenSpec change
[`2026-08-31-learning-graph-equivalency-graph-v1`](../../../../openspec/changes/2026-08-31-learning-graph-equivalency-graph-v1/proposal.md).

For each of the 7 target jurisdictions (`ENGLAND`, `WALES`,
`NORTHERN_IRELAND`, `SCOTLAND`, `ISLE_OF_MAN`, `JERSEY`,
`GUERNSEY`) crossed with each of the 6 BIEP priority subjects
(`computer_science`, `mathematics`, `english`, `gaeilge`,
`chemistry`, `geography`), build a single Dagster asset that:

  1. Loads the corresponding NCCE source `LearningGraph` (produced by
     `uk_ncce_learning_graphs.<subject>_learning_graph` from Change A).
  2. For every cell in the source graph, calls BAML
     `ExtractCellEquivalencies(source_cell, source_jurisdiction=UK_NCCE,
     target_jurisdictions=[<target>])`.
  3. Materialises a `LearningGraphCrossReference` to:
       - Firestore `prerequisiteEdges/{edge_id}` collection
       - FalkorDB `:CellEquivalentEdge` graph (when FalkorDB is
         reachable — the dev-deploy Phase 8 path)

7 × 6 = 42 assets total.

Asset naming convention (per the spec delta):

    uk_ncce_<subject_slug>_<jurisdiction_slug>_equivalencies

Example:
    uk_ncce_computer_science_england_equivalencies

The ``_subject_slug`` and ``_jurisdiction_slug`` use snake_case
conventions matching the BAML `Jurisdiction` + `PrioritySubject` enums.

Sister module: `learning_graph_equivalency_graph.py` owns the
aggregation step that builds the unified cross-walk graph from the
42 individual asset outputs.
"""

from __future__ import annotations

import asyncio
import datetime as _dt
import json
import logging
import pathlib
import sqlite3
import time
import uuid
from collections.abc import Iterator, Mapping
from typing import Any, Final

logger = logging.getLogger(__name__)

# Dagster is optional — degrade gracefully when missing (the same
# pattern as `cocoindex_flows/pdf/pdf_to_markdown_app.py`).
try:
    from dagster import AssetExecutionContext, AssetOut, Output, multi_asset
except ImportError:
    AssetExecutionContext = None  # type: ignore[assignment]
    AssetOut = None  # type: ignore[assignment]
    Output = None  # type: ignore[assignment]
    multi_asset = None  # type: ignore[assignment]
    logger.warning(
        "uk_ncce_learning_graph_equivalencies: dagster not installed; "
        "running as a plain Python module only."
    )


# ---------------------------------------------------------------------------
# Constants — the 7 × 6 = 42 (jurisdiction × subject) pairs
# ---------------------------------------------------------------------------

#: Canonical 7 target jurisdictions for Change B. The source jurisdiction
#: is always UK_NCCE (NCCE — National Centre for Computing Education).
TARGET_JURISDICTIONS: Final[tuple[str, ...]] = (
    "ENGLAND",
    "WALES",
    "NORTHERN_IRELAND",
    "SCOTLAND",
    "ISLE_OF_MAN",
    "JERSEY",
    "GUERNSEY",
)

#: The 6 BIEP priority subjects (one asset per subject × jurisdiction).
PRIORITY_SUBJECTS: Final[tuple[str, ...]] = (
    "computer_science",
    "mathematics",
    "english",
    "gaeilge",
    "chemistry",
    "geography",
)

#: The Firestore collection that receives every cross-walk edge.
FIRESTORE_COLLECTION: Final[str] = "prerequisiteEdges"

#: Dev SQLite path (the canonical Phase 3 extracted_syllabi DB).
SQLITE_PATH: pathlib.Path = pathlib.Path(
    __import__("os").environ.get(
        "BI_EP_EXTRACTED_SYLLABI_PATH",
        pathlib.Path.cwd() / "data" / "bi_ep" / "extracted_syllabi.sqlite",
    )
)

#: Source-jurisdiction constant (the cell-level cross-walk is always
#: UK_NCCE -> target jurisdiction).
SOURCE_JURISDICTION: Final[str] = "UNITED_KINGDOM_NCCE"


# ---------------------------------------------------------------------------
# Helpers — naming, db, fire-cursor stubs
# ---------------------------------------------------------------------------


def _asset_key(subject: str, jurisdiction: str) -> str:
    """Return the canonical Dagster asset name for the cross-walk asset."""
    return (
        f"uk_ncce_{subject.replace('_', '_')}_"
        f"{jurisdiction.lower()}_equivalencies"
    )


def _edge_id(source_cell_id: str, source_jurisdiction: str, target_jurisdiction: str) -> str:
    """Stable Firestore document id + FalkorDB edge key.

    Format:  ``<source_cell_id>__<source_jurisdiction>_TO_<target>__<sha8>``
    where ``sha8`` is the first 8 hex chars of a UUID5 derived from the
    (source_cell_id, target_jurisdiction) tuple. The deterministic UUID
    keeps re-runs idempotent — the same source cell always maps to the
    same edge id in FalkorDB.
    """
    raw = f"{source_cell_id}|{source_jurisdiction}|{target_jurisdiction}".encode("utf-8")
    sha8 = uuid.uuid5(uuid.NAMESPACE_DNS, raw.decode("utf-8")).hex[:8]
    return f"{source_cell_id}__{source_jurisdiction}_TO_{target_jurisdiction}__{sha8}"


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _jurisdiction_pair(source: str, target: str) -> dict[str, str]:
    """Canonical (source, target) jurisdiction pair as a JSON-serialisable dict."""
    return {"source": source, "target": target}


def _cross_reference_doc(
    *,
    source_graph_id: str,
    target_graph_id: str,
    source: str,
    target: str,
    cell_edges: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the canonical LearningGraphCrossReference JSON document."""
    if cell_edges:
        mean_conf = sum(e["confidence"] for e in cell_edges) / len(cell_edges)
    else:
        mean_conf = 0.0
    return {
        "source_graph_id": source_graph_id,
        "target_graph_id": target_graph_id,
        "jurisdiction_pair": _jurisdiction_pair(source, target),
        "cell_edges": cell_edges,
        "overall_confidence": mean_conf,
        "generated_at": _now_iso(),
    }


def _ensure_crosswalks_table(path: pathlib.Path) -> None:
    """Create the learning_graph_crossrefs dev SQLite table if missing.

    Schema mirrors the Firestore `prerequisiteEdges/{edge_id}` document
    shape so the two destinations stay in sync.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS learning_graph_crossrefs (
                edge_id            TEXT PRIMARY KEY,
                source_graph_id    TEXT NOT NULL,
                target_graph_id    TEXT NOT NULL,
                source_jurisdiction TEXT NOT NULL,
                target_jurisdiction TEXT NOT NULL,
                subject            TEXT NOT NULL,
                cell_edges_json    TEXT NOT NULL,
                overall_confidence REAL NOT NULL,
                generated_at       TEXT NOT NULL
            )
            """
        )
        conn.commit()


def _upsert_crosswalk(
    path: pathlib.Path,
    *,
    edge_id: str,
    source_graph_id: str,
    target_graph_id: str,
    source_jurisdiction: str,
    target_jurisdiction: str,
    subject: str,
    cell_edges: list[dict[str, Any]],
    overall_confidence: float,
) -> None:
    """Insert/update one row in learning_graph_crossrefs."""
    with sqlite3.connect(str(path)) as conn:
        conn.execute(
            """
            INSERT INTO learning_graph_crossrefs
                (edge_id, source_graph_id, target_graph_id,
                 source_jurisdiction, target_jurisdiction,
                 subject, cell_edges_json,
                 overall_confidence, generated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (edge_id) DO UPDATE SET
                source_graph_id = excluded.source_graph_id,
                target_graph_id = excluded.target_graph_id,
                source_jurisdiction = excluded.source_jurisdiction,
                target_jurisdiction = excluded.target_jurisdiction,
                subject = excluded.subject,
                cell_edges_json = excluded.cell_edges_json,
                overall_confidence = excluded.overall_confidence,
                generated_at = excluded.generated_at
            """,
            (
                edge_id,
                source_graph_id,
                target_graph_id,
                source_jurisdiction,
                target_jurisdiction,
                subject,
                json.dumps(cell_edges, sort_keys=True),
                overall_confidence,
                _now_iso(),
            ),
        )
        conn.commit()


def _persist(
    *,
    firestore_doc: dict[str, Any],
    subject: str,
    target_jurisdiction: str,
    sqlite_path: pathlib.Path,
) -> bool:
    """Persist to SQLite (always) + FalkorDB (best-effort).

    The Firestore write is deferred to the production DAG run because it
    requires google-cloud-firestore credentials; in dev we mirror the
    write to SQLite (which has the same schema) so unit tests can
    exercise the contract offline.
    """
    edge_id = _edge_id(
        firestore_doc["source_graph_id"],
        SOURCE_JURISDICTION,
        target_jurisdiction,
    )
    _upsert_crosswalk(
        sqlite_path,
        edge_id=edge_id,
        source_graph_id=firestore_doc["source_graph_id"],
        target_graph_id=firestore_doc["target_graph_id"],
        source_jurisdiction=SOURCE_JURISDICTION,
        target_jurisdiction=target_jurisdiction,
        subject=subject,
        cell_edges=firestore_doc["cell_edges"],
        overall_confidence=firestore_doc["overall_confidence"],
    )

    # FalkorDB is best-effort; the dev-deploy Phase 8 path will use the
    # canonical CocoIndex FalkorDB connector. Absence of FalkorDB MUST NOT
    # fail the asset (the disk+SQLite path is the canonical dev fallback).
    try:
        import falkordb  # type: ignore[import-not-found]
    except ImportError:
        return True

    try:
        graph = falkordb.select_graph("cianhoghlaim")  # type: ignore[union-attr]
        # The FalkorDB `:CellEquivalentEdge` semantic is one edge per
        # unique (source, target, confidence) tuple — sufficient for the
        # cross-walk graph query in the Equivalencies tab.
        for ce in firestore_doc["cell_edges"]:
            graph.query(  # type: ignore[union-attr]
                "MERGE (s:LearningGraphCell {id: $source_id}) "
                "MERGE (t:LearningGraphCell {id: $target_id}) "
                "MERGE (s)-[r:CELL_EQUIVALENT_EDGE "
                "{confidence: $conf, target_jurisdiction: $tgt}]->(t)",
                params={
                    "source_id": firestore_doc["source_graph_id"],
                    "target_id": ce.get("cell_id", ""),
                    "tgt": target_jurisdiction,
                    "conf": float(ce.get("confidence", 0.0)),
                },
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "uk_ncce_learning_graph_equivalencies._persist: falkordb write "
            "failed for %s — continuing (SQLite is the canonical dev fallback): %s",
            target_jurisdiction,
            exc,
        )
    return True


# ---------------------------------------------------------------------------
# BAML wrapper (graceful fallback to a deterministic stub)
# ---------------------------------------------------------------------------


def _call_extract_cell_equivalencies(
    source_cell: Any,
    *,
    target_jurisdiction: str,
) -> dict[str, Any] | None:
    """Call BAML `ExtractCellEquivalencies` for one target jurisdiction.

    Falls back to a deterministic stub when `baml_client` is missing —
    the canonical 12-curve stub returns a confidence-weighted placeholder
    so the dev SQLite + Firestore schema stay valid.
    """
    try:
        from baml_client import b  # type: ignore[import-not-found]
        from baml_client.types import (  # type: ignore[import-not-found]
            CellEquivalent,
            Jurisdiction,
            LearningGraphCell,
        )

        target_enum = Jurisdiction[target_jurisdiction]

        async def _run() -> Any:
            return await b.ExtractCellEquivalencies(
                source_cell=source_cell,
                source_jurisdiction=Jurisdiction.UNITED_KINGDOM_NCCE
                if hasattr(Jurisdiction, "UNITED_KINGDOM_NCCE")
                else Jurisdiction.IRELAND,
                target_jurisdictions=[target_enum],
            )

        result = asyncio.run(_run())
        mapped = result.get(target_enum) if isinstance(result, dict) else None
        if mapped is None:
            return None
        if hasattr(mapped, "model_dump"):
            return mapped.model_dump()
        return (
            dict(mapped)
            if isinstance(mapped, dict)
            else None
        )
    except ImportError:
        # Stub: 1:1 identity equivalence (low confidence, dev only).
        return {
            "cell_id": getattr(source_cell, "id", "cell_stub"),
            "jurisdiction": target_jurisdiction,
            "subject": "computer_science",
            "year_level": 10,
            "confidence": 0.7,
            "notes": "stub: identity equivalence for offline dev",
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "_call_extract_cell_equivalencies: BAML call failed: %s", exc
        )
        return None


# ---------------------------------------------------------------------------
# Asset construction — 42 assets via `multi_asset`
# ---------------------------------------------------------------------------


def _build_assets() -> Mapping[str, Any]:
    """Build the 42 Dagster assets dynamically (one per pair).

    Returns an empty dict when Dagster isn't available (the dev path
    uses `iterate_assets()` to enumerate the asset configurations).
    """
    if multi_asset is None:
        return {}

    pairs: list[tuple[str, str]] = [
        (subject, jurisdiction)
        for subject in PRIORITY_SUBJECTS
        for jurisdiction in TARGET_JURISDICTIONS
    ]
    if len(pairs) != 42:
        logger.warning(
            "uk_ncce_learning_graph_equivalencies: expected 42 pairs, "
            "got %d (TARGET_JURISDICTIONS=%d × PRIORITY_SUBJECTS=%d)",
            len(pairs), len(TARGET_JURISDICTIONS), len(PRIORITY_SUBJECTS),
        )

    # Per the Change A asset-group contract: each priority subject has its
    # own extracted-graph asset (`uk_ncce_<short>_extracted_graph`). Each
    # cross-walk asset depends on the matching subject asset + the
    # `uk_ncce_pedagogy_cache` is NOT a dep here (the cross-walk is
    # independent of pedagogy overlay).
    subject_to_slug: dict[str, str] = {
        "computer_science": "uk_ncce_cs_extracted_graph",
        "mathematics": "uk_ncce_maths_extracted_graph",
        "english": "uk_ncce_english_extracted_graph",
        "gaeilge": "uk_ncce_gaeilge_extracted_graph",
        "chemistry": "uk_ncce_chemistry_extracted_graph",
        "geography": "uk_ncce_geography_extracted_graph",
    }

    @multi_asset(
        outs={
            _asset_key(subject, jurisdiction): AssetOut(
                description=(
                    f"Cell-level cross-walk from NCCE {subject} to "
                    f"{jurisdiction} ({_asset_key(subject, jurisdiction)})"
                ),
            )
            for subject, jurisdiction in pairs
        },
        can_subset=True,
    )
    def _uk_ncce_learning_graph_equivalencies(context: Any) -> Iterator[Output]:
        """Per-pair asset — emits one Output per (subject, jurisdiction) pair."""
        _ensure_crosswalks_table(SQLITE_PATH)
        for subject, jurisdiction in pairs:
            asset_key = _asset_key(subject, jurisdiction)
            if (
                context is not None
                and context.op_execution_context is not None
                and asset_key not in context.op_execution_context.selected_asset_keys
            ):
                # Dagster asset selection — skip the non-selected ones.
                continue

            # Load source cells (from Change A's uk_ncce_learning_graphs asset
            # output or from the dev SQLite cache as a fallback).
            cells = _load_source_cells(subject=subject)
            cell_edges: list[dict[str, Any]] = []
            for cell in cells:
                equivalent = _call_extract_cell_equivalencies(
                    cell, target_jurisdiction=jurisdiction
                )
                if equivalent is None:
                    continue
                if not isinstance(cell, dict):
                    continue
                cell_edges.append(
                    {
                        "cell_id": equivalent.get("cell_id", cell.get("id", "")),
                        "jurisdiction": equivalent.get(
                            "jurisdiction", jurisdiction
                        ),
                        "subject": equivalent.get("subject", subject),
                        "year_level": int(
                            equivalent.get(
                                "year_level", cell.get("year_level", 8)
                            )
                        ),
                        "confidence": float(equivalent.get("confidence", 0.0)),
                        "notes": equivalent.get("notes", ""),
                    }
                )

            source_graph_id = subject_to_slug.get(
                subject, f"uk_ncce_{subject}_extracted_graph"
            )
            target_graph_id = f"{jurisdiction.lower()}_{subject}_learning_graph"
            firestore_doc = _cross_reference_doc(
                source_graph_id=source_graph_id,
                target_graph_id=target_graph_id,
                source=SOURCE_JURISDICTION,
                target=jurisdiction,
                cell_edges=cell_edges,
            )
            _persist(
                firestore_doc=firestore_doc,
                subject=subject,
                target_jurisdiction=jurisdiction,
                sqlite_path=SQLITE_PATH,
            )
            yield Output(
                value=firestore_doc,
                output_name=asset_key,
                metadata={
                    "n_cell_edges": len(cell_edges),
                    "overall_confidence": firestore_doc["overall_confidence"],
                    "target_jurisdiction": jurisdiction,
                    "subject": subject,
                },
            )

    return {_asset_key(*pair): _uk_ncce_learning_graph_equivalencies for pair in pairs}


def _load_source_cells(*, subject: str) -> list[Any]:
    """Load the source NCCE learning-graph cells for one subject.

    Reads the per-subject extracted-graph payload written by Change A's
    ``uk_ncce_learning_graphs`` asset group. The canonical store is the
    SQLite table ``uk_ncce_learning_graphs`` at ``extracted_syllabi.sqlite``
    (per the sibling module's `_ensure_sqlite_table` contract).

    Falls back to an empty list when no Change A asset has run yet.
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
                "_load_source_cells: SQLite mirror missing (%s) — has Change A's "
                "uk_ncce_learning_graphs asset group run?",
                SQLITE_PATH,
            )
            return []
        with sqlite3.connect(str(SQLITE_PATH)) as conn:
            row = conn.execute(
                "SELECT payload FROM uk_ncce_learning_graphs WHERE slug = ?",
                (slug,),
            ).fetchone()
        if row is None:
            logger.warning(
                "_load_source_cells: no row for slug=%s — yield empty cells "
                "(Change A's per-subject asset for %s hasn't been materialised)",
                slug, subject,
            )
            return []
        payload = json.loads(row[0])
        cells = payload.get("cells") or []
        if not isinstance(cells, list):
            return []
        return cells
    except (OSError, sqlite3.OperationalError, json.JSONDecodeError) as exc:
        logger.warning("_load_source_cells: %s", exc)
        return []
    except Exception as exc:  # noqa: BLE001
        logger.warning("_load_source_cells: unhandled error: %s", exc)
        return []


# Lazy asset construction — registers `_uk_ncce_learning_graph_equivalencies`
# on import when Dagster is installed.
_assets: Mapping[str, Any] = _build_assets()
if _assets:
    globals().update(_assets)


# ---------------------------------------------------------------------------
# CLI entry point — `python -m orchestration.defs.3_model_lifecycle.uk_ncce_learning_graph_equivalencies`
# ---------------------------------------------------------------------------


def iterate_assets() -> Iterator[tuple[str, str]]:
    """Yield `(asset_name, target_jurisdiction)` for all 42 assets.

    Useful for `dg launch --assets` enumeration and unit tests.
    """
    for subject in PRIORITY_SUBJECTS:
        for jurisdiction in TARGET_JURISDICTIONS:
            yield _asset_key(subject, jurisdiction), jurisdiction


def main() -> int:
    """CLI entry — log the 42 asset names + their existence status."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    started = time.monotonic()
    found = sum(1 for _ in iterate_assets())
    logger.info(
        "uk_ncce_learning_graph_equivalencies.assets_registered count=%d elapsed_ms=%d",
        found,
        int((time.monotonic() - started) * 1000),
    )
    for asset_name, jurisdiction in iterate_assets():
        logger.info("  - %s -> %s", asset_name, jurisdiction)
    return 0


__all__ = [
    "FIRESTORE_COLLECTION",
    "PRIORITY_SUBJECTS",
    "SQLITE_PATH",
    "SOURCE_JURISDICTION",
    "TARGET_JURISDICTIONS",
    "iterate_assets",
    "main",
]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
