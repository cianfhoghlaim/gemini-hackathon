"""gemini_hackathon.knowledge_graph.hybrid_search — Firestore/Vertex hybrid search.

Phase 6 of the GCP-first refactor. Was: LanceDB (vector) + FalkorDB
(graph) — both stub-only (`_vector_search`/`_graph_search` were `return
[]` with a docstring describing the intended real implementation, never
written). Now: the Phase 2 `VectorTarget` (Firestore `FindNearest` /
Vertex AI Vector Search) for vector search + the Phase 6
`FirestoreSkillGraph`'s node/edge collections for graph search — both
genuinely implemented, not stubs.

`content_type` values are education-centric:
  - `curriculum_unit` — JC / LC / Primary / Early Years / Tertiary
  - `learning_outcome` — a NCCA learning outcome (from BAML extract)
  - `marking_scheme` — a LC marking scheme row
  - `policy_citation` — a citation from one of the 5 NCCA policy PDFs (W2)
  - `formative_exit_card` — a formative assessment exit card
  - `certificate` — a generated LC/JC certificate (W14)
  - `subject_specialist` — a per-subject ADK agent (W7)

Search modes are unchanged (VECTOR / GRAPH / HYBRID).

Honesty note on `_graph_search`: Firestore has no full-text search index,
so the graph path does a substring match over node descriptions rather
than a real query-language traversal (the FalkorDB stub's docstring
described `graph_client.cypher("MATCH ... WHERE n.text CONTAINS $q")` —
Firestore has no Cypher equivalent). A real deployment wanting proper
full-text graph search should sit a search index (Vertex AI Search,
Algolia, or Typesense) in front of the `skillNodes` collection; this
module's substring match is a working placeholder, not a permanent design.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class SearchMode(str, Enum):
    """Search strategy modes."""

    VECTOR = "vector"
    GRAPH = "graph"
    HYBRID = "hybrid"


class ContentType(str, Enum):
    """The education-system content types indexed by the hybrid search."""

    CURRICULUM_UNIT = "curriculum_unit"
    LEARNING_OUTCOME = "learning_outcome"
    MARKING_SCHEME = "marking_scheme"
    POLICY_CITATION = "policy_citation"
    FORMATIVE_EXIT_CARD = "formative_exit_card"
    CERTIFICATE = "certificate"
    SUBJECT_SPECIALIST = "subject_specialist"


class SearchResult(BaseModel):
    """Unified search result."""

    id: str
    content_type: ContentType
    title: str
    content: str
    score: float
    source: str  # "vector", "graph", or "hybrid"
    metadata: dict = Field(default_factory=dict)
    related_entities: list[str] = Field(default_factory=list)


class HybridSearchConfig(BaseModel):
    """Configuration for hybrid search."""

    vector_weight: float = 0.6
    graph_weight: float = 0.4
    max_results: int = 20
    min_score: float = 0.1
    include_relationships: bool = True
    relationship_depth: int = 2


@dataclass
class HybridSearchEngine:
    """Hybrid search engine combining vector and graph search.

    Uses:
    - The Phase 2 `VectorTarget` for vector similarity (Firestore
      `FindNearest` by default, or Vertex AI Vector Search via
      `VECTOR_BACKEND=vertex`) — `gemini-embedding-001`, 1536-dim.
    - The Phase 6 `FirestoreSkillGraph`'s `skillNodes`/`skillEdges`
      collections for graph traversal (substring match — see the module
      docstring's honesty note).

    `lance_uri` is kept as a constructor parameter for backward-compatible
    call sites but is unused (no LanceDB dependency remains); prefer
    omitting it in new code.
    """

    lance_uri: str = ""
    graph_client: Any | None = None
    vector_table_name: str = "biep_hybrid_search_chunks"

    def __post_init__(self):
        from cocoindex_flows._shared._vector_target import get_vector_target

        try:
            self._vector_target = get_vector_target()
        except Exception:
            logger.exception("HybridSearchEngine: vector target init failed")
            self._vector_target = None

        if self.graph_client is None:
            from gemini_hackathon.ledger.backends.firestore_graph import FirestoreSkillGraph

            self.graph_client = FirestoreSkillGraph(project_id=os.environ.get("GCP_PROJECT_ID"))

    async def search(
        self,
        query: str,
        mode: SearchMode = SearchMode.HYBRID,
        content_types: list[ContentType] | None = None,
        config: HybridSearchConfig | None = None,
    ) -> list[SearchResult]:
        """Perform hybrid search across the British Isles education corpus.

        Args:
            query: Search query text (e.g. "What are the JC Science strands?").
            mode: Search strategy (vector, graph, or hybrid).
            content_types: Optional filter to specific content types.
            config: Optional search configuration.

        Returns:
            List of `SearchResult` objects ranked by relevance.
        """
        config = config or HybridSearchConfig()
        results: list[SearchResult] = []

        if mode in (SearchMode.VECTOR, SearchMode.HYBRID) and self._vector_target is not None:
            results.extend(await self._vector_search(query, content_types, config))

        if mode in (SearchMode.GRAPH, SearchMode.HYBRID) and self.graph_client is not None:
            results.extend(await self._graph_search(query, content_types, config))

        if mode == SearchMode.HYBRID and len(results) > 0:
            results = self._reciprocal_rank_fusion(results)

        results = [r for r in results if r.score >= config.min_score]
        return results[: config.max_results]

    async def _vector_search(
        self,
        query: str,
        content_types: list[ContentType] | None,
        config: HybridSearchConfig,
    ) -> list[SearchResult]:
        """Vector similarity search via the `VectorTarget`."""
        from cocoindex_flows._shared._vertex_embedder import VertexEmbedder

        embedder = VertexEmbedder()
        if not embedder.available:
            logger.warning("_vector_search: VertexEmbedder unavailable, returning no vector results")
            return []

        query_vector = await embedder.embed_query(query)
        matches = await self._vector_target.find_nearest(
            self.vector_table_name, query_vector, k=config.max_results
        )
        results = []
        for m in matches:
            payload = m.payload or {}
            content_type_str = payload.get("content_type", ContentType.CURRICULUM_UNIT.value)
            try:
                content_type = ContentType(content_type_str)
            except ValueError:
                content_type = ContentType.CURRICULUM_UNIT
            if content_types and content_type not in content_types:
                continue
            results.append(
                SearchResult(
                    id=m.id,
                    content_type=content_type,
                    title=payload.get("title", payload.get("source_file", m.id)),
                    content=payload.get("text", ""),
                    score=m.score,
                    source="vector",
                    metadata=payload,
                )
            )
        return results

    async def _graph_search(
        self,
        query: str,
        content_types: list[ContentType] | None,
        config: HybridSearchConfig,
    ) -> list[SearchResult]:
        """Graph traversal via `FirestoreSkillGraph` (substring match over
        node descriptions — see the module docstring's honesty note)."""
        graph = self.graph_client.get_full_graph()
        query_lower = query.lower()
        results = []
        for node in graph.get("nodes", []):
            description = node.get("description", "")
            if query_lower not in description.lower():
                continue
            results.append(
                SearchResult(
                    id=node["id"],
                    content_type=ContentType.LEARNING_OUTCOME,
                    title=node.get("learning_outcome_code", node["id"]),
                    content=description,
                    score=0.5,  # substring match — a fixed confidence, not a graded rank
                    source="graph",
                    metadata={"subject_slug": node.get("subject_slug", "")},
                    related_entities=node.get("contributes_to", []),
                )
            )
            if len(results) >= config.max_results:
                break
        return results

    def _reciprocal_rank_fusion(
        self, results: list[SearchResult], k: int = 60
    ) -> list[SearchResult]:
        """Reciprocal rank fusion (RRF) — combine vector + graph ranks.

        Per Cormack et al. 2009.
        """
        scores: dict[str, float] = {}
        seen: dict[str, SearchResult] = {}
        for rank, r in enumerate(results, start=1):
            key = f"{r.content_type.value}:{r.id}"
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
            seen[key] = r
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        return [
            SearchResult(
                id=seen[k].id,
                content_type=seen[k].content_type,
                title=seen[k].title,
                content=seen[k].content,
                score=score,
                source="hybrid",
                metadata=seen[k].metadata,
                related_entities=seen[k].related_entities,
            )
            for k, score in ranked
        ]


__all__ = [
    "ContentType",
    "HybridSearchConfig",
    "HybridSearchEngine",
    "SearchMode",
    "SearchResult",
]
