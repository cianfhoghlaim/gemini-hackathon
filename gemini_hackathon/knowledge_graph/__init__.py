"""gemini_hackathon.knowledge_graph.hybrid_search — FalkorDB + LanceDB hybrid search.

Lifted from `cianfhoghlaim/docs/sruth/tuath/knowledge_graph/hybrid_search.py`
and adapted for the British Isles education system.

`content_type` values are now education-centric (not mythology-centric):
  - `curriculum_unit` — JC / LC / Primary / Early Years / Tertiary
  - `learning_outcome` — a NCCA learning outcome (from BAML extract)
  - `marking_scheme` — a LC marking scheme row
  - `policy_citation` — a citation from one of the 5 NCCA policy PDFs (W2)
  - `formative_exit_card` — a formative assessment exit card
  - `certificate` — a generated LC/JC certificate (W14)
  - `subject_specialist` — a per-subject ADK agent (W7)

Search modes are unchanged (VECTOR / GRAPH / HYBRID).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class SearchMode(str, Enum):
    """Search strategy modes."""

    VECTOR = "vector"
    GRAPH = "graph"
    HYBRID = "hybrid"


class ContentType(str, Enum):
    """The education-system content types indexed by the hybrid search.

    Replaces the Celtic-mythology content types from the sruth/tuath
    original (`curriculum, mythology, character, story, location`).
    """

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
    - LanceDB for vector similarity (BAAI/bge-m3 multilingual embeddings,
      1024-dim per the BIEP v1 spec)
    - FalkorDB for graph traversal (the skill-prerequisite + key-competency
      graph from W9)
    """

    lance_uri: str
    graph_client: Any | None = None

    def __post_init__(self):
        """Lazy-import LanceDB at construction time (defer hard dep)."""
        try:
            import lancedb

            self._lance_db = lancedb.connect(self.lance_uri)
        except ImportError:
            self._lance_db = None

    async def search(
        self,
        query: str,
        mode: SearchMode = SearchMode.HYBRID,
        content_types: Optional[list[ContentType]] = None,
        config: Optional[HybridSearchConfig] = None,
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

        # Vector search (LanceDB)
        if mode in (SearchMode.VECTOR, SearchMode.HYBRID) and self._lance_db is not None:
            results.extend(await self._vector_search(query, content_types, config))

        # Graph search (FalkorDB)
        if mode in (SearchMode.GRAPH, SearchMode.HYBRID) and self.graph_client is not None:
            results.extend(await self._graph_search(query, content_types, config))

        # Reciprocal rank fusion (for HYBRID)
        if mode == SearchMode.HYBRID and len(results) > 0:
            results = self._reciprocal_rank_fusion(results)

        # Filter by min_score
        results = [r for r in results if r.score >= config.min_score]
        return results[: config.max_results]

    async def _vector_search(
        self,
        query: str,
        content_types: Optional[list[ContentType]],
        config: HybridSearchConfig,
    ) -> list[SearchResult]:
        """Vector similarity search via LanceDB.

        Stub implementation — the real implementation calls
        `lance_db.create_table("search", ...) + lance_db.search().limit(N)`.
        """
        return []

    async def _graph_search(
        self,
        query: str,
        content_types: Optional[list[ContentType]],
        config: HybridSearchConfig,
    ) -> list[SearchResult]:
        """Graph traversal via FalkorDB.

        Stub implementation — the real implementation calls
        `graph_client.cypher("MATCH (n:CurriculumUnit) WHERE n.text CONTAINS $q ...")`.
        """
        return []

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
    "SearchMode",
    "ContentType",
    "SearchResult",
    "HybridSearchConfig",
    "HybridSearchEngine",
]
