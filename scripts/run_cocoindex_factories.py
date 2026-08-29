"""scripts.run_cocoindex_factories — the `embed-index` Cloud Run Job entrypoint.

Phase 7 of the GCP-first refactor. Runs every CocoIndex v1 App built by
`cocoindex_flows._factory.four_stage` (114 LC/JC/GCSE/A-Level Apps) and
`cocoindex_flows._factory.bi_jurisdiction` (8 British Isles jurisdiction
Apps) against the corpus `dlt_pipelines.corpus_downloader` fetched.

Calls each App's underlying async main callable directly via the
`APP_MAINS` registry rather than going through CocoIndex's own
App-invocation CLI/runtime — that surface (`cocoindex update <module>`
per the cianfhoghlaim skill docs, or a `coco.App.run()`-shaped Python API)
was never installed or verified against a real environment in this
refactor, so this script does not guess at its contract. `APP_MAINS`
gives a known-safe direct call path instead (see
`cocoindex_flows/_factory/four_stage.py`'s `_build_app` docstring).

Runs Apps sequentially with per-App error isolation (one App's failure —
e.g. a jurisdiction with no ingested corpus yet, like most of the crown
dependencies — must not abort the other 121 Apps).

Usage:
    python -m scripts.run_cocoindex_factories
    python -m scripts.run_cocoindex_factories --only lc_mathematics_en_embedding,jc_english_en_embedding
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _collect_app_mains(only: set[str] | None) -> dict[str, object]:
    """Merge `APP_MAINS` from both factories, optionally filtered to `only`."""
    from cocoindex_flows._factory import bi_jurisdiction, four_stage

    combined: dict[str, object] = {**four_stage.APP_MAINS, **bi_jurisdiction.APP_MAINS}
    if only:
        combined = {name: fn for name, fn in combined.items() if name in only}
    return combined


async def _run_all(app_mains: dict[str, object]) -> tuple[int, int]:
    """Run every App main sequentially. Returns (succeeded, failed) counts."""
    succeeded = 0
    failed = 0
    for name, main_fn in app_mains.items():
        start = time.monotonic()
        try:
            await main_fn()  # type: ignore[operator]
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.info("app_run_succeeded name=%s duration_ms=%d", name, duration_ms)
            succeeded += 1
        except Exception:
            logger.exception("app_run_failed name=%s", name)
            failed += 1
    return succeeded, failed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--only",
        type=str,
        default=None,
        help="Comma-separated App names to run (default: all)",
    )
    args = parser.parse_args()

    only = set(args.only.split(",")) if args.only else None

    from cocoindex_flows._shared._lifespan import COCOINDEX_AVAILABLE

    if not COCOINDEX_AVAILABLE:
        logger.warning(
            "run_cocoindex_factories: cocoindex not installed — nothing to run "
            "(this is a graceful no-op, not a failure, matching the repo-wide "
            "COCOINDEX_AVAILABLE degrade pattern)"
        )
        return 0

    app_mains = _collect_app_mains(only)
    if not app_mains:
        logger.warning("run_cocoindex_factories: no Apps matched (only=%s)", only)
        return 0

    logger.info("run_cocoindex_factories: running %d Apps", len(app_mains))
    succeeded, failed = asyncio.run(_run_all(app_mains))
    logger.info("run_cocoindex_factories: done — succeeded=%d failed=%d", succeeded, failed)

    # Exit non-zero only if EVERY App failed (a Cloud Run Job retry should
    # kick in for a total failure; a partial failure — e.g. jurisdictions
    # with no corpus yet — is expected and shouldn't fail the whole job).
    return 1 if failed > 0 and succeeded == 0 else 0


if __name__ == "__main__":
    sys.exit(main())
