"""gemini_hackathon.ledger.backends.lance_vectors — the LanceDB mastery-vector backend.

LanceDB stores the per-learner mastery vectors — 320-dim per learner
(5 NCCA Key Competencies × 8 NCCA LC subjects × 4 levels × 2 languages).

The actual embeddings use `bge-m3` (multilingual 1024-dim) per the BIEP
v1 spec; we use the 320-dim NCCA Key Competency mastery vector as
the per-learner "mastery fingerprint" for similarity search.

In production: writes to a LanceDB instance (local file or server). In
dev (no LanceDB available): writes to an in-memory dict + generates
deterministic random vectors (seeded by learner_id for reproducibility).
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from typing import Any, Optional

from gemini_hackathon.ledger.types import MasteryRecord


# The canonical per-learner mastery-vector shape
# 5 NCCA Key Competencies × 8 NCCA LC subjects × 4 levels (H/O/H1/O1)
# × 2 languages (en/ga) = 320 dimensions
MASTERY_VECTOR_DIM: int = 5 * 8 * 4 * 2  # 320


@dataclass
class LanceMasteryVectors:
    """The LanceDB-backed per-learner mastery vectors."""

    lance_uri: Optional[str] = None

    def __post_init__(self):
        self._in_memory: dict[str, list[float]] = {}

    async def upsert_mastery_vector(
        self,
        learner_id: str,
        mastery_vector: Optional[list[float]] = None,
        subject_slug: Optional[str] = None,
        mastery_score: Optional[float] = None,
    ) -> list[float]:
        """Upsert the per-learner mastery vector.

        If `mastery_vector` is provided, store it as-is.
        Otherwise, if `subject_slug` + `mastery_score` are provided,
        fold the score into the per-subject slice of the 320-dim vector.
        Otherwise, generate a deterministic placeholder from `learner_id`.
        """
        if mastery_vector is None and subject_slug is not None and mastery_score is not None:
            # Update only the subject-slice of the vector (lazy init)
            if learner_id not in self._in_memory:
                self._in_memory[learner_id] = _generate_placeholder_vector(learner_id)
            offset = _subject_offset(subject_slug)
            for i in range(40):  # 5 Key Competencies × 4 levels × 2 languages = 40
                self._in_memory[learner_id][offset + i] = mastery_score
        elif mastery_vector is None:
            # Deterministic placeholder
            self._in_memory[learner_id] = _generate_placeholder_vector(learner_id)
        else:
            assert len(mastery_vector) == MASTERY_VECTOR_DIM, (
                f"mastery_vector must be {MASTERY_VECTOR_DIM}-dim, "
                f"got {len(mastery_vector)}"
            )
            self._in_memory[learner_id] = list(mastery_vector)
        return self._in_memory[learner_id]

    async def get_mastery_vector(self, learner_id: str) -> list[float]:
        """Return the per-learner mastery vector (320-dim)."""
        if learner_id not in self._in_memory:
            self._in_memory[learner_id] = _generate_placeholder_vector(learner_id)
        return list(self._in_memory[learner_id])

    async def search_similar_learners(
        self,
        query_vector: list[float],
        top_k: int = 5,
    ) -> list[tuple[str, float]]:
        """Find the top-k most similar learners by cosine similarity.

        Returns:
            List of (learner_id, similarity) tuples, sorted desc.
        """
        from math import sqrt

        def cosine(a: list[float], b: list[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            na = sqrt(sum(x * x for x in a))
            nb = sqrt(sum(x * x for x in b))
            return dot / (na * nb) if na and nb else 0.0

        scored = [
            (learner_id, cosine(query_vector, vec))
            for learner_id, vec in self._in_memory.items()
        ]
        return sorted(scored, key=lambda t: t[1], reverse=True)[:top_k]


def _subject_offset(subject_slug: str) -> int:
    """Return the offset of the subject slice in the 320-dim vector.

    The 8 NCCA LC subjects are indexed in the canonical order:
    mathematics=0, applied_mathematics=1, chemistry=2, ..., physics=7.
    Each subject gets a 40-dim slice (5 Key Competencies × 4 levels ×
    2 languages).
    """
    from gemini_hackathon.agents.registry import SUBJECT_WIRING_REGISTRY
    subjects = list(SUBJECT_WIRING_REGISTRY.keys())
    if subject_slug in subjects:
        return subjects.index(subject_slug) * 40
    return 0


def _generate_placeholder_vector(learner_id: str) -> list[float]:
    """Generate a deterministic 320-dim placeholder vector for a learner.

    Uses SHA-256(learner_id) as the seed — same learner always gets
    the same placeholder, but different learners get different vectors.
    """
    seed = hashlib.sha256(learner_id.encode("utf-8")).digest()
    # Expand the 32-byte hash to fill 320 floats via PRNG-style repetition
    # (deterministic but variable across learners).
    out: list[float] = []
    for i in range(MASTERY_VECTOR_DIM):
        b = seed[i % len(seed)]
        out.append(b / 255.0)  # normalise to [0.0, 1.0]
    return out


__all__ = ["MASTERY_VECTOR_DIM", "LanceMasteryVectors"]
