"""gemini_hackathon.cocoindex_flows.ireland — CocoIndex embedding apps for Ireland K-12 + LC.

Lifted from `cianfhoghlaim/cocoindex_flows/subjects/` and rewritten to
use the gemini_hackathon shared lifespan (gemini_hackathon/cocoindex_flows/_shared).

BUGFIX (Phase 4, GCP-first refactor): this module previously imported
`lc_subject_app` from `lc_subject_embedding.py` and `junior_cycle_app`
from `junior_cycle_embedding.py` — neither name was ever defined in
either file (`lc_subject_embedding.py`'s App-construction block was
dead code behind `if COCOINDEX_AVAILABLE and False:`, and
`junior_cycle_embedding.py` exports `app`, not `junior_cycle_app`), which
made this entire package unimportable. The working per-(subject,
language) LC + JC Apps now live in `cocoindex_flows._factory.four_stage`
(99+ Apps, GCS-backed, Firestore/Vertex-Vector-Search-targeted — see that
module's docstring for why it replaced the incomplete originals) and are
re-exported here for backward-compatible `from cocoindex_flows.ireland
import ...` call sites.

Apps:
  - `_factory.four_stage`                — the 114 LC + JC + GCSE +
    A-Level Apps (supersedes lc_subject_embedding.py / junior_cycle_embedding.py)
  - education_subject_embedding.py       — the BIEP v3 P2
    DuckLake -> LanceDB voter
  - cross_subject_competency_embedding.py — the 5 NCCA Key Competencies
    x 320 mastery vectors

R1-R4 conformance (per the cianfhoghlaim CocoIndex v1 spec):
  - R1: `from .._shared import shared_lifespan`
  - R2: shared EMBEDDER + VECTOR_TARGET (LANCE_DB kept offline-dev only)
  - R3: `app = coco.App(coco.AppConfig(name=...))` at module scope
  - R4: `@coco.fn` + `VECTOR_TARGET.upsert_batch(...)`

The embedder is Vertex AI `gemini-embedding-001` (1536-dim) by default —
see `EMBED_BACKEND` in `_shared/_lifespan.py`.
"""

from .._factory.four_stage import get_4_stage_manifest
from .cross_subject_competency_embedding import cross_subject_competency_app
from .education_subject_embedding import consume_voted_ducklake_to_lance

__all__ = [
    "consume_voted_ducklake_to_lance",
    "cross_subject_competency_app",
    "get_4_stage_manifest",
]
