"""gemini_hackathon.syllabus.extractor — the SyllabusExtractor protocol.

Per the user's "BAML vs VLM comparison" ask — every extraction method
(BAML structured output, Gemini 3.5 Flash multimodal, Gemma 4 E4B-it
local, PaliGemma 2 for scanned PDFs) returns an `ExtractedSyllabus`
that conforms to the canonical LCSyllabusDocument schema from
`baml_extracts_education/stages/leaving_cycle.baml`.

Lifted + adapted from cianfhoghlaim/cocoindex_flows/biep_parity/4_stage_extraction.py
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class ExtractionMethod(str, Enum):
    """The 4 extraction methods compared in Phase 5."""

    BAML = "baml"                        # BAML ExtractCurriculumSyllabus (Phase 1.2 + Phase 4)
    VLM_GEMINI_FLASH = "vlm_gemini_flash"   # Gemini 3.5 Flash multimodal (online, primary)
    VLM_GEMMA4_E4B = "vlm_gemma4_e4b"        # google/gemma-4-E4B-it (local, llama-swap)
    VLM_PALIGEMMA2 = "vlm_paligemma2"        # google/paligemma2-3b-mix-448 (OCR specialist)


class SyllabusExtractionError(Exception):
    """Raised when an extraction method fails to produce a valid syllabus."""


@dataclass
class ExtractedSyllabus:
    """The unified extraction result (any of the 4 methods can produce this)."""

    subject: str
    language: str # "EN" | "GA" | "EN_AND_GA"
    module_topics: list[dict[str, Any]] = field(default_factory=list)
    total_learning_outcomes: int = 0
    cross_curricular: list[str] = field(default_factory=list)
    assessment_objectives: list[str] = field(default_factory=list)
    prescribed_texts: list[dict[str, Any]] = field(default_factory=list)
    formulas: list[str] = field(default_factory=list)
    extraction_method: ExtractionMethod = ExtractionMethod.BAML
    extraction_latency_ms: int = 0
    extraction_confidence: float = 0.0
    raw_response: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dict for Firestore / DuckDB persistence."""
        return {
            "subject": self.subject,
            "language": self.language,
            "module_topics": self.module_topics,
            "total_learning_outcomes": self.total_learning_outcomes,
            "cross_curricular": self.cross_curricular,
            "assessment_objectives": self.assessment_objectives,
            "prescribed_texts": self.prescribed_texts,
            "formulas": self.formulas,
            "extraction_method": self.extraction_method.value,
            "extraction_latency_ms": self.extraction_latency_ms,
            "extraction_confidence": self.extraction_confidence,
        }


class SyllabusExtractor(Protocol):
    """The protocol every extraction method implements."""

    method: ExtractionMethod

    def extract(
        self,
        *,
        subject: str,
        level: str = "scoil_sinsearach",
        language: str = "EN",
        source_pdf_path: str | None = None,
        source_pdf_url: str | None = None,
    ) -> ExtractedSyllabus: ...


__all__ = [
    "ExtractedSyllabus",
    "ExtractionMethod",
    "SyllabusExtractor",
    "SyllabusExtractionError",
]