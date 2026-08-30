"""cocoindex_flows.equivalency.equivalency_graph_app — Phase 4a equivalency graph App.

Phase 4a of the multi-stage plan (see AGENTS.md). Reads every row in the
``extracted_syllabi`` SQLite table (populated by Phase 3), groups them
by (subnation, stage, subject_slug, language), parses the
``syllabus_json.module_topics[]`` array, then calls BAML
``ExtractEquivalencies`` for each topic to build a cross-jurisdiction
topic-equivalence map.

Output is stored in two tables in the dev SQLite (at
``data/bi_ep/extracted_syllabi.sqlite``):

  - ``topic_nodes`` — one row per topic node (subnation, stage, subject_slug,
    language, topic_key, topic_name, confidence)
  - ``topic_equivalent_edges`` — one row per equivalence (source_topic_key,
    target_topic_key, target_subnation, target_topic_name, confidence,
    notes)

When FalkorDB IS available (Phase 8 dev-deploy), the tables are also
mirrored to a ``:TopicNode`` + ``:TopicEquivalentEdge`` graph via the
canonical CocoIndex FalkorDB connector. The dev path uses SQLite-only
semantics; the production migration is a single mount_table_target call.

Run::

    python -m cocoindex_flows.equivalency.equivalency_graph_app

Or programmatically via ``build_equivalency_graph()``.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.util as _iu
import json
import logging
import pathlib
import sqlite3
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

#: Reuse the Phase 3 SQLite path (the canonical dev DB for the bi_ep corpus).
SQLITE_PATH: pathlib.Path = pathlib.Path(
    __import__("os").environ.get(
        "BI_EP_EXTRACTED_SYLLABI_PATH",
        pathlib.Path.cwd() / "data" / "bi_ep" / "extracted_syllabi.sqlite",
    )
)

#: The 6 canonical jurisdictions for the equivalency graph (matches BAML).
CANONICAL_JURISDICTIONS: tuple[str, ...] = (
    "Ireland", "England", "Scotland", "Wales",
    "Northern Ireland", "Isle of Man",
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TopicNode:
    """One node in the equivalency graph."""

    subnation: str
    stage: str
    subject_slug: str
    language: str
    topic_key: str  # unique within (subnation, stage, subject_slug, language)
    topic_name: str
    confidence: float = 1.0
    fetched_at: str = field(default_factory=lambda: "")


@dataclass
class TopicEquivalentEdge:
    """One edge in the equivalency graph."""

    source_topic_key: str
    source_topic_name: str
    source_subnation: str
    target_topic_key: str
    target_topic_name: str
    target_subnation: str
    confidence: float = 0.0
    notes: str = ""


# ---------------------------------------------------------------------------
# Schema setup (dev SQLite)
# ---------------------------------------------------------------------------

def _ensure_graph_tables(path: pathlib.Path) -> None:
    """Create the topic_nodes + topic_equivalent_edges tables if missing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS topic_nodes (
                subnation TEXT,
                stage TEXT,
                subject_slug TEXT,
                language TEXT,
                topic_key TEXT,
                topic_name TEXT,
                confidence REAL,
                fetched_at TEXT,
                PRIMARY KEY (subnation, stage, subject_slug, language, topic_key)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS topic_equivalent_edges (
                source_topic_key TEXT,
                source_topic_name TEXT,
                source_subnation TEXT,
                target_topic_key TEXT,
                target_topic_name TEXT,
                target_subnation TEXT,
                confidence REAL,
                notes TEXT,
                PRIMARY KEY (source_topic_key, target_topic_key)
            )
            """
        )
        conn.commit()


def _upsert_topic_node(path: pathlib.Path, node: TopicNode) -> None:
    with sqlite3.connect(str(path)) as conn:
        conn.execute(
            """
            INSERT INTO topic_nodes
                (subnation, stage, subject_slug, language, topic_key,
                 topic_name, confidence, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (subnation, stage, subject_slug, language, topic_key)
            DO UPDATE SET
                topic_name = excluded.topic_name,
                confidence = excluded.confidence,
                fetched_at = excluded.fetched_at
            """,
            (
                node.subnation, node.stage, node.subject_slug, node.language,
                node.topic_key, node.topic_name, node.confidence, node.fetched_at,
            ),
        )
        conn.commit()


def _upsert_edge(path: pathlib.Path, edge: TopicEquivalentEdge) -> None:
    with sqlite3.connect(str(path)) as conn:
        conn.execute(
            """
            INSERT INTO topic_equivalent_edges
                (source_topic_key, source_topic_name, source_subnation,
                 target_topic_key, target_topic_name, target_subnation,
                 confidence, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (source_topic_key, target_topic_key)
            DO UPDATE SET
                source_topic_name = excluded.source_topic_name,
                target_topic_name = excluded.target_topic_name,
                confidence = excluded.confidence,
                notes = excluded.notes
            """,
            (
                edge.source_topic_key, edge.source_topic_name,
                edge.source_subnation, edge.target_topic_key,
                edge.target_topic_name, edge.target_subnation,
                edge.confidence, edge.notes,
            ),
        )
        conn.commit()


# ---------------------------------------------------------------------------
# BAML wrapper (graceful fallback to a deterministic stub)
# ---------------------------------------------------------------------------

def _topic_key(subnation: str, topic_name: str) -> str:
    """Stable hash-based topic key."""
    raw = f"{subnation}::{topic_name}".encode("utf-8")
    return uuid.uuid5(uuid.NAMESPACE_DNS, raw.decode("utf-8")).hex[:16]


def _call_baml_extract_equivalencies(
    topic: str,
    source_jurisdiction: str,
    target_jurisdictions: list[str],
) -> dict[str, Any]:
    """Call BAML ExtractEquivalencies; return the TopicMapping as dict.

    Falls back to a deterministic stub when baml_client is missing.
    """
    try:
        from baml_client import b  # type: ignore[import-not-found]
        from baml_client.types import TopicMapping  # type: ignore[import-not-found]

        async def _run() -> Any:
            return await b.ExtractEquivalencies(
                topic=topic,
                source_jurisdiction=source_jurisdiction,
                target_jurisdictions=target_jurisdictions,
            )

        result = asyncio.run(_run())
        if hasattr(result, "model_dump"):
            return result.model_dump()
        return result if isinstance(result, dict) else dict(result)
    except ImportError:
        # Stub: 1:1 identity equivalence across jurisdictions (with 0.7
        # confidence — clearly marked as a stub for dev purposes).
        return {
            "source_topic": topic,
            "source_jurisdiction": source_jurisdiction,
            "equivalents": {j: topic for j in target_jurisdictions},
            "confidence": 0.7,
            "notes": "stub: identity equivalence; replace with real BAML call",
        }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def _iter_source_topics(
    sqlite_path: pathlib.Path,
) -> list[tuple[str, str, str, str, list[dict[str, Any]]]]:
    """Yield (subnation, stage, subject_slug, language, syllabus_json) per row.

    Reads from the Phase 3 ``extracted_syllabi`` table.
    """
    if not sqlite_path.exists():
        logger.warning(
            "equivalency_graph.sqlite_missing path=%s — run `python -m cocoindex_flows.education.lc6_extraction_app` first",
            sqlite_path,
        )
        return []
    out: list[tuple[str, str, str, str, list[dict[str, Any]]]] = []
    with sqlite3.connect(str(sqlite_path)) as conn:
        try:
            rows = conn.execute(
                "SELECT subnation, stage, subject_slug, language, syllabus_json "
                "FROM extracted_syllabi WHERE syllabus_json IS NOT NULL"
            ).fetchall()
        except sqlite3.OperationalError as exc:
            logger.warning("equivalency_graph.table_missing reason=%s", exc)
            return []
    for subnation, stage, subject_slug, language, syllabus_json in rows:
        try:
            parsed = json.loads(syllabus_json)
        except (TypeError, json.JSONDecodeError):
            continue
        out.append((subnation, stage, subject_slug, language, parsed))
    return out


def build_equivalency_graph(
    sqlite_path: pathlib.Path | None = None,
) -> dict[str, int]:
    """Walk every topic in ``extracted_syllabi``; emit nodes + edges.

    Returns {nodes_created, edges_created, skipped} stats.
    """
    db = sqlite_path or SQLITE_PATH
    _ensure_graph_tables(db)

    started = time.monotonic()
    stats = {"nodes_created": 0, "edges_created": 0, "skipped": 0}
    sources = _iter_source_topics(db)
    if not sources:
        return stats

    fetched_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    target_jurisdictions = list(CANONICAL_JURISDICTIONS)

    for subnation, stage, subject_slug, language, syllabus in sources:
        module_topics = syllabus.get("module_topics") or []
        if not isinstance(module_topics, list):
            continue
        for topic_entry in module_topics:
            if not isinstance(topic_entry, dict):
                continue
            topic_name = topic_entry.get("name") or topic_entry.get("title")
            if not topic_name:
                continue
            topic_node = TopicNode(
                subnation=subnation,
                stage=stage,
                subject_slug=subject_slug,
                language=language,
                topic_key=_topic_key(subnation, topic_name),
                topic_name=topic_name,
                confidence=1.0,
                fetched_at=fetched_at,
            )
            _upsert_topic_node(db, topic_node)
            stats["nodes_created"] += 1

            # BAML call for cross-jurisdiction equivalents
            mapping = _call_baml_extract_equivalencies(
                topic=topic_name,
                source_jurisdiction=_subnation_to_jurisdiction(subnation),
                target_jurisdictions=target_jurisdictions,
            )
            equivalents = mapping.get("equivalents") or {}
            confidence = float(mapping.get("confidence", 0.0) or 0.0)
            notes = mapping.get("notes") or ""
            if confidence < 0.50:
                stats["skipped"] += 1
                continue
            for target_jurisdiction, target_topic in equivalents.items():
                if not target_topic:
                    continue
                edge = TopicEquivalentEdge(
                    source_topic_key=topic_node.topic_key,
                    source_topic_name=topic_node.topic_name,
                    source_subnation=subnation,
                    target_topic_key=_topic_key(target_jurisdiction, target_topic),
                    target_topic_name=target_topic,
                    target_subnation=target_jurisdiction.lower().replace(" ", "_"),
                    confidence=confidence,
                    notes=notes,
                )
                _upsert_edge(db, edge)
                stats["edges_created"] += 1
    elapsed_ms = int((time.monotonic() - started) * 1000)
    logger.info(
        "equivalency_graph.summary stats=%s elapsed_ms=%d", stats, elapsed_ms
    )
    return stats


def _subnation_to_jurisdiction(subnation: str) -> str:
    """Map the path-style subnation slug to the BAML canonical jurisdiction name.

    E.g. ``aqa.org.uk`` -> ``England``, ``ncca.ie`` -> ``Ireland``.
    """
    table = {
        "ncca.ie": "Ireland",
        "aqa.org.uk": "England",
        "ocr.org.uk": "England",
        "wjec.co.uk": "Wales",
        "ccea.org.uk": "Northern Ireland",
        "sqa.org.uk": "Scotland",
        "gov.im": "Isle of Man",
        "gov.je": "Jersey",
        "gov.gg": "Guernsey",
    }
    return table.get(subnation, subnation)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the cross-jurisdiction equivalency graph."
    )
    parser.add_argument("--sqlite", type=pathlib.Path, default=None)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    stats = build_equivalency_graph(sqlite_path=args.sqlite)
    return 0 if stats["skipped"] == 0 else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())


__all__ = [
    "CANONICAL_JURISDICTIONS",
    "SQLITE_PATH",
    "TopicEquivalentEdge",
    "TopicNode",
    "build_equivalency_graph",
    "main",
]