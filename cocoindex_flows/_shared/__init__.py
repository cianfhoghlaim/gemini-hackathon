"""gemini_hackathon.cocoindex_flows._shared — the CocoIndex v1 shared library.

Per the R1-R4 conformance contract:

  R1: `from .._shared import shared_lifespan, EMBEDDER, VECTOR_TARGET`
  R2: the EMBEDDER + VECTOR_TARGET constants are defined here
  R3: each embedding app uses `coco.App(coco.AppConfig(name=...))`
  R4: the mount target pattern is `target.upsert_batch([...])` against
      VECTOR_TARGET (Phase 2 of the GCP-first refactor — supersedes the
      original `lancedb.mount_table_target(LANCE_DB, ...)` pattern; LANCE_DB
      is kept only for the offline-dev / cianfhoghlaim-parity path).

See `_lifespan.py` for the canonical shared_lifespan() + EMBEDDER +
VECTOR_TARGET + LANCE_DB constants.
"""

from ._lifespan import (
    EMBED_BACKEND,
    EMBEDDER,
    LANCE_DB,
    VECTOR_BACKEND,
    VECTOR_TARGET,
    shared_lifespan,
)

__all__ = [
    "EMBEDDER",
    "EMBED_BACKEND",
    "LANCE_DB",
    "VECTOR_BACKEND",
    "VECTOR_TARGET",
    "shared_lifespan",
]
