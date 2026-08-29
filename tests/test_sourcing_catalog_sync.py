"""test_sourcing_catalog_sync.py — guard the catalog duplication.

Per the audit trail in `docs/ideas/sourcing_integration.md` (Stream S.6),
the sourcing pipeline's `pipeline.py` duplicates `KNOWN_OFFICIAL_URLS`
from `gemini_hackathon/dlt_pipelines/official_doc_fetcher.py` because the
source module re-imports `dlt` at the top of its `__init__.py`, which
fails offline. This test asserts the two stay in sync — when the canonical
catalog changes, this test must be updated too.

Skipped when `dlt` isn't importable (the canonical source module fails to
import, exactly the case this duplication was created for).
"""
from __future__ import annotations

import pytest


def test_catalog_urls_in_sync():
    """The inlined `KNOWN_OFFICIAL_URLS` must equal the canonical one."""
    try:
        import dlt  # noqa: F401 — required for the canonical source module
        from gemini_hackathon.dlt_pipelines.official_doc_fetcher import KNOWN_OFFICIAL_URLS as canonical
    except ImportError:
        pytest.skip("dlt not importable; canonical catalog unreachable (this is exactly why we duplicated)")

    from gemini_hackathon.journey.sourcing.pipeline import KNOWN_OFFICIAL_URLS as inlined

    assert canonical == inlined, (
        "Catalog drift between "
        "gemini_hackathon.dlt_pipelines.official_doc_fetcher.KNOWN_OFFICIAL_URLS and "
        "gemini_hackathon.journey.sourcing.pipeline.KNOWN_OFFICIAL_URLS — "
        "update BOTH when the catalog changes."
    )
