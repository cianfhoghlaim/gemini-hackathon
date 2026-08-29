"""
gemini_hackathon.cocoindex_flows._shared._lifespan — Shared CocoIndex v1 lifespan.

The canonical shared lifespan for the gemini-hackathon CocoIndex flows
(the 8 NCCA LC subjects + the cross-subject competency embeddings +
the leaving-cert subject embeddings + the junior-cycle embeddings).

Lifted from cianfhoghlaim/cocoindex_flows/_shared/_lifespan.py:158
(the canonical home) and adapted for the gemini-hackathon's
GCP-first deployment (Phase 2 of the GCP-first refactor).

4 shared ContextKeys are wired via the `@coco.lifespan shared_lifespan()`
+ exposed as `shared_lifespan_ctx` (an `asynccontextmanager`) so Apps that
delegate to the shared lifespan can use it:

    EMBEDDER               — VertexEmbedder (default) or SentenceTransformer
                              (offline fallback), selected by EMBED_BACKEND.
    VECTOR_TARGET           — the canonical write/query target (NEW). Firestore
                              or Vertex AI Vector Search, selected by
                              VECTOR_BACKEND. Every App ported after Phase 2
                              writes here instead of a LanceDB table.
    LANCE_DB                — kept for offline-dev / cianfhoghlaim-parity
                              only (EMBED_BACKEND=sentence_transformers).
                              New Apps should not depend on this.
    RESOLVED_FILE_REGISTRY  — the resolved file registry (used by the Apps
                              that walk the filesystem).

Per-subject CocoIndex apps in `gemini_hackathon/cocoindex_flows/ireland/`
import from here instead of redeclaring.

Reference:
    cianfhoghlaim/cocoindex_flows/leabharlann_embedding.py:236-249 (original)
    cocoindex_flows/biep_parity/ireland_lc_factory.py (the 11-App factory)
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog

logger = structlog.get_logger(__name__)

# Canonical env-var defaults for the gemini-hackathon deployment.
#
# EMBED_BACKEND selects the embedder (Phase 2 of the GCP-first refactor):
#   "vertex"               (default) -- VertexEmbedder (gemini-embedding-001,
#                            1536-d, no torch/2GB-model in the Cloud Run image)
#   "sentence_transformers" -- the original offline BGE-M3 fallback, for dev
#                            machines / CI without GCP credentials.
EMBED_BACKEND = os.getenv("EMBED_BACKEND", "vertex").lower()

# Local DuckDB-backed LanceDB path — only consulted when
# EMBED_BACKEND=sentence_transformers AND VECTOR_BACKEND is unset (the
# fully-offline dev path). The deployed path uses `_vector_target.py`
# (Firestore / Vertex AI Vector Search) instead, selected by VECTOR_BACKEND.
LANCEDB_URI = os.getenv("LANCEDB_URI") or os.getenv("GEMINI_HACKATHON_LANCEDB_URL") or "./data/lancedb/gemini_hackathon.lance"

if EMBED_BACKEND == "vertex":
    from ._vertex_embedder import VERTEX_EMBED_DIM, VERTEX_EMBED_MODEL, VertexEmbedder

    EMBED_MODEL = os.getenv("GEMINI_HACKATHON_EMBED_MODEL") or os.getenv("EMBED_MODEL") or VERTEX_EMBED_MODEL
    EMBED_DIM = VERTEX_EMBED_DIM
else:
    VertexEmbedder = None  # type: ignore[assignment]
    EMBED_MODEL = os.getenv("GEMINI_HACKATHON_EMBED_MODEL") or os.getenv("EMBED_MODEL") or "BAAI/bge-m3"
    EMBED_DIM = 1024

# VECTOR_BACKEND selects the vector store (Phase 2). See
# `_vector_target.py` for the FirestoreVectorTarget / VertexVectorSearchTarget
# comparison. Firestore is the default (zero standing infra).
VECTOR_BACKEND = os.getenv("VECTOR_BACKEND", "firestore").lower()

from ._vector_target import VectorTarget, get_vector_target  # noqa: E402

# CocoIndex is optional — degrade gracefully if not installed.
try:
    import cocoindex as coco  # type: ignore[import-not-found]

    COCOINDEX_AVAILABLE = True
except ImportError as e:
    logger.warning("cocoindex_v1_not_available: %s", e)
    COCOINDEX_AVAILABLE = False
    coco = None  # type: ignore[assignment]

# LanceDB connector — only needed for the offline sentence_transformers
# fallback path. Importing it unconditionally would reintroduce the
# torch/2GB-model dependency this refactor removes from the default
# (EMBED_BACKEND=vertex) Cloud Run image, so it's deferred behind the
# EMBED_BACKEND check.
if COCOINDEX_AVAILABLE and EMBED_BACKEND != "vertex":
    try:
        from cocoindex.connectors import lancedb as coco_lancedb  # type: ignore[import-not-found]
        from cocoindex.ops.sentence_transformers import (  # type: ignore[import-not-found]
            SentenceTransformerEmbedder,
        )

        LANCEDB_CONNECTOR_AVAILABLE = True
    except ImportError as e:
        logger.warning("lancedb_connector_not_available: %s", e)
        LANCEDB_CONNECTOR_AVAILABLE = False
        coco_lancedb = None  # type: ignore[assignment]
        SentenceTransformerEmbedder = None  # type: ignore[assignment]
else:
    LANCEDB_CONNECTOR_AVAILABLE = False
    coco_lancedb = None  # type: ignore[assignment]
    SentenceTransformerEmbedder = None  # type: ignore[assignment]


# The 4 shared ContextKeys (per the v1 best practice — see the module
# docstring for what each one is for).
if COCOINDEX_AVAILABLE:
    EmbedderType = VertexEmbedder if EMBED_BACKEND == "vertex" else SentenceTransformerEmbedder
    EMBEDDER = coco.ContextKey[EmbedderType](  # type: ignore[index,valid-type]
        "gemini_hackathon_embedder",
        detect_change=True,
    )
    VECTOR_TARGET = coco.ContextKey[VectorTarget](  # type: ignore[index]
        "gemini_hackathon_vector_target"
    )
    LANCE_DB = (
        coco.ContextKey[coco_lancedb.LanceAsyncConnection](  # type: ignore[index]
            "gemini_hackathon_lance_db"
        )
        if LANCEDB_CONNECTOR_AVAILABLE
        else None
    )
    RESOLVED_FILE_REGISTRY = coco.ContextKey[dict](  # type: ignore[index]
        "gemini_hackathon_resolved_file_registry"
    )
else:
    LANCE_DB = None  # type: ignore[assignment]
    EMBEDDER = None  # type: ignore[assignment]
    VECTOR_TARGET = None  # type: ignore[assignment]
    RESOLVED_FILE_REGISTRY = None  # type: ignore[assignment]


if COCOINDEX_AVAILABLE:

    @coco.lifespan
    async def shared_lifespan(builder: coco.EnvironmentBuilder) -> AsyncIterator[None]:  # type: ignore[no-redef]
        """Shared lifespan for all gemini-hackathon CocoIndex Apps.

        Wires:
            1. Embedder — VertexEmbedder (default) or SentenceTransformer
               (EMBED_BACKEND=sentence_transformers)
            2. Vector target — Firestore or Vertex AI Vector Search
               (VECTOR_BACKEND); the canonical write/query destination for
               Apps ported after Phase 2
            3. LanceDB connection — offline-dev only, best-effort (a
               connection failure here must not abort the whole lifespan,
               since new Apps don't depend on it)
            4. Resolved file registry (in-memory cache)
        """
        # 1. Embedder (re-used; detect_change=True so a model swap auto-re-embeds).
        embedder = VertexEmbedder(EMBED_MODEL) if EMBED_BACKEND == "vertex" else SentenceTransformerEmbedder(EMBED_MODEL)
        builder.provide(EMBEDDER, embedder)  # type: ignore[arg-type]

        # 2. Vector target (the canonical destination — see _vector_target.py).
        builder.provide(VECTOR_TARGET, get_vector_target(backend=VECTOR_BACKEND))  # type: ignore[arg-type]

        # 3. LanceDB connection (offline-dev only; best-effort).
        if LANCE_DB is not None:
            try:
                conn = await coco_lancedb.connect_async(LANCEDB_URI)  # type: ignore[arg-type]
                builder.provide(LANCE_DB, conn)  # type: ignore[arg-type]
            except Exception:
                logger.exception("shared_lifespan: LanceDB connect failed (non-fatal, offline-dev only)")

        # 4. Resolved file registry (the in-memory cache used by `localfs.walk_dir`).
        builder.provide(RESOLVED_FILE_REGISTRY, {})  # type: ignore[arg-type]

        yield

    # `coco.lifespan` registers the provider but returns the async-generator
    # function unchanged, so it cannot be used with `async with` directly.
    # Apps that delegate to the shared lifespan use this wrapper instead.
    shared_lifespan_ctx = asynccontextmanager(shared_lifespan)
else:  # pragma: no cover
    # `shared_lifespan` itself (not just `_ctx`) must exist even when
    # CocoIndex isn't installed — `cocoindex_flows/_shared/__init__.py`
    # imports it unconditionally, and every downstream App module imports
    # `from .._shared import shared_lifespan`. Leaving this undefined here
    # made the entire package unimportable offline, contradicting the
    # graceful-degrade pattern every other symbol in this module follows.
    shared_lifespan = None  # type: ignore[assignment]
    shared_lifespan_ctx = None  # type: ignore[assignment]


__all__ = [
    "COCOINDEX_AVAILABLE",
    "EMBEDDER",
    "EMBED_BACKEND",
    "EMBED_DIM",
    "EMBED_MODEL",
    "LANCEDB_CONNECTOR_AVAILABLE",
    "LANCEDB_URI",
    "LANCE_DB",
    "RESOLVED_FILE_REGISTRY",
    "VECTOR_BACKEND",
    "VECTOR_TARGET",
    "shared_lifespan",
    "shared_lifespan_ctx",
]
