"""orchestration.defs.3_model_lifecycle.learning_graph_equivalency_graph — unified cross-walk.

Phase 2 (cont.) of the OpenSpec change
[`2026-08-31-learning-graph-equivalency-graph-v1`](../../../../openspec/changes/2026-08-31-learning-graph-equivalency-graph-v1/proposal.md).

The sister module
`uk_ncce_learning_graph_equivalencies.py` builds 42 individual
`LearningGraphCrossReference` documents (one per (target jurisdiction x
subject) pair). This module owns the **aggregation** asset that runs
**after** all 42 assets have completed:

  - Reads every `LearningGraphCrossReference` document from the
    Firestore `prerequisiteEdges/{edge_id}` collection (or its dev
    SQLite mirror at `learning_graph_crossrefs`).
  - Writes the unified graph to FalkorDB
    `:CellEquivalentEdge` (when reachable; the dev-deploy Phase 8 path).
  - Returns the total edge count + the per-target-jurisdiction
    breakdown for the Dagster metadata view.

Per the spec delta:

    "WHEN the learning_graph_equivalency_graph asset runs
     THEN it SHALL read all 42 LearningGraphCrossReference documents
          from Firestore
     AND write the unified graph to FalkorDB :CellEquivalentEdge
     AND return the total edge count"
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
import pathlib
import sqlite3
import time
from collections.abc import Iterator
from typing import Any

logger = logging.getLogger(__name__)

try:
    from dagster import AssetExecutionContext, Output, asset
except ImportError:
    AssetExecutionContext = None  # type: ignore[assignment]
    Output = None  # type: ignore[assignment]
    asset = None  # type: ignore[assignment]
    logger.warning(
        "learning_graph_equivalency_graph: dagster not installed; "
        "running as a plain Python module only."
    )


# Re-use the constants + helpers from the sibling 42-asset module.
try:
    from .uk_ncce_learning_graph_equivalencies import (
        FIRESTORE_COLLECTION,
        PRIORITY_SUBJECTS,
        SOURCE_JURISDICTION,
        SQLITE_PATH,
        TARGET_JURISDICTIONS,
        iterate_assets,
    )
except ImportError:  # pragma: no cover — sibling module not yet importable
    FIRESTORE_COLLECTION = "prerequisiteEdges"
    PRIORITY_SUBJECTS: tuple[str, ...] = (
        "computer_science",
        "mathematics",
        "english",
        "gaeilge",
        "chemistry",
        "geography",
    )
    TARGET_JURISDICTIONS: tuple[str, ...] = (
        "ENGLAND",
        "WALES",
        "NORTHERN_IRELAND",
        "SCOTLAND",
        "ISLE_OF_MAN",
        "JERSEY",
        "GUERNSEY",
    )
    SQLITE_PATH = pathlib.Path(pathlib.Path.cwd() / "data" / "bi_ep" / "extracted_syllabi.sqlite")
    SOURCE_JURISDICTION = "UNITED_KINGDOM_NCCE"

    def iterate_assets() -> Iterator[tuple[str, str]]:
        for subject in PRIORITY_SUBJECTS:
            for jurisdiction in TARGET_JURISDICTIONS:
                yield f"uk_ncce_{subject}_{jurisdiction.lower()}_equivalencies", jurisdiction


# ---------------------------------------------------------------------------
# Source-of-truth — read every LearningGraphCrossReference from SQLite
# (the canonical dev fallback) + best-effort Firestore refresh.
# ---------------------------------------------------------------------------


def _read_crossrefs_from_sqlite(
    path: pathlib.Path,
) -> list[dict[str, Any]]:
    """Return every row from learning_graph_crossrefs as a list of dicts."""
    if not path.exists():
        logger.warning(
            "learning_graph_equivalency_graph.sqlite_missing path=%s — "
            "run the 42 uk_ncce_learning_graph_equivalencies assets first.",
            path,
        )
        return []
    out: list[dict[str, Any]] = []
    with sqlite3.connect(str(path)) as conn:
        try:
            rows = conn.execute(
                "SELECT edge_id, source_graph_id, target_graph_id, "
                "source_jurisdiction, target_jurisdiction, subject, "
                "cell_edges_json, overall_confidence, generated_at "
                "FROM learning_graph_crossrefs"
            ).fetchall()
        except sqlite3.OperationalError as exc:
            logger.warning(
                "learning_graph_equivalency_graph: learning_graph_crossrefs "
                "table missing — has any uk_ncce_learning_graph_equivalencies "
                "asset run? reason=%s",
                exc,
            )
            return []
    for (
        edge_id,
        source_graph_id,
        target_graph_id,
        source_jurisdiction,
        target_jurisdiction,
        subject,
        cell_edges_json,
        overall_confidence,
        generated_at,
    ) in rows:
        try:
            cell_edges = json.loads(cell_edges_json)
        except (TypeError, json.JSONDecodeError):
            cell_edges = []
        out.append(
            {
                "edge_id": edge_id,
                "source_graph_id": source_graph_id,
                "target_graph_id": target_graph_id,
                "jurisdiction_pair": {
                    "source": source_jurisdiction,
                    "target": target_jurisdiction,
                },
                "cell_edges": cell_edges,
                "overall_confidence": float(overall_confidence),
                "generated_at": generated_at,
                "subject": subject,
            }
        )
    return out


def _count_edges(crossrefs: list[dict[str, Any]]) -> int:
    """Total number of cell-level equivalency edges across all crossrefs."""
    return sum(len(c.get("cell_edges") or []) for c in crossrefs)


def _per_jurisdiction_breakdown(
    crossrefs: list[dict[str, Any]],
) -> dict[str, int]:
    """Map target_jurisdiction -> edge count for the Dagster metadata view."""
    counts: dict[str, int] = {}
    for c in crossrefs:
        target = c["jurisdiction_pair"]["target"]
        counts[target] = counts.get(target, 0) + len(c.get("cell_edges") or [])
    return counts


# ---------------------------------------------------------------------------
# FalkorDB mirror — best-effort
# ---------------------------------------------------------------------------


def _write_to_falkordb(crossrefs: list[dict[str, Any]]) -> bool:
    """Write the unified cross-walk to FalkorDB `:CellEquivalentEdge`.

    Returns ``True`` when the write committed (or when FalkorDB isn't
    installed — the dev path), ``False`` on transport failure. NEVER
    raises — the disk+SQLite path is the canonical dev fallback per the
    spec ("FalkorDB is available, dev-deploy path").
    """
    try:
        import falkordb  # type: ignore[import-not-found]
    except ImportError:
        logger.info(
            "learning_graph_equivalency_graph.falkordb_unavailable — "
            "skipping the FalkorDB mirror (SQLite is the canonical dev fallback)."
        )
        return True

    try:
        graph = falkordb.select_graph("cianhoghlaim")  # type: ignore[union-attr]
        for c in crossrefs:
            target = c["jurisdiction_pair"]["target"]
            for ce in c.get("cell_edges") or []:
                graph.query(  # type: ignore[union-attr]
                    "MERGE (s:LearningGraphCell {id: $source_id}) "
                    "MERGE (t:LearningGraphCell {id: $target_id}) "
                    "MERGE (s)-[r:CELL_EQUIVALENT_EDGE "
                    "{confidence: $conf, target_jurisdiction: $tgt}]->(t)",
                    params={
                        "source_id": c["source_graph_id"],
                        "target_id": ce.get("cell_id", ""),
                        "tgt": target,
                        "conf": float(ce.get("confidence", 0.0)),
                    },
                )
        logger.info(
            "learning_graph_equivalency_graph.falkordb_wrote edges=%d",
            _count_edges(crossrefs),
        )
        return True
    except Exception as exc:
        logger.warning("learning_graph_equivalency_graph.falkordb_failed reason=%s", exc)
        return False


# ---------------------------------------------------------------------------
# Dagster asset
# ---------------------------------------------------------------------------


def _build_asset() -> Any:
    """Build the `learning_graph_equivalency_graph` Dagster asset."""
    if asset is None:
        return None

    @asset(
        description=(
            "Aggregate the 42 uk_ncce_<subject>_<jurisdiction>_equivalencies "
            "outputs into a single unified cross-walk graph; mirror to "
            "FalkorDB :CellEquivalentEdge; return total edge count."
        ),
        group_name="3_model_lifecycle",
        deps=[
            f"uk_ncce_{subject}_{jurisdiction.lower()}_equivalencies"
            for subject in PRIORITY_SUBJECTS
            for jurisdiction in TARGET_JURISDICTIONS
        ],
    )
    def _learning_graph_equivalency_graph(context: Any) -> dict[str, Any]:
        started = time.monotonic()
        crossrefs = _read_crossrefs_from_sqlite(SQLITE_PATH)
        total_edges = _count_edges(crossrefs)
        breakdown = _per_jurisdiction_breakdown(crossrefs)
        falkordb_ok = _write_to_falkordb(crossrefs)

        summary = {
            "generated_at": _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total_crossrefs": len(crossrefs),
            "total_cell_equivalent_edges": total_edges,
            "per_jurisdiction_breakdown": breakdown,
            "falkordb_committed": falkordb_ok,
            "elapsed_ms": int((time.monotonic() - started) * 1000),
        }
        if context is not None:
            context.add_metadata(
                {
                    "total_crossrefs": len(crossrefs),
                    "total_cell_equivalent_edges": total_edges,
                    "falkordb_committed": falkordb_ok,
                    "elapsed_ms": summary["elapsed_ms"],
                }
            )
        return summary

    return _learning_graph_equivalency_graph


_asset = _build_asset()
if _asset is not None:
    globals()["learning_graph_equivalency_graph"] = _asset


def main() -> int:
    """CLI entry — log the per-target-jurisdiction breakdown."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    started = time.monotonic()
    crossrefs = _read_crossrefs_from_sqlite(SQLITE_PATH)
    total = _count_edges(crossrefs)
    breakdown = _per_jurisdiction_breakdown(crossrefs)
    falkordb_ok = _write_to_falkordb(crossrefs)
    elapsed_ms = int((time.monotonic() - started) * 1000)
    logger.info(
        "learning_graph_equivalency_graph.summary crossrefs=%d edges=%d falkordb=%s elapsed_ms=%d",
        len(crossrefs),
        total,
        falkordb_ok,
        elapsed_ms,
    )
    for jurisdiction, edges in sorted(breakdown.items()):
        logger.info("  - %s : %d cell-equivalent edges", jurisdiction, edges)
    return 0


__all__ = [
    "FIRESTORE_COLLECTION",
    "main",
]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
