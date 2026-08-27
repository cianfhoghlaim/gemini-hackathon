"""gemini_hackathon.ledger.types — the data types for the skill-progression ledger."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class MasteryRecord:
    """A single learning-outcome mastery entry for a learner.

    Per the canonical 8-field SubjectAgentWiring extended with
    learner_id + mastery_score.
    """

    learner_id: str
    subject_slug: str  # one of the 14 NCCA_LC_SUBJECTS
    learning_outcome_code: str  # e.g. "MA-LC-CH-2.1"
    stage: str  # "aistear" / "bunscoil" / "meanscoil" / "scoil_sinsearach" / "ollscoil"
    mastery_score: float  # 0.0-1.0
    formative_evidence_ids: list[str] = field(default_factory=list)
    # Bloom level (from the BAML extract)
    bloom_level: str = "understand"
    # 5 NCCA Key Competencies (lifted from W8)
    key_competency_codes: list[str] = field(default_factory=list)
    # Spaced repetition metadata
    next_review_date: Optional[str] = None  # ISO datetime
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class MasteryUpdate:
    """An update event to apply to the ledger (written by the W7 cross-subject fan-out)."""

    record: MasteryRecord
    delta: float = 0.0  # the mastery-score delta (e.g. +0.05)
    evidence_id: str = ""  # the formative exit-card ID
    source_module: str = ""  # "cross_subject_fan_out" | "manual" | "exit_card"


@dataclass
class AchievementRecord:
    """An achievement ledger row (the Convex-facing view).

    This is what the editorial canvas UI surfaces in the per-learner
    skill progression sidebar.
    """

    learner_id: str
    subject_slug: str
    learning_outcome_code: str
    mastery_score: float
    unlocked_outcome_codes: list[str] = field(default_factory=list)
    # The 5 NCCA Key Competencies this outcome contributes to
    key_competency_codes: list[str] = field(default_factory=list)
    # Evidence IDs (the formative exit cards + topic mastery events)
    evidence_ids: list[str] = field(default_factory=list)
    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class SkillGraphNode:
    """A node in the FalkorDB skill-prerequisite graph."""

    node_id: str  # canonical learning outcome code (e.g. "MA-LC-CH-2.1")
    subject_slug: str
    learning_outcome_code: str
    description: str
    bloom_level: str = "understand"
    # The 5 NCCA Key Competencies this outcome develops
    contributes_to: list[str] = field(default_factory=list)


@dataclass
class SkillGraphEdge:
    """An edge in the FalkorDB skill-prerequisite graph."""

    edge_type: str  # "PREREQUISITE_OF" | "ASSESSED_BY" | "UNLOCKS" | "CONTRIBUTES_TO"
    from_node_id: str
    to_node_id: str
    weight: float = 1.0  # the strength of the relationship
    metadata: dict[str, Any] = field(default_factory=dict)


__all__ = [
    "MasteryRecord",
    "MasteryUpdate",
    "AchievementRecord",
    "SkillGraphNode",
    "SkillGraphEdge",
]
