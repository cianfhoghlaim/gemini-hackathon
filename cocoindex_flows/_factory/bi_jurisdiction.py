"""cocoindex_flows._factory.bi_jurisdiction — the 8-jurisdiction BI factory.

Phase 4 of the GCP-first refactor. Ports
`cianfhoghlaim/cocoindex_flows/biep_parity/bi_factory.py`'s jurisdiction
table and factory *pattern* (that source file is one of the few in
`biep_parity/` that actually builds working `coco.App(...)` instances —
unlike `4_stage_factory.py`, see `four_stage.py`'s docstring). Rewritten
for the GCP-first substrate:

    - `localfs.walk_dir("dlt/british_isles/<slug>/education")` -> GCS/local
      corpus reader (a directory that never existed in this repo; see
      `_iter_source_texts` in `four_stage.py`, reused here)
    - `lancedb.mount_table_target(LANCE_DB, ...)` -> `VECTOR_TARGET.upsert_batch(...)`
    - `EMBEDDER.embed(...)` -> unchanged (VertexEmbedder now, by default)

The source's 8-row `JURISDICTION_CONFIG` (Ireland/Gaeilge + England + NI +
Scotland + Wales + Isle of Man + Jersey + Guernsey) maps 1:1 onto the 8
jurisdictions `dlt_pipelines/official_doc_fetcher.py` now fetches for
(Phase 3), so `jurisdiction` here is the same string as
`JURISDICTION_BOARDS.values()` there — the two Phase 3/4 pieces read the
same GCS layout.

Reference: cianfhoghlaim/cocoindex_flows/biep_parity/bi_factory.py
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

import structlog

from .._shared._lifespan import COCOINDEX_AVAILABLE, EMBEDDER, VECTOR_TARGET, shared_lifespan
from .._shared._vector_target import VectorRow
from .four_stage import _chunk_text, _iter_source_texts

logger = structlog.get_logger(__name__)

try:
    import cocoindex as coco  # type: ignore[import-not-found]
except ImportError:
    coco = None  # type: ignore[assignment]


@dataclass(frozen=True)
class BIJurisdictionConfig:
    """One British Isles jurisdiction row. `jurisdiction` matches
    `dlt_pipelines._shared.JURISDICTION_BOARDS.values()` (Phase 3) so both
    phases agree on the GCS/local corpus path.
    """

    slug: str
    jurisdiction: str  # matches JURISDICTION_BOARDS value, e.g. "Ireland"
    display_name: str
    source_subject: str  # the `subject` key under data/<jurisdiction>/<subject>/


#: The 8 British Isles jurisdictions. `source_subject="_index"` /
#: `"_curriculum"` etc. match the catalog-row subject slugs
#: `official_doc_fetcher.KNOWN_OFFICIAL_URLS` uses for jurisdictions that
#: publish framework pages rather than per-subject specs (Jersey,
#: Guernsey, Isle of Man) — see that module's Phase 3 docstring notes.
JURISDICTION_CONFIG: list[BIJurisdictionConfig] = [
    BIJurisdictionConfig("ga", "Ireland", "Gaeilge (Ireland)", "gaeilge"),
    BIJurisdictionConfig("en", "England", "England", "mathematics"),
    BIJurisdictionConfig("ni", "Northern Ireland", "Northern Ireland", "_index"),
    BIJurisdictionConfig("sct", "Scotland", "Scotland", "mathematics"),
    BIJurisdictionConfig("wls", "Wales", "Wales", "mathematics"),
    BIJurisdictionConfig("isle_of_man", "Isle of Man", "Isle of Man", "_curriculum"),
    BIJurisdictionConfig("jersey", "Jersey", "Jersey", "_key_stage_4"),
    BIJurisdictionConfig("guernsey", "Guernsey", "Guernsey", "_qualifications"),
]


def _build_jurisdiction_app(config: BIJurisdictionConfig) -> tuple[Any, Any] | tuple[None, None]:
    """Returns `(coco.App, async_main_callable)` — see `four_stage.py`'s
    `_build_app` docstring for why the callable is exposed directly
    alongside the `coco.App` object."""
    if not COCOINDEX_AVAILABLE:
        return None, None

    table_name = f"biep_bi_{config.slug}_education_chunks"

    @coco.fn(memo=True)  # type: ignore[misc]
    async def _process_source_file(filename: str, text: str) -> None:
        embedder = await coco.use_context(EMBEDDER)  # type: ignore[arg-type]
        vector_target = await coco.use_context(VECTOR_TARGET)  # type: ignore[arg-type]
        rows = []
        for chunk_index, chunk_text in enumerate(_chunk_text(text)):
            if not chunk_text.strip():
                continue
            embedding = await embedder.embed(chunk_text)
            row_id = hashlib.sha256(f"{table_name}:{filename}:{chunk_index}".encode()).hexdigest()
            rows.append(
                VectorRow(
                    id=row_id,
                    table_name=table_name,
                    vector=embedding,
                    payload={
                        "jurisdiction": config.jurisdiction,
                        "jurisdiction_slug": config.slug,
                        "source_file": filename,
                        "chunk_index": chunk_index,
                        "text": chunk_text[:2000],
                    },
                )
            )
        if rows:
            await vector_target.upsert_batch(rows)

    @coco.fn  # type: ignore[misc]
    async def _main() -> None:
        for filename, text in _iter_source_texts(config.jurisdiction, config.source_subject):
            await _process_source_file(filename, text)

    return coco.App(coco.AppConfig(name=f"{config.slug}_education_embedding"), _main), _main  # type: ignore[union-attr]


#: app_name -> the async main callable (see `four_stage.APP_MAINS`).
APP_MAINS: dict[str, Any] = {}

__all__ = ["APP_MAINS", "JURISDICTION_CONFIG", "BIJurisdictionConfig", "shared_lifespan"]

for _jurisdiction in JURISDICTION_CONFIG:
    _app_name = f"{_jurisdiction.slug}_education_embedding"
    _app, _main_fn = _build_jurisdiction_app(_jurisdiction)
    globals()[_app_name] = _app
    if _main_fn is not None:
        APP_MAINS[_app_name] = _main_fn
    __all__.append(_app_name)
