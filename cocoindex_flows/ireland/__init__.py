"""gemini_hackathon.cocoindex_flows.ireland — CocoIndex embedding apps for Ireland K-12 + LC.

Lifted from `cianfhoghlaim/cocoindex_flows/subjects/` and rewritten to
use the gemini_hackathon shared lifespan (gemini_hackathon/cocoindex_flows/_shared).

Apps:
  - lc_subject_embedding.py              — the canonical per-subject LC
    syllabus/paper/marking-scheme embed
  - junior_cycle_embedding.py            — the JC subject specifications
    + CBA + short-course embed
  - education_subject_embedding.py       — the BIEP v3 P2
    DuckLake → LanceDB voter
  - cross_subject_competency_embedding.py — the 5 NCCA Key Competencies
    × 320 mastery vectors

R1-R4 conformance (per the cianfhoghlaim CocoIndex v1 spec):
  - R1: `from .._shared import shared_lifespan`
  - R2: shared LANCE_DB + EMBEDDER
  - R3: `app = coco.App(coco.AppConfig(name=...))` at module scope
  - R4: `@coco.fn` + `lancedb.mount_table_target(LANCE_DB, ...)`

The embedder is `BAAI/bge-m3` (multilingual 1024-dim) per the BIEP v1 spec.
"""

from .lc_subject_embedding import lc_subject_app
from .junior_cycle_embedding import junior_cycle_app
from .education_subject_embedding import consume_voted_ducklake_to_lance
from .cross_subject_competency_embedding import cross_subject_competency_app


__all__ = [
    "lc_subject_app",
    "junior_cycle_app",
    "consume_voted_ducklake_to_lance",
    "cross_subject_competency_app",
]
