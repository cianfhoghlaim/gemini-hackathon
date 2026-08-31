"""gemini_hackathon.agents.ideas.marking_grader_workflow — LC marking grader.

The Marking Grader Workflow is one of the 4 idea agents in the
gemini_hackathon fleet (per the openspec change
``2026-08-24-gemini-hackathon-public-v1``). Given:

* A student's answer script (free-form text or per-question blocks)
* The corresponding official marking scheme (per-question + per-part)

…this agent produces a per-question mark breakdown that aligns to
the marking scheme, with a justified grade for each question.

The agent always uses the canonical :func:`gemini_hackathon.call_llm`
entrypoint (the 3-tier model policy) and the
:func:`gemini_hackathon.theming.load_palette` function to render
the result in the active source's brand identity.

This agent is the wholesale port of the Cianfhoghlaim
``marking_grader_workflow.py`` (per the
``wholesale-copy-convention``) — adapted from the
``google.adk.agents.LlmAgent`` factory to a plain Python class.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import structlog

from gemini_hackathon.call_llm import LLMResponse, Message, call_llm
from gemini_hackathon.theming import Palette, load_palette

from ..fleet.fleet_identity import IdentityContext
from ..fleet.fleet_observability import Observability, TraceContext

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MarkingSchemeQuestion:
    """One question on the official marking scheme.

    Attributes:
        question_id: Stable question identifier (e.g. ``"Q1"``,
            ``"Q2(b)(iii)"``).
        prompt: The question text from the exam paper.
        max_marks: The maximum marks available for the question.
        rubric: The official marking scheme text (per-part bullet
            list, or a single paragraph).
        level: The curriculum level (``"LC"`` / ``"A-Level"`` /
            ``"GCSE"`` / …). Defaults to the active identity
            level when empty.
    """

    question_id: str
    prompt: str
    max_marks: int
    rubric: str
    level: str = ""


@dataclass(frozen=True)
class StudentAnswer:
    """One question's worth of student work.

    Attributes:
        question_id: The :attr:`MarkingSchemeQuestion.question_id`
            this answer belongs to.
        answer_text: The student's free-form answer text.
        attachments: Optional list of attachment filenames (e.g.
            ``["scan-p1.png"]``).
    """

    question_id: str
    answer_text: str
    attachments: tuple[str, ...] = ()


@dataclass(frozen=True)
class MarkingBreakdown:
    """The per-question mark breakdown for one question.

    Attributes:
        question_id: The question identifier.
        awarded_marks: The number of marks awarded (0 to
            ``max_marks``).
        max_marks: The maximum marks available.
        justification: The grader's plain-English justification
            (citing the rubric bullets that apply).
        rubric_alignment: The list of rubric bullet IDs that were
            satisfied (e.g. ``["b(i)", "b(iii)"]``).
        confidence: The grader's confidence in [0.0, 1.0].
    """

    question_id: str
    awarded_marks: float
    max_marks: int
    justification: str
    rubric_alignment: tuple[str, ...] = ()
    confidence: float = 0.0

    @property
    def pct(self) -> float:
        """Return the percentage score (0-100)."""
        if self.max_marks <= 0:
            return 0.0
        return round(100.0 * self.awarded_marks / self.max_marks, 2)


@dataclass(frozen=True)
class MarkingResult:
    """The full marking output for one student's paper.

    Attributes:
        student_id: Optional student identifier.
        subject: The exam subject (e.g. ``"Mathematics"``).
        breakdown: The list of :class:`MarkingBreakdown` rows.
        total_awarded: The sum of ``awarded_marks``.
        total_available: The sum of ``max_marks``.
        overall_pct: The total percentage (0-100).
        grade: The letter grade (``"A1"`` / ``"B2"`` / etc. — or
            empty string if grading scale is unknown).
        palette: The active :class:`Palette`.
        llm_response: The underlying :class:`LLMResponse`.
        trace_id: The observability trace ID.
    """

    student_id: str
    subject: str
    breakdown: list[MarkingBreakdown]
    total_awarded: float
    total_available: int
    overall_pct: float
    grade: str
    palette: Palette | None
    llm_response: LLMResponse
    trace_id: str


@dataclass(frozen=True)
class MarkingRequest:
    """The input envelope for the marking workflow.

    Attributes:
        subject: The exam subject.
        marking_scheme: The list of :class:`MarkingSchemeQuestion`.
        student_answers: The list of :class:`StudentAnswer`.
        student_id: Optional student identifier.
        identity: The resolved :class:`IdentityContext`.
        grading_scale: Optional list of ``(pct, grade)`` tuples
            (default: the LC A1-F2 scale).
    """

    subject: str
    marking_scheme: Sequence[MarkingSchemeQuestion]
    student_answers: Sequence[StudentAnswer]
    student_id: str = ""
    identity: IdentityContext | None = None
    grading_scale: Sequence[tuple[float, str]] = ()


# ---------------------------------------------------------------------------
# Constants — the canonical LC grading scale
# ---------------------------------------------------------------------------

DEFAULT_LC_GRADING_SCALE: tuple[tuple[float, str], ...] = (
    (90.0, "A1"),
    (80.0, "A2"),
    (70.0, "B1"),
    (60.0, "B2"),
    (50.0, "B3"),
    (40.0, "C1"),
    (30.0, "C2"),
    (20.0, "C3"),
    (10.0, "D1"),
    (0.0, "D2"),
)


# ---------------------------------------------------------------------------
# The MarkingGraderWorkflow agent
# ---------------------------------------------------------------------------


class MarkingGraderWorkflow:
    """The Marking Grader Workflow idea agent.

    Constructed once at process start and registered with the
    :class:`FleetGateway`. The :meth:`invoke` method is the
    canonical entrypoint for the gateway's keyword router.
    """

    def __init__(
        self,
        *,
        observability: Observability | None = None,
    ) -> None:
        """Initialise the workflow.

        Args:
            observability: The :class:`Observability` (default: a
                fresh instance).
        """
        self.observability = observability or Observability()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def invoke(
        self,
        request: MarkingRequest,
        *,
        trace: TraceContext | None = None,
    ) -> MarkingResult:
        """Run the marking workflow for one student paper.

        Args:
            request: The :class:`MarkingRequest` envelope.
            trace: Optional pre-existing observability trace.

        Returns:
            The :class:`MarkingResult` envelope.
        """
        identity = request.identity or IdentityContext()
        grading_scale = list(request.grading_scale) or list(DEFAULT_LC_GRADING_SCALE)
        answer_by_qid = {a.question_id: a for a in request.student_answers}

        # Open the trace.
        if trace is None:
            cm = self.observability.trace(
                agent="marking_grader_workflow",
                user_id=identity.user_id,
                metadata={
                    "subject": request.subject,
                    "question_count": len(request.marking_scheme),
                    "student_id": request.student_id,
                },
            )
            trace = cm.__enter__()  # capture the yielded TraceContext
            close_cm = cm
        else:
            close_cm = None

        try:
            messages = self._build_messages(request, answer_by_qid)
            llm_response = call_llm(
                messages=messages,
                metadata={
                    "trace_id": trace.trace_id,
                    "agent": "marking_grader_workflow",
                    "user_id": identity.user_id,
                },
            )
            self.observability.record_invocation(trace, llm_response)

            # Parse the per-question breakdown out of the response.
            breakdown = _parse_breakdown(llm_response.content, request)

            total_awarded = sum(b.awarded_marks for b in breakdown)
            total_available = sum(b.max_marks for b in breakdown)
            overall_pct = (
                round(100.0 * total_awarded / total_available, 2) if total_available else 0.0
            )
            grade = _grade_for(overall_pct, grading_scale)
            palette = load_palette(identity.source_palette_key)

            return MarkingResult(
                student_id=request.student_id,
                subject=request.subject,
                breakdown=breakdown,
                total_awarded=total_awarded,
                total_available=total_available,
                overall_pct=overall_pct,
                grade=grade,
                palette=palette,
                llm_response=llm_response,
                trace_id=trace.trace_id,
            )
        finally:
            if close_cm is not None:
                close_cm.__exit__(None, None, None)

    def as_gateway_invoker(
        self,
        *,
        sanitised_input: Any,
        identity: IdentityContext,
        trace: TraceContext,
    ) -> list[Message]:
        """Adapter that produces the message list for the gateway.

        Args:
            sanitised_input: The :class:`SanitisedPrompt`.
            identity: The :class:`IdentityContext`.
            trace: The :class:`TraceContext`.

        Returns:
            The message list to send to :func:`call_llm`.

        Raises:
            ValueError: If the sanitised prompt does not contain
                enough structure to extract the marking scheme +
                student answers. The gateway caller should attach
                the structured payload as metadata when invoking
                this agent (see the gateway keyword router).
        """
        # The gateway stores the structured marking payload on
        # the invocation metadata under ``marking_payload``. If
        # it's absent we fall back to building a placeholder
        # request so the LLM call still succeeds (with a clear
        # note in the system prompt).
        metadata = trace.metadata.get("marking_payload") or {}
        try:
            request = _request_from_metadata(sanitised_input.text, metadata, identity)
        except Exception as e:
            logger.warning(
                "marking.payload_parse_failed",
                error=f"{type(e).__name__}: {e}",
            )
            request = MarkingRequest(
                subject=metadata.get("subject", "Unknown"),
                marking_scheme=[],
                student_answers=[],
                student_id=metadata.get("student_id", ""),
                identity=identity,
            )
        trace.metadata["subject"] = request.subject
        trace.metadata["question_count"] = len(request.marking_scheme)
        return self._build_messages(request, {a.question_id: a for a in request.student_answers})

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_messages(
        self,
        request: MarkingRequest,
        answer_by_qid: dict[str, StudentAnswer],
    ) -> list[Message]:
        """Compose the message list for :func:`call_llm`."""
        scheme_block = _render_scheme(request.marking_scheme)
        answers_block = _render_answers(request.student_answers)

        system = (
            "You are the BIEP Marking Grader. You mark a Leaving "
            "Certificate paper against its official marking "
            "scheme. Be conservative: only award marks that are "
            "explicitly supported by the rubric. Cite the rubric "
            "bullet(s) that justify each awarded mark. Score your "
            "confidence in [0.0, 1.0]. Return ONLY valid JSON of "
            "the shape:\n"
            "{\n"
            '  "breakdown": [\n'
            "    {\n"
            '      "question_id": "Q1",\n'
            '      "awarded_marks": <float>,\n'
            '      "max_marks": <int>,\n'
            '      "justification": "<plain English>",\n'
            '      "rubric_alignment": ["<rubric bullet IDs>"],\n'
            '      "confidence": <float 0-1>\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Do not wrap the JSON in markdown fences. The "
            "awarded_marks field MUST NOT exceed max_marks."
        )
        user = (
            f"SUBJECT: {request.subject}\n"
            f"STUDENT_ID: {request.student_id or '(anonymous)'}\n\n"
            f"MARKING SCHEME\n{scheme_block}\n\n"
            f"STUDENT ANSWERS\n{answers_block}"
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _render_scheme(scheme: Sequence[MarkingSchemeQuestion]) -> str:
    """Render the marking scheme as a Markdown block."""
    if not scheme:
        return "(no marking scheme provided)"
    blocks: list[str] = []
    for q in scheme:
        blocks.append(
            f"### {q.question_id} (max {q.max_marks} marks)\n"
            f"**Prompt:** {q.prompt}\n\n"
            f"**Rubric:**\n{q.rubric}"
        )
    return "\n\n".join(blocks)


def _render_answers(answers: Sequence[StudentAnswer]) -> str:
    """Render the student answers as a Markdown block."""
    if not answers:
        return "(no student answers provided)"
    blocks: list[str] = []
    for a in answers:
        attachments = f" (attachments: {', '.join(a.attachments)})" if a.attachments else ""
        blocks.append(f"### {a.question_id}{attachments}\n{a.answer_text}")
    return "\n\n".join(blocks)


def _parse_breakdown(content: str, request: MarkingRequest) -> list[MarkingBreakdown]:
    """Best-effort parse of the LLM JSON response."""
    import json as _json

    try:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`").split("\n", 1)[-1].rsplit("```", 1)[0]
        payload = _json.loads(cleaned)
    except Exception as e:
        logger.warning(
            "marking.llm_json_parse_failed",
            error=f"{type(e).__name__}: {e}",
            content_preview=content[:120],
        )
        # Fall back to a zero-mark breakdown for every question.
        return [
            MarkingBreakdown(
                question_id=q.question_id,
                awarded_marks=0.0,
                max_marks=q.max_marks,
                justification=f"(parse failure: {e})",
                rubric_alignment=(),
                confidence=0.0,
            )
            for q in request.marking_scheme
        ]

    rows = payload.get("breakdown", []) or []
    max_marks_by_qid = {q.question_id: q.max_marks for q in request.marking_scheme}
    breakdown: list[MarkingBreakdown] = []
    for row in rows:
        qid = str(row.get("question_id", ""))
        awarded = float(row.get("awarded_marks", 0) or 0)
        max_marks = int(row.get("max_marks", max_marks_by_qid.get(qid, 0)) or 0)
        # Defensive clamp.
        if max_marks > 0:
            awarded = max(0.0, min(awarded, float(max_marks)))
        breakdown.append(
            MarkingBreakdown(
                question_id=qid,
                awarded_marks=awarded,
                max_marks=max_marks,
                justification=str(row.get("justification", "")),
                rubric_alignment=tuple(row.get("rubric_alignment", []) or []),
                confidence=float(row.get("confidence", 0.0) or 0.0),
            )
        )
    # Backfill missing questions with a zero-mark row.
    seen = {b.question_id for b in breakdown}
    for q in request.marking_scheme:
        if q.question_id not in seen:
            breakdown.append(
                MarkingBreakdown(
                    question_id=q.question_id,
                    awarded_marks=0.0,
                    max_marks=q.max_marks,
                    justification="(no breakdown returned by the LLM)",
                    rubric_alignment=(),
                    confidence=0.0,
                )
            )
    # Sort by question_id (preserves the question order in the scheme).
    breakdown.sort(key=lambda b: b.question_id)
    return breakdown


def _grade_for(pct: float, scale: Sequence[tuple[float, str]]) -> str:
    """Return the grade string for the given percentage."""
    sorted_scale = sorted(scale, key=lambda t: -t[0])
    for threshold, grade in sorted_scale:
        if pct >= threshold:
            return grade
    return sorted_scale[-1][1] if sorted_scale else ""


def _request_from_metadata(
    sanitised_text: str,
    metadata: dict[str, Any],
    identity: IdentityContext,
) -> MarkingRequest:
    """Build a :class:`MarkingRequest` from the gateway metadata.

    The metadata is expected to be of the shape::

        {
            "subject": "Mathematics",
            "student_id": "u-42",
            "marking_scheme": [
                {"question_id": "Q1", "prompt": "...", "max_marks": 10, "rubric": "..."}
            ],
            "student_answers": [{"question_id": "Q1", "answer_text": "..."}],
        }
    """
    scheme_payload = metadata.get("marking_scheme", [])
    answers_payload = metadata.get("student_answers", [])
    if not isinstance(scheme_payload, list) or not isinstance(answers_payload, list):
        raise ValueError(
            "marking_payload must contain `marking_scheme` and `student_answers` lists."
        )
    scheme = [
        MarkingSchemeQuestion(
            question_id=str(q.get("question_id", "")),
            prompt=str(q.get("prompt", "")),
            max_marks=int(q.get("max_marks", 0) or 0),
            rubric=str(q.get("rubric", "")),
            level=str(q.get("level", identity.level)),
        )
        for q in scheme_payload
    ]
    answers = [
        StudentAnswer(
            question_id=str(a.get("question_id", "")),
            answer_text=str(a.get("answer_text", "")),
            attachments=tuple(a.get("attachments", []) or []),
        )
        for a in answers_payload
    ]
    return MarkingRequest(
        subject=str(metadata.get("subject", "Unknown")),
        marking_scheme=scheme,
        student_answers=answers,
        student_id=str(metadata.get("student_id", "")),
        identity=identity,
    )


# ---------------------------------------------------------------------------
# Public exports
# ---------------------------------------------------------------------------

__all__ = [
    "DEFAULT_LC_GRADING_SCALE",
    "MarkingBreakdown",
    "MarkingGraderWorkflow",
    "MarkingRequest",
    "MarkingResult",
    "MarkingSchemeQuestion",
    "StudentAnswer",
    "build_default_workflow",
    "workflow_invoker",
]


# ---------------------------------------------------------------------------
# Convenience constructors
# ---------------------------------------------------------------------------


def build_default_workflow() -> MarkingGraderWorkflow:
    """Construct a canonical :class:`MarkingGraderWorkflow` instance."""
    return MarkingGraderWorkflow()


def workflow_invoker(
    workflow: MarkingGraderWorkflow | None = None,
) -> Any:
    """Return a callable that adapts :class:`MarkingGraderWorkflow` for the gateway.

    Args:
        workflow: Optional pre-built workflow (default: a fresh
            :func:`build_default_workflow` instance).

    Returns:
        A callable suitable for
        :meth:`FleetGateway.register_agent`.
    """
    _wf = workflow or build_default_workflow()
    return _wf.as_gateway_invoker
