"""gemini_hackathon.cocoindex_flows._shared — CocoIndex v1 shared lifespan (R1-R4 conformance).

Lifted from `cianfhoghlaim/cocoindex_flows/_shared/_lifespan.py` and
adapted for the gemini_hackathon editor + CocoIndex v1 patterns.

R1: this module delegates to the shared lifespan (used via
    `from ._shared._lifespan import shared_lifespan, EMBEDDER, LANCE_DB`)
R2: the EMBEDDER + LANCE_DB constants are defined here, consumed by
    each cocoindex_flows/<ireland>/<stage>_embedding.py
R3: the app patterns in each embedding.py use
    `coco.App(coco.AppConfig(name=...))`
R4: the mount target pattern is
    `lancedb.mount_table_target(LANCE_DB, ...)`

The EMBEDDER is `BAAI/bge-m3` (multilingual 1024-dim) per the BIEP v1
spec. The LANCE_DB defaults to a local LanceDB file at
`./data/lancedb/gemini_hackathon.lance`; override with the
`LANCE_DB_URI` env var.
"""

from __future__ import annotations

# The shared LANCE_DB target URI.
# Override via the `LANCE_DB_URI` env var.
import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_LANCE_DB = str(_REPO_ROOT / "data" / "lancedb" / "gemini_hackathon.lance")

LANCE_DB: str = os.getenv("LANCE_DB_URI", _DEFAULT_LANCE_DB)
"""The canonical LanceDB URI (used as `lance.connect(LANCE_DB)`)."""


# The shared embedder model (multilingual, per the BIEP v1 spec).
# Override via the `EMBEDDING_MODEL` env var.
EMBEDDER: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
"""The canonical embedder model (BAAI/bge-m3, multilingual, 1024-dim)."""


# The shared CocoIndex lifespan (R1).
def shared_lifespan():
    """Yield the CocoIndex v1 app context.

    Mirrors the cianfhoghlaim `shared_lifespan()` factory — returns a
    context manager that the embedding apps use for `with shared_lifespan(): ...`.

    Lazy-imports CocoIndex to avoid forcing the dependency in environments
    that don't use it (the editorial canvas for example only loads the
    BAML + DLT paths).
    """
    try:
        import cocoindex as coco  # type: ignore[import-not-found]
    except ImportError as e:
        raise ImportError(
            "cocoindex is required for shared_lifespan(); install with "
            "`pip install cocoindex>=1.0,<2.0`"
        ) from e

    @coco.app()
    def _app(ctx: coco.AppContext) -> None:
        # No-op lifespan (no shared resources to load); the embedder is
        # configured per-app via `coco.AppConfig(name=..., embedder=...)`.
        return None

    return _app


__all__ = ["EMBEDDER", "LANCE_DB", "shared_lifespan"]
