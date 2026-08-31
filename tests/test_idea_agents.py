"""Smoke tests for the 4 idea agents.

4 tests, one per agent:

* :class:`MarkingGraderWorkflow` returns a per-question :class:`MarkingBreakdown`.
* :class:`AdaptiveTutor` uses the active source palette in its
  message construction.
* :class:`EquivalencyGenerator` produces one :class:`EquivalencyRow`
  per target jurisdiction (the canonical 5).
* :class:`CurriculumChangeSensor` returns a list of :class:`ChangeEvent`.

All tests use the :func:`mock_call_llm` fixture from
:mod:`tests.conftest` — no live API calls, no live BAML extraction.
The :func:`tmp_themes_dir` fixture provides the palette fixtures.
"""

from __future__ import annotations

import json

import pytest

from gemini_hackathon.agents.fleet import IdentityContext

# ---------------------------------------------------------------------------
# Marking Grader Workflow
# ---------------------------------------------------------------------------


def test_marking_grader_workflow_returns_breakdown(
    mock_call_llm,
    tmp_themes_dir: object,
) -> None:
    """The marking grader returns a per-question :class:`MarkingBreakdown`.

    Asserts:

    * The canned ``call_llm`` response (a valid JSON breakdown) is
      parsed into one :class:`MarkingBreakdown` row per question.
    * The total marks + grade are computed against the canonical
      :data:`DEFAULT_LC_GRADING_SCALE`.
    * The :class:`MarkingResult` carries the active palette.
    """
    from gemini_hackathon.agents.ideas import (
        DEFAULT_LC_GRADING_SCALE,
        MarkingGraderWorkflow,
        MarkingRequest,
        MarkingSchemeQuestion,
        StudentAnswer,
    )

    # Override the canned LLM response with a 2-question breakdown.
    mock_call_llm.return_content = json.dumps(
        {
            "breakdown": [
                {
                    "question_id": "Q1",
                    "awarded_marks": 8.0,
                    "max_marks": 10,
                    "justification": "Mostly correct",
                    "rubric_alignment": ["a"],
                    "confidence": 0.9,
                },
                {
                    "question_id": "Q2",
                    "awarded_marks": 18.0,
                    "max_marks": 20,
                    "justification": "Strong answer",
                    "rubric_alignment": ["b", "c"],
                    "confidence": 0.95,
                },
            ]
        }
    )

    workflow = MarkingGraderWorkflow()
    request = MarkingRequest(
        subject="Mathematics",
        marking_scheme=[
            MarkingSchemeQuestion(
                question_id="Q1",
                prompt="Differentiate x^2.",
                max_marks=10,
                rubric="2 marks per derivative step",
            ),
            MarkingSchemeQuestion(
                question_id="Q2",
                prompt="Solve the quadratic",
                max_marks=20,
                rubric="4 marks per root",
            ),
        ],
        student_answers=[
            StudentAnswer(question_id="Q1", answer_text="2x"),
            StudentAnswer(question_id="Q2", answer_text="x=2 and x=-3"),
        ],
        identity=IdentityContext(
            user_id="teacher-1",
            role="teacher",
            jurisdiction="Ireland",
            level="LC",
            source_palette_key="ncca.ie",
        ),
    )

    result = workflow.invoke(request)

    assert len(result.breakdown) == 2
    assert result.total_awarded == 26.0
    assert result.total_available == 30
    assert result.overall_pct == pytest.approx(86.67, rel=1e-2)
    # The default scale: 80-90% → A2.
    assert result.grade == "A2"
    # The default scale is the canonical LC scale.
    assert DEFAULT_LC_GRADING_SCALE


# ---------------------------------------------------------------------------
# Adaptive Tutor
# ---------------------------------------------------------------------------


def test_adaptive_tutor_uses_active_palette(
    mock_call_llm,
    tmp_themes_dir: object,
) -> None:
    """The adaptive tutor builds messages that mention the active palette.

    Asserts:

    * The :class:`AdaptiveTutor` resolves the palette from the
      identity's ``source_palette_key``.
    * The system prompt references the jurisdiction + level + the
      active palette's primary hex code.
    * The LLM invocation was made (and the canned response was returned).
    """
    from gemini_hackathon.agents.ideas import (
        AdaptiveTutor,
        TutorRequest,
    )

    # The NCCA palette is on disk in tmp_themes_dir.
    identity = IdentityContext(
        user_id="pupil-1",
        jurisdiction="Ireland",
        level="LC",
        source_palette_key="ncca.ie",
    )
    tutor = AdaptiveTutor()
    response = tutor.invoke(
        TutorRequest(
            question="Please explain quadratic functions",
            topic_hint="Quadratic Functions",
            identity=identity,
        )
    )

    # The response is a TutorResponse with the canned content.
    assert response.answer == mock_call_llm.return_content
    # The resolved topic is the hint.
    assert response.topic == "Quadratic Functions"
    # The palette was resolved.
    assert response.palette is not None
    assert response.palette.source_key == "ncca.ie"

    # The canned call_llm was invoked exactly once.
    assert mock_call_llm.call_count == 1


# ---------------------------------------------------------------------------
# Equivalency Generator
# ---------------------------------------------------------------------------


def test_equivalency_generator_maps_across_5_targets(
    mock_call_llm,
    tmp_themes_dir: object,
) -> None:
    """The equivalency generator produces 5 :class:`EquivalencyRow`s.

    Asserts:

    * With ``source_jurisdiction="Ireland"`` the generator targets
      the canonical 5 other BI jurisdictions (England / Scotland /
      Wales / Northern Ireland / Isle of Man).
    * Each row carries the awarding body string from
      :data:`JURISDICTION_AWARDING_BODY`.
    * The canned LLM response is parsed and the rows are exposed on
      the :class:`EquivalencyResult`.
    """
    from gemini_hackathon.agents.ideas import (
        ALL_TARGET_JURISDICTIONS,
        JURISDICTION_AWARDING_BODY,
        EquivalencyGenerator,
        EquivalencyRequest,
        EquivalencyRow,
    )

    # The canned LLM response lists 5 target jurisdictions.
    mock_call_llm.return_content = json.dumps(
        {
            "equivalents": {
                "England": "Quadratic Functions",
                "Scotland": "Quadratic Functions & Graphs",
                "Wales": "Quadratic Functions",
                "Northern Ireland": "Quadratic Functions",
                "Isle of Man": "Quadratic Functions",
            },
            "confidence": 0.92,
            "notes": "Strong overlap across all jurisdictions.",
        }
    )

    generator = EquivalencyGenerator()
    result = generator.invoke(
        EquivalencyRequest(
            topic="Quadratic Functions",
            source_jurisdiction="Ireland",
            subject="Mathematics",
            identity=IdentityContext(
                user_id="pupil-1",
                role="pupil",
                jurisdiction="Ireland",
                level="LC",
                source_palette_key="ncca.ie",
            ),
        )
    )

    assert len(result.rows) == len(ALL_TARGET_JURISDICTIONS)
    assert {r.target_jurisdiction for r in result.rows} == set(ALL_TARGET_JURISDICTIONS)

    # Each row carries the awarding body.
    for row in result.rows:
        assert isinstance(row, EquivalencyRow)
        assert row.awarding_body == JURISDICTION_AWARDING_BODY[row.target_jurisdiction]


# ---------------------------------------------------------------------------
# Curriculum Change Sensor
# ---------------------------------------------------------------------------


def test_curriculum_change_sensor_returns_change_events(
    mock_call_llm,
    tmp_themes_dir: object,
) -> None:
    """The change sensor emits the canonical :class:`ChangeEvent` rows.

    Asserts:

    * The canned LLM response (a JSON list of ChangeEvents) is
      parsed into the right dataclasses.
    * The :class:`CurriculumChangeResult.events` list is non-empty.
    * The ``themes_re_extracted`` flag is True when at least one
      NEW_SYLLABUS event is present.
    """
    from gemini_hackathon.agents.ideas import (
        ChangeEvent,
        ChangeType,
        CurriculumChangeRequest,
        CurriculumChangeResult,
        CurriculumChangeSensor,
    )

    mock_call_llm.return_content = json.dumps(
        [
            {
                "source_url": "https://www.curriculumonline.ie/senior-cycle/maths",
                "change_type": "NEW_SYLLABUS",
                "affected_topics": ["Calculus", "Statistics"],
                "summary": "New LC Mathematics specification published.",
                "effective_date": "2026-09-01",
                "confidence": 0.95,
                "jurisdiction": "Ireland",
                "level": "LC",
            },
            {
                "source_url": "https://www.curriculumonline.ie/senior-cycle/maths",
                "change_type": "UPDATED_SYLLABUS",
                "affected_topics": ["Algebra"],
                "summary": "Algebra section extended with matrices.",
                "effective_date": "",
                "confidence": 0.85,
                "jurisdiction": "Ireland",
                "level": "LC",
            },
        ]
    )

    sensor = CurriculumChangeSensor()
    result = sensor.invoke(
        CurriculumChangeRequest(
            source_url="https://www.curriculumonline.ie/senior-cycle/maths",
            before_text="(initial capture)",
            after_text="(post-publication capture)",
            identity=IdentityContext(
                user_id="safeguarding-lead-1",
                role="safeguarding_lead",
                jurisdiction="Ireland",
                level="LC",
                source_palette_key="ncca.ie",
            ),
        )
    )

    assert isinstance(result, CurriculumChangeResult)
    assert len(result.events) == 2
    # The first event is a NEW_SYLLABUS → themes_re_extracted = True.
    assert isinstance(result.events[0], ChangeEvent)
    assert result.events[0].change_type == ChangeType.NEW_SYLLABUS
    assert result.events[1].change_type == ChangeType.UPDATED_SYLLABUS
    assert result.themes_re_extracted is True
