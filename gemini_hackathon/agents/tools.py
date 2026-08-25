"""The 5 ADK agent tool implementations.

Each tool is a regular Python function that the Google ADK `LlmAgent`
can invoke. In dev (no RAG corpus) the tools return a stub response;
in production they wire to the RAG index (Phase 2 of the plan).

The 5 tools:
    1. `lookup_outcome`           - BAML ExtractOutcome
    2. `retrieve_resources`       - RAG over the chunked + embedded index
    3. `find_similar_resources`   - cross-national resource discovery
    4. `retrieve_safeguarding`    - active subnation's safeguarding policy
    5. `mark_answer`              - per-question mark breakdown
"""

from __future__ import annotations

import logging
from typing import Any

from ..session import (
    DEFAULT_PALETTE_PER_SUBNATION,
    get_subnation_meta,
    is_valid_subject,
    subjects_for,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tool 1: lookup_outcome
# ---------------------------------------------------------------------------


def lookup_outcome(*, subnation: str, subject_id: str, outcome_id: str) -> dict:
    """Return a specific learning outcome from the active subnation's syllabus.

    In production this calls the BAML ExtractOutcome function against the
    relevant syllabus PDF. In dev it returns a stub describing what the
    tool would return.
    """
    if not is_valid_subject(subject_id):
        return {"status": "not_found", "reason": f"Unknown subject_id: {subject_id!r}"}
    return {
        "status": "stub",
        "subnation": subnation,
        "subject_id": subject_id,
        "outcome_id": outcome_id,
        "outcome_text": (
            f"[stub] The student should be able to demonstrate outcome "
            f"{outcome_id} for {subject_id} per the {subnation} syllabus. "
            f"In production, BAML ExtractOutcome returns the canonical text."
        ),
        "source_pdf_path": f"/data/syllabi/{subnation}/{subject_id}.pdf",
        "page": 0,
    }


# ---------------------------------------------------------------------------
# Tool 2: retrieve_resources
# ---------------------------------------------------------------------------


def retrieve_resources(
    *,
    subnation: str,
    subject_id: str,
    topic: str,
    k: int = 5,
) -> list[dict]:
    """Return top-K resources for a topic from the active subnation.

    In production this hits the RAG index (Phase 2). In dev it returns
    a stub list.
    """
    return [
        {
            "source_nation": subnation,
            "resource_type": "textbook_chapter",
            "title": f"{topic} — Chapter reference",
            "url": f"https://{subnation}.example/syllabus/{subject_id}/{topic}",
            "score": 0.95,
            "rationale": "Stub: this is what the RAG index would return.",
        }
    ]


# ---------------------------------------------------------------------------
# Tool 3: find_similar_resources (the cross-national "find resources that help" feature)
# ---------------------------------------------------------------------------


def find_similar_resources(
    *,
    active_subnation: str,
    subject_id: str,
    topic: str,
    k: int = 8,
) -> list[dict]:
    """Cross-national resource discovery.

    Given a topic the user is studying in their home subnation, return
    resources from OTHER British Isles jurisdictions that may help.
    Each result is labelled with source nation + resource type + reason.

    This is the single most leveraged tool for the hackathon's Innovation
    criterion: an Irish student studying NCCA LC Maths can find English
    AQA Pure 1 resources that cover similar content; a Welsh student
    studying WJEC English can find English AQA English Literature; etc.

    In production this hits the RAG index (Phase 2). In dev it returns
    a stub list with one row per other active subnation.
    """
    other_subnations = [
        s for s in get_subnation_meta.__self_class__.__mro__[0] if False  # placeholder
    ] if False else _other_subnations(active_subnation)

    results = []
    for s in other_subnations:
        results.append({
            "source_subnation": s.code,
            "source_name": s.name,
            "source_flag": s.flag,
            "awarding_body": s.awarding_body_short,
            "resource_type": "exam_paper" if "paper" in topic.lower() else "textbook_chapter",
            "title": f"{topic} — {s.awarding_body_short} reference",
            "url": f"https://{s.code}.example/{subject_id}/{topic}",
            "score": 0.80,
            "rationale": (
                f"Stub: {s.awarding_body_short} covers similar learning outcomes "
                f"to your home subnation. In production, the RAG index returns "
                f"actual ranked matches."
            ),
        })
    return results[:k]


def _other_subnations(active_subnation: str) -> list[Any]:
    from ..session import SUBNATIONS
    return [s for s in SUBNATIONS if s.code != active_subnation and s.available]


# ---------------------------------------------------------------------------
# Tool 4: retrieve_safeguarding
# ---------------------------------------------------------------------------


def retrieve_safeguarding(*, subnation: str) -> dict:
    """Return the active subnation's safeguarding policy.

    In production this loads the policy JSON from the canonical
    `themes/safeguarding/` directory. In dev it returns a stub.
    """
    subnation_meta = get_subnation_meta(subnation)
    return {
        "subnation": subnation,
        "policy_source_key": subnation_meta.safeguarding_source_key,
        "policy_name": f"{subnation_meta.name} safeguarding policy",
        "policy_summary": (
            f"[stub] The {subnation_meta.awarding_body_short} requires schools to follow "
            f"the safeguarding policy at {subnation_meta.awarding_body_url}."
        ),
        "in_effect": True,
    }


# ---------------------------------------------------------------------------
# Tool 5: mark_answer
# ---------------------------------------------------------------------------


def mark_answer(
    *,
    subnation: str,
    subject_id: str,
    question: str,
    student_answer: str,
    marking_scheme_ref: str = "",
) -> dict:
    """Mark a piece of student work.

    In production this calls the BAML ExtractMarkingScheme function and
    applies the per-question descriptor vocabulary. In dev it returns
    a stub descriptor.
    """
    return {
        "subnation": subnation,
        "subject_id": subject_id,
        "question": question,
        "student_answer_length_chars": len(student_answer),
        "descriptor": "in_line_with_expectations",
        "rationale": (
            f"[stub] In production, the BAML ExtractMarkingScheme function "
            f"would return a per-question breakdown using the {subnation} "
            f"descriptor vocabulary (Exceptional / Above / In line / Yet to meet)."
        ),
        "marks_awarded": 0,
        "marks_available": 0,
    }


# ---------------------------------------------------------------------------
# ADK tool registry
# ---------------------------------------------------------------------------


def build_adk_tools() -> list[Any]:
    """Build the tool list for the Google ADK `LlmAgent`.

    The actual wrapping in `google.adk`'s FunctionTool format is done
    in the ADK integration layer. This function returns the raw Python
    callables — the ADK layer decides whether to wrap them as
    FunctionTool (synchronous) or FunctionAgent (async).
    """
    return [
        lookup_outcome,
        retrieve_resources,
        find_similar_resources,
        retrieve_safeguarding,
        mark_answer,
    ]


__all__ = [
    "build_adk_tools",
    "find_similar_resources",
    "list_subnations",
    "lookup_outcome",
    "mark_answer",
    "retrieve_resources",
    "retrieve_safeguarding",
]
