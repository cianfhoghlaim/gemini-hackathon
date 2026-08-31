"""gemini_hackathon.ledger.backends.firestore_graph — the skill-prerequisite graph backend.

Phase 6 of the GCP-first refactor — replaces `FalkorSkillGraph`. Like
`ConvexLedger`, the original never actually connected to a live FalkorDB
instance; every method only ever touched an in-memory adjacency dict, so
this is a clean swap, not a migration.

The graph is populated from the BIEP v1 cross-subject competency master
vectors + the NCCA per-subject learning outcomes.

Nodes: Skill (per learning outcome), stored as Firestore documents in the
`skillNodes` collection.
Edges: stored as Firestore documents in the `skillEdges` collection:
  - PREREQUISITE_OF (skill -> skill)
  - ASSESSED_BY (skill -> formative_artefact)
  - UNLOCKS (mastery_event -> skill)
  - CONTRIBUTES_TO (skill -> key_competency)

Same synchronous method shape `FalkorSkillGraph` had (this class is used
from `mastery_ledger.py` without `await`, so it stays sync-first — the
`google-cloud-firestore` Python client's default `Client` is synchronous
too, so no async wrapper is needed here).

In production (`GCP_PROJECT_ID` set): writes to Firestore. In dev/offline:
falls back to the same in-memory adjacency dict the original always used.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

import structlog

from gemini_hackathon.ledger.types import SkillGraphEdge, SkillGraphNode

logger = structlog.get_logger(__name__)

try:
    from google.cloud import firestore

    FIRESTORE_AVAILABLE = True
except ImportError:
    FIRESTORE_AVAILABLE = False
    firestore = None  # type: ignore[assignment]


@dataclass
class FirestoreSkillGraph:
    """The Firestore-backed skill-prerequisite graph."""

    project_id: str | None = None

    def __post_init__(self) -> None:
        self._nodes: dict[str, SkillGraphNode] = {}
        self._edges: list[SkillGraphEdge] = []
        self._client = None
        if FIRESTORE_AVAILABLE and self.project_id:
            try:
                self._client = firestore.Client(project=self.project_id)
            except Exception:
                logger.exception(
                    "FirestoreSkillGraph: client init failed, using in-memory fallback"
                )
                self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    def upsert_node(self, node: SkillGraphNode) -> None:
        self._nodes[node.node_id] = node
        if self.available:
            try:
                self._client.collection("skillNodes").document(node.node_id).set(
                    {
                        "subject_slug": node.subject_slug,
                        "learning_outcome_code": node.learning_outcome_code,
                        "description": node.description,
                        "bloom_level": node.bloom_level,
                        "contributes_to": node.contributes_to,
                    }
                )
            except Exception:
                logger.warning(
                    "FirestoreSkillGraph.upsert_node: Firestore write failed (in-memory copy stands)"
                )

    def upsert_edge(self, edge: SkillGraphEdge) -> None:
        self._edges.append(edge)
        if self.available:
            try:
                doc_id = f"{edge.edge_type}__{edge.from_node_id}__{edge.to_node_id}"
                self._client.collection("skillEdges").document(doc_id).set(
                    {
                        "edge_type": edge.edge_type,
                        "from_node_id": edge.from_node_id,
                        "to_node_id": edge.to_node_id,
                        "weight": edge.weight,
                        "metadata": edge.metadata,
                    }
                )
            except Exception:
                logger.warning(
                    "FirestoreSkillGraph.upsert_edge: Firestore write failed (in-memory copy stands)"
                )

    def get_node(self, node_id: str) -> SkillGraphNode | None:
        return self._nodes.get(node_id)

    def get_prerequisites(self, node_id: str) -> list[SkillGraphNode]:
        """Return all skills that are prerequisites of `node_id`."""
        prereq_ids = {
            e.from_node_id
            for e in self._edges
            if e.to_node_id == node_id and e.edge_type == "PREREQUISITE_OF"
        }
        return [self._nodes[nid] for nid in prereq_ids if nid in self._nodes]

    def get_unlocks(self, node_id: str) -> list[SkillGraphNode]:
        """Return all skills that `node_id` unlocks (a mastery event)."""
        unlocked_ids = {
            e.to_node_id
            for e in self._edges
            if e.from_node_id == node_id and e.edge_type == "UNLOCKS"
        }
        return [self._nodes[nid] for nid in unlocked_ids if nid in self._nodes]

    def get_full_graph(self) -> dict:
        """Return the entire graph as a serialisable dict.

        Suitable for the editorial canvas UI + the certificate pipeline.
        Reads from the in-memory mirror (kept in sync with every
        `upsert_node`/`upsert_edge` call) rather than re-querying
        Firestore, so this stays fast and works offline too.
        """
        return {
            "nodes": [
                {
                    "id": n.node_id,
                    "subject_slug": n.subject_slug,
                    "learning_outcome_code": n.learning_outcome_code,
                    "description": n.description,
                    "bloom_level": n.bloom_level,
                    "contributes_to": n.contributes_to,
                }
                for n in self._nodes.values()
            ],
            "edges": [
                {
                    "edge_type": e.edge_type,
                    "from_node_id": e.from_node_id,
                    "to_node_id": e.to_node_id,
                    "weight": e.weight,
                    "metadata": e.metadata,
                }
                for e in self._edges
            ],
        }

    def seed_default_ireland_lc_graph(self) -> None:
        """Seed the graph with a small subset of the LC Mathematics graph.

        Demonstrates the 3 edge types + the 5 Key Competencies.
        Run automatically at construction (for dev convenience).
        """
        math_outcomes = [
            ("MA-LC-MA-1.1", "Complex numbers — addition, multiplication, modulus"),
            ("MA-LC-MA-1.2", "Complex numbers — argand diagram, polar form"),
            ("MA-LC-MA-2.1", "Proof by induction"),
            ("MA-LC-MA-2.2", "Proof by contradiction"),
            ("MA-LC-MA-3.1", "Differentiation from first principles"),
            ("MA-LC-MA-3.2", "Integration techniques"),
            ("MA-LC-MA-4.1", "Sequences and series — convergence"),
            ("MA-LC-MA-4.2", "Maclaurin series"),
        ]
        for code, desc in math_outcomes:
            self.upsert_node(
                SkillGraphNode(
                    node_id=code,
                    subject_slug="mathematics",
                    learning_outcome_code=code,
                    description=desc,
                    bloom_level="apply",
                    contributes_to=["communicating", "managing_information_and_thinking"],
                )
            )
        for prev, curr in itertools.pairwise(math_outcomes):
            self.upsert_edge(
                SkillGraphEdge(
                    edge_type="PREREQUISITE_OF",
                    from_node_id=prev[0],
                    to_node_id=curr[0],
                    weight=1.0,
                )
            )
        for prev, curr in itertools.pairwise(math_outcomes):
            self.upsert_edge(
                SkillGraphEdge(
                    edge_type="UNLOCKS",
                    from_node_id=prev[0],
                    to_node_id=curr[0],
                    weight=0.8,
                )
            )
        self.upsert_edge(
            SkillGraphEdge(
                edge_type="UNLOCKS",
                from_node_id="exit_card_MA-LC-MA-1.1",
                to_node_id="MA-LC-MA-1.1",
                weight=1.0,
                metadata={"type": "formative_exit_card"},
            )
        )


__all__ = ["FirestoreSkillGraph"]
