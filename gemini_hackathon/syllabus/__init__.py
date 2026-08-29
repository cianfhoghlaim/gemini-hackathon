"""gemini_hackathon.syllabus — the syllabus extraction pipeline (Phase 5).

Per the user's "BAML vs VLM comparison + per-subject asset schema":
  - extractor.py        — Protocol SyllabusExtractor.extract(source_url, subject, level) -> CurriculumUnit
  - baml_extractor.py   — Wraps the lifted BAML ExtractCurriculumSyllabus (Phase 1.2 + Phase 4)
  - vlm_extractor.py    — Wraps Gemini 3.5 Flash multimodal PDF→JSON
  - comparison.py       — Orchestrator: runs both, applies rubric, persists results
  - rubric.py           — Jaccard + LO coverage + schema-conformance + LLM-judge
  - per_topic_schema.py — CurriculumUnit.learning_outcomes[i] -> CurriculumConcept -> AssetRequest
  - storage.py          — Writes to DuckDB + Firestore

The 8 active NCCA LC subjects × 4 extraction methods (BAML, VLM Gemini,
VLM Gemma-4-E4B-it, VLM PaliGemma2) = 32 comparison cells.

Plus the per-topic asset schema is the input to the Phase 6
7-backend asset comparison pipeline (40 topics × 7 backends = 280 cells).

Lifted + adapted from cianfhoghlaim/cocoindex_flows/biep_parity/baml_cocoindex_integration.py
+ cianfhoghlaim/cocoindex_flows/biep_parity/4_stage_extraction.py
"""

from .baml_extractor import BAMLSyllabusExtractor
from .comparison import SyllabusComparison, run_extraction_comparison
from .extractor import (
    ExtractedSyllabus,
    ExtractionMethod,
    SyllabusExtractor,
    SyllabusExtractionError,
)
from .per_topic_schema import (
    ASSET_REQUEST_BY_SUBJECT,
    CurriculumConcept,
    build_curriculum_concepts,
    to_asset_request,
)
from .rubric import (
    ExtractionRubric,
    compute_jaccard,
    compute_lo_coverage,
    compute_pydantic_conformance,
    llm_judge_score,
)
from .storage import (
    SYLLABUS_RESULTS_PATH,
    write_extraction_to_duckdb,
    write_extraction_to_jsonl,
)
from .vlm_extractor import (
    GeminiFlashVLMSyllabusExtractor,
    Gemma4E4BVLMSyllabusExtractor,
    PaliGemma2VLMSyllabusExtractor,
)


__all__ = [
    "ASSET_REQUEST_BY_SUBJECT",
    "BAMLSyllabusExtractor",
    "CurriculumConcept",
    "ExtractedSyllabus",
    "ExtractionMethod",
    "ExtractionRubric",
    "GeminiFlashVLMSyllabusExtractor",
    "Gemma4E4BVLMSyllabusExtractor",
    "PaliGemma2VLMSyllabusExtractor",
    "SYLLABUS_RESULTS_PATH",
    "SyllabusExtractionError",
    "SyllabusExtractor",
    "build_curriculum_concepts",
    "compute_jaccard",
    "compute_lo_coverage",
    "compute_pydantic_conformance",
    "llm_judge_score",
    "run_extraction_comparison",
    "to_asset_request",
    "write_extraction_to_duckdb",
    "write_extraction_to_jsonl",
]