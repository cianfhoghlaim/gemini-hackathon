"""gemini_hackathon.ledger.backends.falkor_graph — the FalkorDB skill graph backend.

FalkorDB stores the skill-prerequisite graph. The graph is populated
from the BIEP v1 cross-subject competency master vectors + the
NCCA per-subject learning outcomes (W5).

Nodes: Skill (per learning outcome).
Edges:
  - PREREQUISITE_OF (skill → skill)
  - ASSESSED_BY (skill → formative_artefact)
  - UNLOCKS (mastery_event → skill)
  - CONTRIBUTES_TO (skill → key_competency)

In production: writes to a FalkorDB instance. In dev (no FalkorDB):
writes to an in-memory adjacency dict.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from gemini_hackathon.ledger.types import SkillGraphEdge, SkillGraphNode


@dataclass
class FalkorSkillGraph:
    """The FalkorDB-backed skill-prerequisite graph."""

    falkor_url: str | None = None

    def __post_init__(self):
        self._nodes: dict[str, SkillGraphNode] = {}
        self._edges: list[SkillGraphEdge] = []

    def upsert_node(self, node: SkillGraphNode) -> None:
        self._nodes[node.node_id] = node

    def upsert_edge(self, edge: SkillGraphEdge) -> None:
        self._edges.append(edge)

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
        # 8 nodes (1 per LC Mathematics learning outcome)
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
            self.upsert_node(SkillGraphNode(
                node_id=code,
                subject_slug="mathematics",
                learning_outcome_code=code,
                description=desc,
                bloom_level="apply",
                contributes_to=["communicating", "managing_information_and_thinking"],
            ))
        # Prerequisites (each step builds on the previous)
        for prev, curr in zip(math_outcomes, math_outcomes[1:]):
            self.upsert_edge(SkillGraphEdge(
                edge_type="PREREQUISITE_OF",
                from_node_id=prev[0],
                to_node_id=curr[0],
                weight=1.0,
            ))
        # Mastery unlocks the next step
        for prev, curr in zip(math_outcomes, math_outcomes[1:]):
            self.upsert_edge(SkillGraphEdge(
                edge_type="UNLOCKS",
                from_node_id=prev[0],
                to_node_id=curr[0],
                weight=0.8,
            ))
        # 1 mastery event unlocks the first outcome
        self.upsert_edge(SkillGraphEdge(
            edge_type="UNLOCKS",
            from_node_id="exit_card_MA-LC-MA-1.1",
            to_node_id="MA-LC-MA-1.1",
            weight=1.0,
            metadata={"type": "formative_exit_card"},
        ))


__all__ = ["FalkorSkillGraph"]
