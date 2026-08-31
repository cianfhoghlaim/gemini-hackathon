"""gemini_hackathon_gradio.an_scrudu.extraction — mark scheme extraction for LC past papers.

Lifted from `sruth/spaces/an_scrudu/extraction.py` and rewritten to use
the shared `gemini_hackathon_gradio._common.baml_pydantic_bridge` and
the shared `gemini_hackathon_gradio._common.baml_client` (the
3-tier LiteLLM → Unsloth Studio → HF Inference fallback chain).

The extraction routes through:

  1. The canonical BAML function in
     `gemini_hackathon/baml_extracts/education/lc_subject/ExtractSeniorCycleSyllabus`
     (when available) — provides schema validation + retries +
     Langfuse tracing.

  2. The baml_pydantic_bridge fallback (`extract_with_fallback`) —
     for tests + dev environments where the BAML client is unavailable.

  3. The offline regex extraction — last resort, always available.

The output is a typed `MarkingSchemeExtraction` (Pydantic), mirroring
the canonical BAML schema. The PCLM emitter (`pclm_emitter.py`)
consumes this for the PCLM-XML + PDF download.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

_log = logging.getLogger("an_scrudu.extraction")

# Stage 1 — the LC past-paper corpus directory.
# Populated by W5 (which lifts the cianfhoghlaim Ireland DLT pipeline)
# and W11 (which scrapes the live NCCA / SEC sites).
LC_PAST_PAPER_CORPUS_DIR = Path(
    "/Users/cianmacandeisigh/dev/gemini_hackathon/data/ireland/lc_subject/past_papers"
)


# ---------------------------------------------------------------------------
# Pydantic schema (mirrors the BAML extraction shape)
# ---------------------------------------------------------------------------


class TopicDistribution(BaseModel):
    """One topic in a marking-scheme extraction."""

    topic_code: str = Field(..., description="e.g. CH1, IR1, MA2")
    topic_label: str
    marking_points: int
    paper_section: str = Field(..., description="e.g. Section A, Section B")


class CircularReference(BaseModel):
    """Reference to the Department-of-Education circular."""

    circular_number: int
    issued_year: int
    issuing_body: str = "State Examinations Commission (SEC)"
    title_en: str
    title_ga: str | None = None
    subject: str
    level: str = Field(default="Leaving Certificate", description="LC or JC")


class MarkingSchemeSummary(BaseModel):
    """The marking scheme's structure (topics, duration, etc.)."""

    total_marking_points: int
    topics: list[TopicDistribution]
    estimated_paper_duration_min: int
    has_orale: bool = False  # true for Irish oral component
    has_coursework: bool = False  # true for any coursework/portfolio


class MarkingSchemeExtraction(BaseModel):
    """A typed marking-scheme extraction record (the editorial canvas output)."""

    circular: CircularReference
    scheme: MarkingSchemeSummary
    raw_text_excerpt: str = ""
    extraction_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    source_model: str = "offline"


# ---------------------------------------------------------------------------
# Legacy flat dataclass (kept for backward compat)
# ---------------------------------------------------------------------------


@dataclass
class _LegacyExtraction:
    """Legacy flat shape (deprecated; use MarkingSchemeExtraction)."""

    circular_number: int
    issued_year: int
    issuing_body: str
    title_en: str
    title_ga: str = ""
    subject: str = ""
    level: str = ""
    total_marking_points: int = 0
    topics: list[TopicDistribution] = field(default_factory=list)
    estimated_paper_duration_min: int = 0
    has_orale: bool = False
    has_coursework: bool = False
    raw_text_excerpt: str = ""
    extraction_confidence: float = 0.0
    source_model: str = "offline"


# ---------------------------------------------------------------------------
# Extraction flow
# ---------------------------------------------------------------------------


_BAML_PROMPT_TEMPLATE = """\
Extract the Irish Leaving Certificate past-paper marking-scheme structure from the text below.

Filename: {filename}

Text (first 8,000 chars):
---
{pdf_text}
---

Return a JSON object with this exact shape:
{{
  "circular": {{
    "circular_number": <int>,
    "issued_year": <int>,
    "issuing_body": <string>,
    "title_en": <string>,
    "title_ga": <string or null>,
    "subject": <string>,
    "level": <string, "Leaving Certificate" or "Junior Cycle">
  }},
  "scheme": {{
    "total_marking_points": <int>,
    "topics": [{{
      "topic_code": <string>,
      "topic_label": <string>,
      "marking_points": <int>,
      "paper_section": <string>
    }}],
    "estimated_paper_duration_min": <int>,
    "has_orale": <bool>,
    "has_coursework": <bool>
  }},
  "raw_text_excerpt": <string, 200-300 char literal excerpt>,
  "extraction_confidence": <float, 0.0 to 1.0>
}}
"""


def extract_circular(pdf_text: str, filename: str) -> MarkingSchemeExtraction:
    """Extract the mark scheme structure from a LC past paper.

    Routes through:
      1. The canonical BAML function in `gemini_hackathon/baml_extracts/`
         (if available) — production path.
      2. The baml_pydantic_bridge fallback — uses the 3-tier LLM
         client to extract, validates the response against the
         Pydantic schema.
      3. The offline regex extraction — last resort.

    Args:
        pdf_text: The text of the past paper (first 8,000 chars used).
        filename: The original filename, for context.

    Returns:
        A typed `MarkingSchemeExtraction`. The `source_model` field
        records which path produced it.
    """
    # Path 1: try the canonical BAML function if it's importable.
    try:
        # Lazy import to avoid forcing baml_client/ to exist in dev.
        from baml_client import b

        result = b.ExtractSeniorCycleSyllabus(pdf_text=pdf_text[:8000], filename=filename)
        return _baml_to_pydantic(result, source_model="baml")
    except (ImportError, AttributeError):
        pass

    # Path 2: baml_pydantic_bridge.
    from .._common.baml_pydantic_bridge import extract_with_fallback

    messages = [
        {
            "role": "system",
            "content": (
                "You are a precise Irish-curriculum document analyser. "
                "You extract structured metadata from Leaving Cert past "
                "papers. You always return valid JSON matching the schema."
            ),
        },
        {
            "role": "user",
            "content": _BAML_PROMPT_TEMPLATE.format(filename=filename, pdf_text=pdf_text[:8000]),
        },
    ]
    record = extract_with_fallback(
        MarkingSchemeExtraction,
        messages=messages,
        raw_text=pdf_text[:8000],
        timeout=60,
    )
    if record is not None:
        return record

    # Path 3: offline regex fallback.
    return _offline_extraction(pdf_text, filename)


def _baml_to_pydantic(baml_result: Any, *, source_model: str) -> MarkingSchemeExtraction:
    """Convert the BAML-generated result into our Pydantic schema.

    The BAML class shape (lifted from
    `oideachais/baml_src/circular_extraction.baml`) has the same nested
    `circular` + `scheme` structure. We map field-by-field.
    """
    return MarkingSchemeExtraction.model_validate(
        {
            "circular": {
                "circular_number": baml_result.circular.circular_number,
                "issued_year": baml_result.circular.issued_year,
                "issuing_body": baml_result.circular.issuing_body,
                "title_en": baml_result.circular.title_en,
                "title_ga": baml_result.circular.title_ga,
                "subject": baml_result.circular.subject,
                "level": baml_result.circular.level,
            },
            "scheme": {
                "total_marking_points": baml_result.scheme.total_marking_points,
                "topics": [
                    {
                        "topic_code": t.topic_code,
                        "topic_label": t.topic_label,
                        "marking_points": t.marking_points,
                        "paper_section": t.paper_section,
                    }
                    for t in baml_result.scheme.topics
                ],
                "estimated_paper_duration_min": baml_result.scheme.estimated_paper_duration_min,
                "has_orale": baml_result.scheme.has_orale,
                "has_coursework": baml_result.scheme.has_coursework,
            },
            "raw_text_excerpt": baml_result.raw_text_excerpt[:300],
            "extraction_confidence": baml_result.extraction_confidence,
            "source_model": source_model,
        }
    )


def _offline_extraction(pdf_text: str, filename: str) -> MarkingSchemeExtraction:
    """Last-resort regex-based extraction. Returns a low-confidence record.

    Used when all 3 LLM tiers fail (offline / dev mode).
    """
    # Detect subject from filename
    name_lower = filename.lower()
    subject = "Unknown"
    for token in (
        "chemistry",
        "mathematics",
        "english",
        "gaeilge",
        "geography",
        "physics",
        "biology",
        "french",
        "history",
    ):
        if token in name_lower:
            subject = token.title()
            break

    # Detect year (1995-2026)
    year_match = re.search(r"(19|20)\d{2}", filename)
    year = int(year_match.group(0)) if year_match else 2024

    # Detect marks (total: e.g. "Total: 300 marks" or "300 marc")
    marks_match = re.search(r"[Tt]otal[:\s]+(\d{2,3})\s*m[aá]r[ck]", pdf_text[:8000])
    total_marks = int(marks_match.group(1)) if marks_match else 300

    # Detect duration (e.g. "2 hours 30 minutes")
    duration_match = re.search(r"(\d)\s*hour[s]?\s*(\d{0,2})\s*min", pdf_text[:8000], re.IGNORECASE)
    duration = (
        int(duration_match.group(1)) * 60 + int(duration_match.group(2) or 0)
        if duration_match
        else 180
    )

    # Detect section labels (Section A, Section B)
    sections = re.findall(r"Section\s+([A-Z])", pdf_text[:8000])

    # Build 4 placeholder topics (so the heatmap + PCLM renderer have something to show)
    topic_count = min(len(set(sections)) or 1, 4) + 1
    topics = [
        TopicDistribution(
            topic_code=f"{subject[:2].upper()}{i + 1}",
            topic_label=f"Topic {i + 1} (offline placeholder)",
            marking_points=total_marks // topic_count,
            paper_section=f"Section {chr(ord('A') + i)}",
        )
        for i in range(topic_count)
    ]

    return MarkingSchemeExtraction(
        circular=CircularReference(
            circular_number=0,
            issued_year=year,
            issuing_body="State Examinations Commission (offline stub)",
            title_en=filename,
            title_ga=None,
            subject=subject,
            level="Leaving Certificate",
        ),
        scheme=MarkingSchemeSummary(
            total_marking_points=total_marks,
            topics=topics,
            estimated_paper_duration_min=duration,
            has_orale=subject == "Gaeilge",
            has_coursework=False,
        ),
        raw_text_excerpt=pdf_text[:280],
        extraction_confidence=0.1,  # very low — this is the offline fallback
        source_model="offline",
    )


__all__ = [
    "LC_PAST_PAPER_CORPUS_DIR",
    "CircularReference",
    "MarkingSchemeExtraction",
    "MarkingSchemeSummary",
    "TopicDistribution",
    "extract_circular",
]
