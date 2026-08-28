"""
gemini_hackathon.cocoindex_flows._shared._lifespan — Shared CocoIndex v1 lifespan.

The canonical shared lifespan for the gemini-hackathon CocoIndex flows
(the 8 NCCA LC subjects + the cross-subject competency embeddings +
the leaving-cert subject embeddings + the junior-cycle embeddings).

Lifted from cianfhoghlaim/cocoindex_flows/_shared/_lifespan.py:158
(the canonical home) and adapted for the gemini-hackathon's
local-DuckDB-only deployment + the bge-m3 embedder.

The 3 shared ContextKeys (`LANCE_DB`, `EMBEDDER`, `RESOLVED_FILE_REGISTRY`)
are wired via the `@coco.lifespan shared_lifespan()` + exposed as
`shared_lifespan_ctx` (an `asynccontextmanager`) so Apps that
delegate to the shared lifespan can use it.

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
# Local DuckDB-backed LanceDB by default; override via
# `LANCEDB_URI=rest://...` or `GEMINI_HACKATHON_LANCEDB_URL=...`.
LANCEDB_URI = os.getenv("LANCEDB_URI") or os.getenv("GEMINI_HACKATHON_LANCEDB_URL") or "./data/lancedb/gemini_hackathon.lance"
EMBED_MODEL = os.getenv("GEMINI_HACKATHON_EMBED_MODEL") or os.getenv("EMBED_MODEL") or "BAAI/bge-m3"
EMBED_DIM = 1024

# CocoIndex is optional — degrade gracefully if not installed.
try:
    import cocoindex as coco  # type: ignore[import-not-found]
    from cocoindex.connectors import lancedb as coco_lancedb  # type: ignore[import-not-found]
    from cocoindex.ops.sentence_transformers import (  # type: ignore[import-not-found]
        SentenceTransformerEmbedder,
    )

    COCOINDEX_AVAILABLE = True
except ImportError as e:
    logger.warning("cocoindex_v1_not_available: %s", e)
    COCOINDEX_AVAILABLE = False
    coco = None  # type: ignore[assignment]
    coco_lancedb = None  # type: ignore[assignment]
    SentenceTransformerEmbedder = None  # type: ignore[assignment]


# The 3 shared ContextKeys (per the v1 best practice).
#
# LANCE_DB              — the LanceDB async connection. Shared across all Apps
#                         so we have 1 LMDB state file, 1 embedder, 1 connection.
# EMBEDDER              — the SentenceTransformer embedder. detect_change=True
#                         so a model swap auto-re-embeds.
# RESOLVED_FILE_REGISTRY — the resolved file registry (used by the Apps
#                         that walk the filesystem).
if COCOINDEX_AVAILABLE:
    LANCE_DB = coco.ContextKey[coco_lancedb.LanceAsyncConnection](  # type: ignore[index]
        "gemini_hackathon_lance_db"
    )
    EMBEDDER = coco.ContextKey[SentenceTransformerEmbedder](  # type: ignore[index]
        "gemini_hackathon_embedder",
        detect_change=True,
    )
    RESOLVED_FILE_REGISTRY = coco.ContextKey[dict](  # type: ignore[index]
        "gemini_hackathon_resolved_file_registry"
    )
else:
    LANCE_DB = None  # type: ignore[assignment]
    EMBEDDER = None  # type: ignore[assignment]
    RESOLVED_FILE_REGISTRY = None  # type: ignore[assignment]


if COCOINDEX_AVAILABLE:

    @coco.lifespan
    async def shared_lifespan(builder: coco.EnvironmentBuilder) -> AsyncIterator[None]:  # type: ignore[no-redef]
        """Shared lifespan for all gemini-hackathon CocoIndex Apps.

        Wires:
            1. LanceDB connection (shared)
            2. SentenceTransformer embedder (bge-m3, 1024-dim)
            3. Resolved file registry (in-memory cache)
        """
        # 1. LanceDB connection (shared).
        conn = await coco_lancedb.connect_async(LANCEDB_URI)  # type: ignore[arg-type]
        builder.provide(LANCE_DB, conn)  # type: ignore[arg-type]

        # 2. Embedder (re-used; detect_change=True so a model swap auto-re-embeds).
        builder.provide(  # type: ignore[arg-type]
            EMBEDDER,
            SentenceTransformerEmbedder(EMBED_MODEL),
        )

        # 3. Resolved file registry (the in-memory cache used by `localfs.walk_dir`).
        builder.provide(RESOLVED_FILE_REGISTRY, {})  # type: ignore[arg-type]

        yield

    # `coco.lifespan` registers the provider but returns the async-generator
    # function unchanged, so it cannot be used with `async with` directly.
    # Apps that delegate to the shared lifespan use this wrapper instead.
    shared_lifespan_ctx = asynccontextmanager(shared_lifespan)
else:  # pragma: no cover
    shared_lifespan_ctx = None  # type: ignore[assignment]


__all__ = [
    "COCOINDEX_AVAILABLE",
    "LANCE_DB",
    "EMBEDDER",
    "RESOLVED_FILE_REGISTRY",
    "LANCEDB_URI",
    "EMBED_MODEL",
    "EMBED_DIM",
    "shared_lifespan",
    "shared_lifespan_ctx",
]