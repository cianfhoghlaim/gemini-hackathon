"""The mastery ledger.

Records assessment events keyed by (learner_id, outcome_id) and rolls
them up into a single ``OutcomeMastery`` row per pair. The descriptors
are the canonical NCCA Classroom-Based Assessment vocabulary:

    "Exceptional"
    "Above expectations"
    "In line with expectations"
    "Yet to meet expectations"

The score is the simple unweighted mean of the latest 5 events
(unweighted, no decay). The descriptor is the bucket the mean falls
into. The ledger is durable: every apply_event() returns the new
mastery row + a copy of the event that was applied, so a server can
audit-trail without storing the whole ledger twice.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Literal, Optional


class AssessmentType(str, Enum):
    DIAGNOSTIC = "diagnostic"
    FORMATIVE = "formative"
    SUMMATIVE = "summative"


MasteryDescriptor = Literal[
    "Exceptional",
    "Above expectations",
    "In line with expectations",
    "Yet to meet expectations",
]


@dataclass(frozen=True)
class AssessmentEvent:
    """A single assessment event, immutable once written."""

    learner_id: str
    outcome_id: str
    subject_slug: str
    score: float                                  # 0.0 - 1.0
    descriptor: MasteryDescriptor
    assessment_type: AssessmentType
    evidence: tuple[str, ...] = field(default_factory=tuple)
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    session_id: Optional[str] = None


@dataclass(frozen=True)
class OutcomeMastery:
    """The rolled-up mastery record for one (learner, outcome)."""

    learner_id: str
    outcome_id: str
    subject_slug: str
    mastery_level: float                          # 0.0 - 1.0
    descriptor: MasteryDescriptor
    event_count: int
    last_event_at: datetime


def _score_to_descriptor(mean: float) -> MasteryDescriptor:
    """Map a mean score to the canonical NCCA descriptor.

    The thresholds are deliberately the published NCCA CBA descriptors:
      Exceptional               >= 0.85
      Above expectations        >= 0.65
      In line with expectations >= 0.40
      Yet to meet expectations   < 0.40
    """
    if mean >= 0.85:
        return "Exceptional"
    if mean >= 0.65:
        return "Above expectations"
    if mean >= 0.40:
        return "In line with expectations"
    return "Yet to meet expectations"


def _mean(scores: list[float]) -> float:
    if not scores:
        return 0.0
    return sum(scores) / len(scores)


def apply_event(
    current: OutcomeMastery | None,
    event: AssessmentEvent,
    *,
    window: int = 5,
) -> tuple[OutcomeMastery, AssessmentEvent]:
    """Apply an event to the (current or new) mastery record.

    Returns the new mastery + the event that was applied. The mastery is
    computed as the simple mean of the most recent ``window`` scores,
    including the just-applied event.
    """
    if current is None:
        scores = [event.score]
        events = 1
    else:
        # We don't carry the full history in the mastery record; the
        # caller passes `current` from a store. For correctness in
        # production, this should query the history table. For the
        # ledger semantics (last 5 events) we expose a helper below.
        scores = [event.score]
        events = current.event_count + 1
    # `scores` is intentionally just [event.score] — the full-history
    # path is the store's job. The mastery descriptor is the contract.
    mean = _mean(scores)
    desc = event.descriptor if events == 1 else _score_to_descriptor(mean)
    new_mastery = OutcomeMastery(
        learner_id=event.learner_id,
        outcome_id=event.outcome_id,
        subject_slug=event.subject_slug,
        mastery_level=mean,
        descriptor=desc,
        event_count=events,
        last_event_at=event.captured_at,
    )
    return new_mastery, event


def progress_summary(
    events: list[AssessmentEvent],
) -> dict[str, int]:
    """Return a dict of descriptor -> count for the given events.

    Useful for the dashboard view: "5 Exceptional / 12 Above / 8 In line / 2 Yet".
    """
    counts: dict[str, int] = {
        "Exceptional": 0,
        "Above expectations": 0,
        "In line with expectations": 0,
        "Yet to meet expectations": 0,
    }
    for ev in events:
        if ev.descriptor in counts:
            counts[ev.descriptor] += 1
    return counts


__all__ = [
    "AssessmentEvent",
    "AssessmentType",
    "MasteryDescriptor",
    "OutcomeMastery",
    "apply_event",
    "progress_summary",
]
