"""gemini_hackathon.ledger.backends.firestore_vectors — the mastery-vector backend.

Phase 6 of the GCP-first refactor — replaces `LanceMasteryVectors`
(`./data/lancedb/gemini_hackathon.lance`, an ephemeral local file that
doesn't survive a Cloud Run cold start — see `_lifespan.py`'s Phase 2
notes).

Stores the per-learner mastery vectors — 320-dim per learner (5 NCCA Key
Competencies x 8 NCCA LC subjects x 4 levels x 2 languages). This is a
different vector than the CocoIndex text-chunk embeddings (1536-d
`gemini-embedding-001` from Phase 2) — it's a per-learner "mastery
fingerprint" used for `search_similar_learners()`, not RAG. It reuses the
same `cocoindex_flows._shared._vector_target.VectorTarget` protocol
(Firestore `FindNearest` by default) rather than inventing a second
storage mechanism — one dual-backed (Firestore/Vertex Vector Search)
vector abstraction for the whole repo.

In production: writes via `VectorTarget` (Firestore `FindNearest` by
default, or Vertex AI Vector Search via `VECTOR_BACKEND=vertex`). In dev
(no GCP): falls back to an in-memory dict + deterministic placeholder
vectors, matching the original `LanceMasteryVectors` fallback exactly.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from math import sqrt

from cocoindex_flows._shared._vector_target import VectorRow, get_vector_target

from gemini_hackathon.ledger.types import MasteryRecord  # noqa: F401 — re-exported for callers

# The canonical per-learner mastery-vector shape: 5 NCCA Key Competencies
# x 8 NCCA LC subjects x 4 levels (H/O/H1/O1) x 2 languages (en/ga) = 320
# dimensions. Well under Firestore's 2048-dim vector-field cap, so no
# Matryoshka truncation is needed here (unlike the 3072->1536 CocoIndex
# embedder cap in `_vertex_embedder.py`).
MASTERY_VECTOR_DIM: int = 5 * 8 * 4 * 2  # 320

#: The VectorTarget table name for learner mastery fingerprints.
MASTERY_VECTOR_TABLE = "learner_mastery_vectors"


@dataclass
class FirestoreMasteryVectors:
    """The Firestore/Vertex-Vector-Search-backed per-learner mastery vectors."""

    vector_backend: str | None = None  # "firestore" (default) | "vertex"

    def __post_init__(self) -> None:
        self._in_memory: dict[str, list[float]] = {}
        try:
            self._target = get_vector_target(backend=self.vector_backend)
        except Exception:
            self._target = None

    @property
    def available(self) -> bool:
        return self._target is not None and getattr(self._target, "available", False)

    async def upsert_mastery_vector(
        self,
        learner_id: str,
        mastery_vector: list[float] | None = None,
        subject_slug: str | None = None,
        mastery_score: float | None = None,
    ) -> list[float]:
        """Upsert the per-learner mastery vector.

        If `mastery_vector` is provided, store it as-is.
        Otherwise, if `subject_slug` + `mastery_score` are provided,
        fold the score into the per-subject slice of the 320-dim vector.
        Otherwise, generate a deterministic placeholder from `learner_id`.
        """
        if mastery_vector is None and subject_slug is not None and mastery_score is not None:
            current = self._in_memory.get(learner_id) or await self.get_mastery_vector(learner_id)
            offset = _subject_offset(subject_slug)
            for i in range(40):  # 5 Key Competencies x 4 levels x 2 languages = 40
                current[offset + i] = mastery_score
            vector = current
        elif mastery_vector is None:
            vector = _generate_placeholder_vector(learner_id)
        else:
            assert len(mastery_vector) == MASTERY_VECTOR_DIM, (
                f"mastery_vector must be {MASTERY_VECTOR_DIM}-dim, got {len(mastery_vector)}"
            )
            vector = list(mastery_vector)

        self._in_memory[learner_id] = vector
        if self.available:
            try:
                await self._target.upsert_batch(
                    [VectorRow(id=learner_id, table_name=MASTERY_VECTOR_TABLE, vector=vector, payload={})]
                )
            except Exception:
                pass  # in-memory copy above is the source of truth on failure
        return vector

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

        Uses `VectorTarget.find_nearest()` when available (Firestore
        `FindNearest` or Vertex AI Vector Search); falls back to an
        in-process cosine scan over the in-memory dict otherwise — same
        contract either way.
        """
        if self.available:
            try:
                matches = await self._target.find_nearest(
                    MASTERY_VECTOR_TABLE, query_vector, k=top_k
                )
                return [(m.id, m.score) for m in matches]
            except Exception:
                pass  # fall through to the in-memory scan below

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

    The 8 NCCA LC subjects are indexed in the canonical order per
    `SUBJECT_WIRING_REGISTRY`. Each subject gets a 40-dim slice
    (5 Key Competencies x 4 levels x 2 languages).
    """
    from gemini_hackathon.agents.registry import SUBJECT_WIRING_REGISTRY

    subjects = list(SUBJECT_WIRING_REGISTRY.keys())
    if subject_slug in subjects:
        return subjects.index(subject_slug) * 40
    return 0


def _generate_placeholder_vector(learner_id: str) -> list[float]:
    """Generate a deterministic 320-dim placeholder vector for a learner.

    Uses SHA-256(learner_id) as the seed — same learner always gets the
    same placeholder, but different learners get different vectors.
    """
    seed = hashlib.sha256(learner_id.encode("utf-8")).digest()
    out: list[float] = []
    for i in range(MASTERY_VECTOR_DIM):
        b = seed[i % len(seed)]
        out.append(b / 255.0)  # normalise to [0.0, 1.0]
    return out


__all__ = ["MASTERY_VECTOR_DIM", "MASTERY_VECTOR_TABLE", "FirestoreMasteryVectors"]
