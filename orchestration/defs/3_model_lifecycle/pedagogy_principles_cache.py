"""orchestration.defs.3_model_lifecycle.pedagogy_principles_cache — the cache asset.

Phase 2 of the OpenSpec change
[`2026-08-31-pedagogy-overlay-renderer-v1`](../../../../openspec/changes/2026-08-31-pedagogy-overlay-renderer-v1/proposal.md).

Wraps the CocoIndex `pedagogy_cache` module
(`cocoindex_flows/uk_ncce/pedagogy_cache.py`) as a single Dagster asset.
The asset is *idempotent* — re-runs return instantly when the
`pedagogy_principles.pdf` sha256 hasn't changed, exactly mirroring the
underlying `@coco.fn(memo=True)` cache semantics.

Sibling assets (`pedagogy_overlay.py` — Phase 3) depend on this asset;
the cross-walk assets in `uk_ncce_learning_graph_equivalencies.py` do
NOT depend on it (the pedagogy overlay is independent of the cell-level
equivalency graph).
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

try:
    from dagster import AssetExecutionContext, asset
except ImportError:
    AssetExecutionContext = None  # type: ignore[assignment]
    asset = None  # type: ignore[assignment]
    logger.warning(
        "pedagogy_principles_cache: dagster not installed; running as a plain Python module only."
    )


def _build_asset() -> Any:
    """Build the `uk_ncce_pedagogy_cache` Dagster asset."""
    if asset is None:
        return None

    @asset(
        description=(
            "Single CocoIndex-driven asset that owns the "
            "`data/bi_ep/syllabi_md/uk_ncce/pedagogy_principles.json` "
            "disk cache + the Cognee `gh_cognee_pedagogy_dataset` "
            "upload. Re-runs are O(1) sha256 cache hits."
        ),
        group_name="3_model_lifecycle",
    )
    def _uk_ncce_pedagogy_cache(context: Any) -> dict[str, Any]:
        started = time.monotonic()
        try:
            from cocoindex_flows.uk_ncce.pedagogy_cache import (  # type: ignore[import-not-found]
                build_pedagogy_cache,
            )

            stats = build_pedagogy_cache()
        except ImportError:
            logger.warning("uk_ncce_pedagogy_cache: cocoindex_flows module not available — no-op.")
            stats = {
                "extracted": False,
                "from_cache": False,
                "n_principles": 0,
                "source_pdf_sha256": "",
                "cognee_uploaded": False,
                "source": "live_pdf",
            }
        if context is not None:
            context.add_metadata(stats)
        stats = dict(stats)
        stats["elapsed_ms"] = int((time.monotonic() - started) * 1000)
        return stats

    return _uk_ncce_pedagogy_cache


_asset = _build_asset()
if _asset is not None:
    globals()["uk_ncce_pedagogy_cache"] = _asset


__all__: list[str] = []


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(0)
