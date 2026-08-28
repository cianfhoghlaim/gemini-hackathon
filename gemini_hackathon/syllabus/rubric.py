"""gemini_hackathon.syllabus.rubric — the extraction-comparison rubric.

Per the user's "BAML vs VLM" comparison ask, we score each extraction
on 4 objective metrics + 1 LLM-judge subjective score:

  - Jaccard on topic titles (how similar are the topic sets)
  - LO coverage (|LOs_found| / |LOs_in_golden_syllabus|)
  - Pydantic schema conformance (% of extracted LOs that pass validation)
  - LLM-as-judge subjective 1-5 (the "would a teacher recognise this" score)
  - Cost + latency (USD + wall-clock seconds)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


def compute_jaccard(set_a: set[str], set_b: set[str]) -> float:
    """Return the Jaccard similarity between two string sets.

    0.0 = no overlap, 1.0 = identical.
    """
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


def compute_lo_coverage(*, found: set[str], golden: set[str]) -> float:
    """Return |found ∩ golden| / |golden|. 1.0 = perfect coverage."""
    if not golden:
        return 1.0
    return len(found & golden) / len(golden)


def compute_pydantic_conformance(*, raw_dict: dict, schema_cls: type) -> float:
    """Return % of fields that pass Pydantic validation.

    schema_cls: a Pydantic BaseModel class (e.g. LCSyllabusDocument).
    """
    try:
        schema_cls.model_validate(raw_dict)
        return 1.0
    except Exception:
        # Try a more lenient validation — check each field
        try:
            instance = schema_cls.model_construct(**raw_dict)
            # Count fields that have valid types
            valid = sum(
                1 for name, field in schema_cls.model_fields.items()
                if name in raw_dict and isinstance(raw_dict[name], field.annotation)
            )
            return valid / max(1, len(schema_cls.model_fields))
        except Exception:
            return 0.0


def llm_judge_score(
    *,
    topic_titles: list[str],
    rubric: str = (
        "You are an expert Irish Leaving Certificate syllabus reviewer. "
        "Rate the topic set on a 1-5 scale:\n"
        "  5 = canonical topic set a teacher would recognise\n"
        "  4 = good coverage with minor omissions\n"
        "  3 = acceptable but missing key topics\n"
        "  2 = poor coverage\n"
        "  1 = nonsensical / not a syllabus"
    ),
    model: str = "gemini-3.5-flash",
) -> tuple[int, str]:
    """LLM-as-judge subjective score (1-5) + rationale.

    Returns (score, rationale_string).
    """
    try:
        import litellm  # type: ignore
    except ImportError:
        return 3, "[stub] litellm not installed — defaulting to 3"

    topics_str = "\n".join(f"  - {t}" for t in topic_titles[:50])  # cap at 50
    prompt = f"{rubric}\n\nTopics to rate:\n{topics_str}\n\nReturn a JSON object: {{\"score\": <1-5>, \"rationale\": \"<one sentence>\"}}"
    try:
        resp = litellm.completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        content = resp.choices[0].message.content or "{}"
        import json
        result = json.loads(content)
        return int(result.get("score", 3)), str(result.get("rationale", ""))
    except Exception as exc:
        logger.warning("llm_judge_score: %s", exc)
        return 3, f"[stub] LLM judge failed: {exc}"


@dataclass(frozen=True)
class ExtractionRubric:
    """The combined rubric for one (subject, extraction_method) cell."""

    subject: str
    extraction_method: str
    jaccard_vs_baml: float
    lo_coverage: float
    pydantic_conformance: float
    judge_score: int # 1-5
    judge_rationale: str
    cost_usd: float
    latency_ms: int
    found_topics: int
    golden_topics: int

    def to_dict(self) -> dict:
        return {
            "subject": self.subject,
            "extraction_method": self.extraction_method,
            "jaccard_vs_baml": self.jaccard_vs_baml,
            "lo_coverage": self.lo_coverage,
            "pydantic_conformance": self.pydantic_conformance,
            "judge_score": self.judge_score,
            "judge_rationale": self.judge_rationale,
            "cost_usd": self.cost_usd,
            "latency_ms": self.latency_ms,
            "found_topics": self.found_topics,
            "golden_topics": self.golden_topics,
        }


__all__ = [
    "ExtractionRubric",
    "compute_jaccard",
    "compute_lo_coverage",
    "compute_pydantic_conformance",
    "llm_judge_score",
]