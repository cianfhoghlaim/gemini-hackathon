"""gemini_hackathon.ledger.mastery_ledger — the unified MasteryLedger facade.

Phase 6 of the GCP-first refactor: the MasteryLedger unifies the 3
Google-native backends (Firestore ledger + Firestore/Vertex-Vector-Search
mastery vectors + Firestore skill graph) + the markdown memory layer (W8)
into a single read/write API. Replaces the prior Convex + LanceDB +
FalkorDB trio outright (none of the three was ever actually deployed —
see `ledger/backends/__init__.py`).

Every `update_mastery()` call writes to all 4 backends + memory
(best-effort: failures in one backend don't fail the whole operation).

This is the single API consumed by:
  - The W7 ADK 2 stage coordinators (`agents/stages/cross_subject/`)
  - The W14 certificate pipeline (reads the per-learner mastery state)
  - The editorial canvas UI (via Firestore realtime `onSnapshot` —
    `web/src/lib/firestore.ts`)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from gemini_hackathon.ledger.types import (
    MasteryRecord,
    MasteryUpdate,
)

_log = logging.getLogger(__name__)


@dataclass
class MasteryLedger:
    """The unified mastery ledger facade.

    Combines:
      - FirestoreLedger (UI-facing per-learner achievement rows)
      - FirestoreMasteryVectors (320-dim per-learner mastery vectors)
      - FirestoreSkillGraph (skill-prerequisite graph)
      - MarkdownMemoryService (W8 long-term memory)
    """

    firestore_ledger: object = field(default=None)  # FirestoreLedger
    mastery_vectors: object = field(default=None)  # FirestoreMasteryVectors
    skill_graph: object = field(default=None)  # FirestoreSkillGraph
    memory: object = field(default=None)  # MarkdownMemoryService

    @classmethod
    def default(cls) -> MasteryLedger:
        """Create a dev-friendly default ledger (Firestore-backed when
        `GCP_PROJECT_ID` is set, else the same in-memory fallback every
        backend has always used)."""
        import os

        from gemini_hackathon.ledger.backends.firestore_graph import FirestoreSkillGraph
        from gemini_hackathon.ledger.backends.firestore_ledger import FirestoreLedger
        from gemini_hackathon.ledger.backends.firestore_vectors import FirestoreMasteryVectors

        project_id = os.environ.get("GCP_PROJECT_ID")
        firestore_ledger = FirestoreLedger(project_id=project_id)
        mastery_vectors = FirestoreMasteryVectors()
        skill_graph = FirestoreSkillGraph(project_id=project_id)
        skill_graph.seed_default_ireland_lc_graph()

        # Memory is optional (requires google-adk + tempfile setup)
        memory = None
        try:
            from gemini_hackathon.memory.markdown import MarkdownMemoryService
            memory = MarkdownMemoryService(root="/tmp/gemini_hackathon_memory")
        except ImportError:
            pass

        return cls(
            firestore_ledger=firestore_ledger,
            mastery_vectors=mastery_vectors,
            skill_graph=skill_graph,
            memory=memory,
        )

    async def update_mastery(self, update: MasteryUpdate) -> MasteryRecord:
        """Apply one mastery update across all backends (best-effort).

        Writes:
          - The achievement record to Firestore (UI-facing)
          - The per-subject mastery slice to the mastery-vector store
          - The graph UNLOCKS edge to the Firestore skill graph
          - The event to MarkdownMemoryService (long-term memory)
        """
        record = update.record

        # 1. Firestore (UI-facing)
        if self.firestore_ledger is not None:
            try:
                await self.firestore_ledger.upsert_achievement(
                    learner_id=record.learner_id,
                    subject_slug=record.subject_slug,
                    learning_outcome_code=record.learning_outcome_code,
                    mastery_score=record.mastery_score,
                    key_competency_codes=record.key_competency_codes,
                    evidence_ids=record.formative_evidence_ids,
                )
            except Exception as e:
                _log.warning("Firestore ledger upsert failed: %s", e)

        # 2. Mastery-vector store
        if self.mastery_vectors is not None:
            try:
                # Update only the subject slice of the 320-dim vector
                await self.mastery_vectors.upsert_mastery_vector(
                    learner_id=record.learner_id,
                    subject_slug=record.subject_slug,
                    mastery_score=record.mastery_score,
                )
            except Exception as e:
                _log.warning("Mastery-vector upsert failed: %s", e)

        # 3. Skill graph
        if self.skill_graph is not None:
            try:
                from gemini_hackathon.ledger.types import SkillGraphEdge

                # The mastery event unlocks the next outcome in the same subject
                next_outcome_code = self._infer_next_outcome(
                    record.subject_slug, record.learning_outcome_code
                )
                if next_outcome_code:
                    self.skill_graph.upsert_edge(SkillGraphEdge(
                        edge_type="UNLOCKS",
                        from_node_id=f"exit_card_{record.learning_outcome_code}",
                        to_node_id=next_outcome_code,
                        weight=1.0,
                        metadata={
                            "type": "formative_exit_card",
                            "learner_id": record.learner_id,
                            "evidence_id": update.evidence_id,
                            "source_module": update.source_module,
                        },
                    ))
            except Exception as e:
                _log.warning("Skill graph upsert failed: %s", e)

        # 4. MarkdownMemoryService (long-term memory)
        if self.memory is not None and update.evidence_id:
            try:
                session = self._build_session_from_update(update)
                await self.memory.add_session_to_memory(session)
            except Exception as e:
                _log.warning("Memory add failed: %s", e)

        return record

    async def get_learner_state(
        self,
        learner_id: str,
    ) -> dict:
        """Return the full learner state across all 3 backends.

        Used by the W14 certificate pipeline to populate the certificate.
        """
        state: dict = {"learner_id": learner_id}

        # Firestore (UI-facing achievement rows)
        if self.firestore_ledger is not None:
            try:
                state["achievements"] = await self.firestore_ledger.get_achievements(learner_id)
                state["summary"] = (
                    await self.firestore_ledger.compute_skill_progression_summary(learner_id)
                )
            except Exception as e:
                _log.warning("Firestore ledger read failed: %s", e)
                state["achievements"] = []
                state["summary"] = {}

        # Mastery-vector store
        if self.mastery_vectors is not None:
            try:
                state["mastery_vector"] = await self.mastery_vectors.get_mastery_vector(learner_id)
            except Exception as e:
                _log.warning("Mastery-vector read failed: %s", e)
                state["mastery_vector"] = []

        # Skill graph
        if self.skill_graph is not None:
            try:
                state["graph"] = self.skill_graph.get_full_graph()
            except Exception as e:
                _log.warning("Skill graph read failed: %s", e)
                state["graph"] = {}

        return state

    @staticmethod
    def _infer_next_outcome(
        subject_slug: str, current_outcome_code: str
    ) -> str | None:
        """Infer the next outcome in the subject sequence.

        For "MA-LC-MA-1.1" -> "MA-LC-MA-1.2" (increment the trailing
        sub-number). For an outcome with no trailing number, return None.
        """
        import re

        m = re.match(r"^(.+?)(\d+)\.(\d+)$", current_outcome_code)
        if not m:
            return None
        head, major, minor = m.groups()
        return f"{head}{major}.{int(minor) + 1}"

    @staticmethod
    def _build_session_from_update(update: MasteryUpdate):
        """Build a google.adk Session-like object from a MasteryUpdate record."""
        from google.genai import types as gtypes

        r = update.record
        text = (
            f"Mastery update for {r.learner_id} on {r.subject_slug}/{r.learning_outcome_code}: "
            f"+{update.delta:.2f} = {r.mastery_score:.2f} "
            f"(evidence: {update.evidence_id}, source: {update.source_module})"
        )
        content = gtypes.Content(role="user", parts=[gtypes.Part(text=text)])
        event = type("_E", (), {"content": content})()
        session = type("_S", (), {
            "id": f"update-{update.evidence_id}",
            "user_id": r.learner_id,
            "events": [event],
        })()
        return session


__all__ = ["MasteryLedger"]
