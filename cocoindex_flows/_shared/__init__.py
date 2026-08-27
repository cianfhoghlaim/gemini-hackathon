"""gemini_hackathon.cocoindex_flows._shared — the CocoIndex v1 shared library.

Per the R1-R4 conformance contract:

  R1: `from .._shared import shared_lifespan, EMBEDDER, LANCE_DB`
  R2: the EMBEDDER + LANCE_DB constants are defined here
  R3: each embedding app uses `coco.App(coco.AppConfig(name=...))`
  R4: the mount target pattern is `lancedb.mount_table_target(LANCE_DB, ...)`

See `_lifespan.py` for the canonical shared_lifespan() + EMBEDDER + LANCE_DB
constants.
"""

from ._lifespan import (
    EMBEDDER,
    LANCE_DB,
    shared_lifespan,
)


__all__ = ["EMBEDDER", "LANCE_DB", "shared_lifespan"]
