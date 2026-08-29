"""gemini_hackathon.ledger.backends.firestore_ledger — the Firestore ledger backend.

Phase 6 of the GCP-first refactor — replaces `ConvexLedger`. Convex was
never actually deployed: its own prior docstring said "the actual Convex
deployment is deferred… for dev, the in-memory fallback keeps the
read/write API working" and every method only ever touched an in-memory
dict. There is no live Convex data to migrate — this is a clean swap, not
a migration.

Firestore is the **UI-facing** backend. Collection layout:

    learners/{learner_id}/achievements/{subject_slug}__{learning_outcome_code}

Mirrors the same 3-method shape `ConvexLedger` had
(`upsert_achievement` / `get_achievements` / `compute_skill_progression_summary`)
so `MasteryLedger` and every call site need zero interface changes.

In production (`GCP_PROJECT_ID` set + `google-cloud-firestore` installed):
writes to a real Firestore database. In dev/offline: falls back to the
same in-memory dict the original always used — the read/write API works
identically either way.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import structlog

from gemini_hackathon.ledger.types import AchievementRecord

logger = structlog.get_logger(__name__)

try:
    from google.cloud import firestore

    FIRESTORE_AVAILABLE = True
except ImportError:
    FIRESTORE_AVAILABLE = False
    firestore = None  # type: ignore[assignment]


# The canonical Firestore schema (mirrors the achievement shape the
# editorial canvas UI's `web/src/lib/firestore.ts` COLLECTIONS registry
# reads from — `achievements` documents nested under `learners/{uid}`).
FIRESTORE_ACHIEVEMENTS_SCHEMA: dict[str, Any] = {
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
class FirestoreLedger:
    """The Firestore-backed ledger.

    In production: writes to `learners/{learner_id}/achievements/{doc_id}`
    via `google-cloud-firestore`. In dev (no `GCP_PROJECT_ID` or the
    library isn't installed): writes to an in-memory dict — the same
    fallback the original `ConvexLedger` always used.
    """

    project_id: str | None = None

    def __post_init__(self) -> None:
        self._in_memory: dict[str, AchievementRecord] = {}
        self._client: Any = None
        if FIRESTORE_AVAILABLE and self.project_id:
            try:
                self._client = firestore.Client(project=self.project_id)
            except Exception:
                logger.exception("FirestoreLedger: client init failed, using in-memory fallback")
                self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    @staticmethod
    def _doc_id(subject_slug: str, learning_outcome_code: str) -> str:
        return f"{subject_slug}__{learning_outcome_code}"

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
        now = datetime.now(tz=UTC).isoformat()
        doc_id = self._doc_id(subject_slug, learning_outcome_code)

        if self.available:
            doc_ref = (
                self._client.collection("learners")
                .document(learner_id)
                .collection("achievements")
                .document(doc_id)
            )
            snapshot = doc_ref.get()
            if snapshot.exists:
                existing = snapshot.to_dict()
                record = AchievementRecord(
                    learner_id=learner_id,
                    subject_slug=subject_slug,
                    learning_outcome_code=learning_outcome_code,
                    mastery_score=max(existing.get("mastery_score", 0.0), mastery_score),
                    unlocked_outcome_codes=existing.get("unlocked_outcome_codes", []),
                    key_competency_codes=list(
                        set(existing.get("key_competency_codes", []) + (key_competency_codes or []))
                    ),
                    evidence_ids=list(set(existing.get("evidence_ids", []) + (evidence_ids or []))),
                    created_at=existing.get("created_at", now),
                    last_updated=now,
                )
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
            doc_ref.set(
                {
                    "learner_id": record.learner_id,
                    "subject_slug": record.subject_slug,
                    "learning_outcome_code": record.learning_outcome_code,
                    "mastery_score": record.mastery_score,
                    "unlocked_outcome_codes": record.unlocked_outcome_codes,
                    "key_competency_codes": record.key_competency_codes,
                    "evidence_ids": record.evidence_ids,
                    "created_at": record.created_at,
                    "last_updated": record.last_updated,
                }
            )
            return record

        # In-memory fallback.
        key = f"{learner_id}|{subject_slug}|{learning_outcome_code}"
        existing = self._in_memory.get(key)
        if existing is not None:
            existing.mastery_score = max(existing.mastery_score, mastery_score)
            existing.last_updated = now
            existing.key_competency_codes = list(
                set(existing.key_competency_codes + (key_competency_codes or []))
            )
            existing.evidence_ids = list(set(existing.evidence_ids + (evidence_ids or [])))
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
        if self.available:
            collection = self._client.collection("learners").document(learner_id).collection("achievements")
            query = collection.where("subject_slug", "==", subject_slug) if subject_slug else collection
            results = [
                AchievementRecord(**doc.to_dict()) for doc in query.stream()
            ]
            return sorted(results, key=lambda r: r.mastery_score, reverse=True)

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


__all__ = ["FIRESTORE_ACHIEVEMENTS_SCHEMA", "FirestoreLedger"]
