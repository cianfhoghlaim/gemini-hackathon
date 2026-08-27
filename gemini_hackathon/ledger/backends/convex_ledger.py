"""gemini_hackathon.ledger.backends.convex_ledger — the Convex ledger backend.

Convex is the **UI-facing** backend. The schema:

    achievements: {learner_id, subject_slug, outcome_code, mastery_score,
                  evidence_id[], unlocked_by, awarded_certificate_ids,
                  created_at, last_updated}

This module defines the backend + the read/write operations. The
schema is the canonical schema consumed by `web/convex/` (the TanStack
web app) and by the editorial canvas's per-learner skill-progression
sidebar.

The actual Convex deployment is deferred to the W12 Cloud Run deploy
(same pattern as `web/convex/schema.ts`). For dev, the in-memory
fallback keeps the read/write API working.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Optional

from gemini_hackathon.ledger.types import AchievementRecord, MasteryRecord


# The canonical Convex schema (mirrors web/convex/schema.ts:achievements)
CONVEX_ACHIEVEMENTS_SCHEMA: dict[str, Any] = {
    "learner_id": str,
    "subject_slug": str,
    "learning_outcome_code": str,
    "mastery_score": float,  # 0.0-1.0
    "unlocked_outcome_codes": list[str],
    "key_competency_codes": list[str],  # 5 NCCA Key Competencies
    "evidence_ids": list[str],
    "created_at": str,
    "last_updated": str,
}


@dataclass
class ConvexLedger:
    """The Convex-backed ledger.

    In production: writes to a Convex deployment via the convex Python
    SDK. In dev (no Convex URL set): writes to an in-memory dict.
    """

    convex_url: Optional[str] = None

    def __post_init__(self):
        self._in_memory: dict[str, AchievementRecord] = {}

    async def upsert_achievement(
        self,
        learner_id: str,
        subject_slug: str,
        learning_outcome_code: str,
        mastery_score: float,
        key_competency_codes: list[str] | None = None,
        evidence_ids: list[str] | None = None,
    ) -> AchievementRecord:
        """Upsert one achievement row.

        The key is `(learner_id, subject_slug, learning_outcome_code)`.
        """
        key = f"{learner_id}|{subject_slug}|{learning_outcome_code}"
        existing = self._in_memory.get(key)
        now = datetime.now().isoformat()
        if existing is not None:
            existing.mastery_score = max(existing.mastery_score, mastery_score)
            existing.last_updated = now
            existing.key_competency_codes = list(
                set(existing.key_competency_codes + (key_competency_codes or []))
            )
            existing.evidence_ids = list(
                set(existing.evidence_ids + (evidence_ids or []))
            )
            record = existing
        else:
            record = AchievementRecord(
                learner_id=learner_id,
                subject_slug=subject_slug,
                learning_outcome_code=learning_outcome_code,
                mastery_score=mastery_score,
                key_competency_codes=list(key_competency_codes or []),
                evidence_ids=list(evidence_ids or []),
                created_at=now,
                last_updated=now,
            )
        self._in_memory[key] = record
        return record

    async def get_achievements(
        self,
        learner_id: str,
        subject_slug: str | None = None,
    ) -> list[AchievementRecord]:
        """Return all achievements for a learner (optionally filtered by subject)."""
        results = []
        for record in self._in_memory.values():
            if record.learner_id != learner_id:
                continue
            if subject_slug and record.subject_slug != subject_slug:
                continue
            results.append(record)
        return sorted(results, key=lambda r: r.mastery_score, reverse=True)

    async def compute_skill_progression_summary(
        self,
        learner_id: str,
    ) -> dict[str, Any]:
        """Compute the per-learner skill progression summary.

        Returns:
            {
              "total_outcomes": 100,
              "mastered_outcomes": 47,
              "average_mastery": 0.78,
              "per_subject_mastery": {"mathematics": 0.85, ...},
              "per_competency_mastery": {"communicating": 0.92, ...},
            }
        """
        achievements = await self.get_achievements(learner_id)
        if not achievements:
            return {
                "total_outcomes": 0,
                "mastered_outcomes": 0,
                "average_mastery": 0.0,
                "per_subject_mastery": {},
                "per_competency_mastery": {},
            }

        per_subject: dict[str, list[float]] = {}
        per_competency: dict[str, list[float]] = {}
        for a in achievements:
            per_subject.setdefault(a.subject_slug, []).append(a.mastery_score)
            for kc in a.key_competency_codes:
                per_competency.setdefault(kc, []).append(a.mastery_score)
        return {
            "total_outcomes": len(achievements),
            "mastered_outcomes": sum(1 for a in achievements if a.mastery_score >= 0.8),
            "average_mastery": sum(a.mastery_score for a in achievements) / len(achievements),
            "per_subject_mastery": {
                s: sum(scores) / len(scores) for s, scores in per_subject.items()
            },
            "per_competency_mastery": {
                c: sum(scores) / len(scores) for c, scores in per_competency.items()
            },
        }


__all__ = ["CONVEX_ACHIEVEMENTS_SCHEMA", "ConvexLedger"]
