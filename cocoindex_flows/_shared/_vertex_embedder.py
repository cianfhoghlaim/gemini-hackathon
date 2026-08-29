"""cocoindex_flows._shared._vertex_embedder — the Vertex AI embedding backend.

Phase 2 of the GCP-first refactor. Drop-in replacement for
`cocoindex.ops.sentence_transformers.SentenceTransformerEmbedder` at every
CocoIndex v1 App call site in this repo — every call site uses the shape
``embedding = await embedder.embed(text)`` (see
`cocoindex_flows/ireland/*.py` and the lifted `biep_parity/bi_factory.py`
factory), so `VertexEmbedder` only needs to satisfy that one async method
to be a transparent swap behind the `EMBEDDER` ContextKey.

Uses `gemini-embedding-001` via the Vertex AI `TextEmbeddingModel` SDK
(`google-cloud-aiplatform`), the same Google model the `TEXT_MODELS`
registry elsewhere in this repo already names. Two deliberate choices:

1. **`output_dimensionality=1536`** (not the model's native 3072). Firestore
   vector fields cap at 2048 dimensions
   (https://firebase.google.com/docs/firestore/vector-search), and using
   the same 1536-d vectors for both `FirestoreVectorTarget` and
   `VertexVectorSearchTarget` (see `_vector_target.py`) means the two
   backends index byte-identical embeddings — a fair head-to-head
   benchmark instead of two unrelated systems.
2. **Task-type aware** — `RETRIEVAL_DOCUMENT` for indexing, `RETRIEVAL_QUERY`
   for search. Matching task types is worth several points of recall on
   Vertex's retrieval-tuned embedding models; every prior CocoIndex App in
   this repo embedded queries and documents identically, which silently
   left recall on the table.

Falls back gracefully (`VERTEX_EMBEDDER_AVAILABLE = False`) when
`google-cloud-aiplatform` is not installed or `GCP_PROJECT_ID` is unset —
matching the `COCOINDEX_AVAILABLE` degrade pattern used throughout
`cocoindex_flows/`. `_lifespan.py`'s `EMBED_BACKEND` switch selects between
this and the offline `sentence_transformers` fallback.
"""
from __future__ import annotations

import os
from typing import Literal

import structlog

logger = structlog.get_logger(__name__)

#: Native output dimensionality of `gemini-embedding-001` is 3072; capped
#: to Firestore's 2048-dim vector-field limit, and rounded down to a
#: Matryoshka-friendly value that both backends share.
VERTEX_EMBED_DIM = 1536

#: The canonical Vertex embedding model. Overridable for experimentation
#: (e.g. `text-multilingual-embedding-002` for the EN/GA bilingual corpus)
#: via `VERTEX_EMBED_MODEL`.
VERTEX_EMBED_MODEL = os.environ.get("VERTEX_EMBED_MODEL", "gemini-embedding-001")

TaskType = Literal["RETRIEVAL_DOCUMENT", "RETRIEVAL_QUERY", "SEMANTIC_SIMILARITY", "CLASSIFICATION"]

try:
    import vertexai
    from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel

    VERTEX_EMBEDDER_AVAILABLE = True
except ImportError as exc:  # pragma: no cover - defensive, mirrors _lifespan.py
    logger.warning("vertex_embedder_not_available: %s", exc)
    VERTEX_EMBEDDER_AVAILABLE = False
    vertexai = None  # type: ignore[assignment]
    TextEmbeddingInput = None  # type: ignore[assignment,misc]
    TextEmbeddingModel = None  # type: ignore[assignment,misc]


class VertexEmbedder:
    """The Vertex AI `gemini-embedding-001` embedder.

    Satisfies the same async-`.embed(text) -> list[float]` interface every
    CocoIndex v1 App in this repo already calls, so it is a transparent
    swap for `SentenceTransformerEmbedder(EMBED_MODEL)` behind the shared
    `EMBEDDER` ContextKey in `_lifespan.py`.

    Not thread-safe across event loops; one instance per process is the
    canonical usage (matches the shared-lifespan singleton pattern).
    """

    def __init__(
        self,
        model_name: str = VERTEX_EMBED_MODEL,
        *,
        output_dimensionality: int = VERTEX_EMBED_DIM,
        project: str | None = None,
        location: str | None = None,
    ) -> None:
        self.model_name = model_name
        self.output_dimensionality = output_dimensionality
        self._project = project or os.environ.get("GCP_PROJECT_ID")
        self._location = location or os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        self._model: TextEmbeddingModel | None = None  # type: ignore[valid-type]

        if not VERTEX_EMBEDDER_AVAILABLE:
            logger.warning("VertexEmbedder constructed without google-cloud-aiplatform installed")
            return
        if not self._project:
            logger.warning("VertexEmbedder constructed without GCP_PROJECT_ID set")
            return

        vertexai.init(project=self._project, location=self._location)
        self._model = TextEmbeddingModel.from_pretrained(self.model_name)

    @property
    def available(self) -> bool:
        return self._model is not None

    async def embed(self, text: str, *, task_type: TaskType = "RETRIEVAL_DOCUMENT") -> list[float]:
        """Embed one string. Returns a zero-vector on any failure (never
        raises into a CocoIndex `@coco.fn` — one bad row must not abort a
        batch `coco.map(...)` run).
        """
        result = await self.embed_many([text], task_type=task_type)
        return result[0]

    async def embed_many(
        self, texts: list[str], *, task_type: TaskType = "RETRIEVAL_DOCUMENT"
    ) -> list[list[float]]:
        """Embed a batch of strings in one Vertex AI call (max 250/request
        per the API limit — callers with larger batches should chunk).

        Returns one zero-vector per input on failure, preserving 1:1
        input/output alignment so callers can zip against the source rows
        without special-casing errors.
        """
        if not self.available:
            logger.warning("VertexEmbedder.embed_many: unavailable, returning zero-vectors")
            return [[0.0] * self.output_dimensionality for _ in texts]

        inputs = [TextEmbeddingInput(text, task_type) for text in texts]
        try:
            embeddings = self._model.get_embeddings(  # type: ignore[union-attr]
                inputs, output_dimensionality=self.output_dimensionality
            )
        except Exception:
            logger.exception("VertexEmbedder.embed_many: Vertex AI call failed")
            return [[0.0] * self.output_dimensionality for _ in texts]
        return [e.values for e in embeddings]

    async def embed_query(self, text: str) -> list[float]:
        """Convenience: embed with `RETRIEVAL_QUERY` task type (search-side)."""
        return await self.embed(text, task_type="RETRIEVAL_QUERY")


__all__ = [
    "VERTEX_EMBEDDER_AVAILABLE",
    "VERTEX_EMBED_DIM",
    "VERTEX_EMBED_MODEL",
    "VertexEmbedder",
]
