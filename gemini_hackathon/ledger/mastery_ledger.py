"""gemini_hackathon.ledger.mastery_ledger — the unified MasteryLedger facade.

The MasteryLedger unifies the 3 backends (Convex + LanceDB + FalkorDB)
+ the markdown memory layer (W8) into a single read/write API.

Every `update_mastery()` call writes to all 4 backends + memory
(best-effort: failures in one backend don't fail the whole operation).

This is the single API consumed by:
  - The W7 ADK 2 stage coordinators (`agents/stages/cross_subject/`)
  - The W14 certificate pipeline (reads the per-learner mastery state)
  - The editorial canvas UI (via `web/convex/` — the Convex-backed view)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from gemini_hackathon.ledger.types import (
    AchievementRecord,
    MasteryRecord,
    MasteryUpdate,
)


_log = logging.getLogger(__name__)


@dataclass
class MasteryLedger:
    """The unified mastery ledger facade.

    Combines:
      - ConvexLedger (UI-facing per-learner achievement rows)
      - LanceMasteryVectors (320-dim per-learner mastery vectors)
      - FalkorSkillGraph (skill-prerequisite graph)
      - MarkdownMemoryService (W8 long-term memory)
    """

    convex: object = field(default=None)  # ConvexLedger
    lance: object = field(default=None)  # LanceMasteryVectors
    falkor: object = field(default=None)  # FalkorSkillGraph
    memory: object = field(default=None)  # MarkdownMemoryService

    @classmethod
    def default(cls) -> "MasteryLedger":
        """Create a dev-friendly default ledger (in-memory backends + memory)."""
        from gemini_hackathon.ledger.backends.convex_ledger import ConvexLedger
        from gemini_hackathon.ledger.backends.lance_vectors import LanceMasteryVectors
        from gemini_hackathon.ledger.backends.falkor_graph import FalkorSkillGraph

        convex = ConvexLedger()
        lance = LanceMasteryVectors()
        falkor = FalkorSkillGraph()
        falkor.seed_default_ireland_lc_graph()

        # Memory is optional (requires google-adk + tempfile setup)
        memory = None
        try:
            from gemini_hackathon.memory.markdown import MarkdownMemoryService
            memory = MarkdownMemoryService(root="/tmp/gemini_hackathon_memory")
        except ImportError:
            pass

        return cls(convex=convex, lance=lance, falkor=falkor, memory=memory)

    async def update_mastery(self, update: MasteryUpdate) -> MasteryRecord:
        """Apply one mastery update across all backends (best-effort).

        Writes:
          - The achievement record to Convex (UI-facing)
          - The per-subject mastery slice to LanceDB (mastery vectors)
          - The graph UNLOCKS edge to FalkorDB (skill progression)
          - The event to MarkdownMemoryService (long-term memory)
        """
        record = update.record

        # 1. Convex (UI-facing)
        if self.convex is not None:
            try:
                await self.convex.upsert_achievement(
                    learner_id=record.learner_id,
                    subject_slug=record.subject_slug,
                    learning_outcome_code=record.learning_outcome_code,
                    mastery_score=record.mastery_score,
                    key_competency_codes=record.key_competency_codes,
                    evidence_ids=record.formative_evidence_ids,
                )
            except Exception as e:
                _log.warning("Convex upsert failed: %s", e)

        # 2. LanceDB (mastery vectors)
        if self.lance is not None:
            try:
                # Update only the subject slice of the 320-dim vector
                await self.lance.upsert_mastery_vector(
                    learner_id=record.learner_id,
                    subject_slug=record.subject_slug,
                    mastery_score=record.mastery_score,
                )
            except Exception as e:
                _log.warning("Lance upsert failed: %s", e)

        # 3. FalkorDB (skill graph)
        if self.falkor is not None:
            try:
                from gemini_hackathon.ledger.types import SkillGraphEdge

                # The mastery event unlocks the next outcome in the same subject
                next_outcome_code = self._infer_next_outcome(
                    record.subject_slug, record.learning_outcome_code
                )
                if next_outcome_code:
                    self.falkor.upsert_edge(SkillGraphEdge(
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
                _log.warning("Falkor upsert failed: %s", e)

        # 4. MarkdownMemoryService (long-term memory)
        if self.memory is not None and update.evidence_id:
            try:
                # Build a fake Session-like object from the update record
                from google.genai import types as gtypes
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

        # Convex (UI-facing achievement rows)
        if self.convex is not None:
            try:
                state["achievements"] = await self.convex.get_achievements(learner_id)
                state["summary"] = (
                    await self.convex.compute_skill_progression_summary(learner_id)
                )
            except Exception as e:
                _log.warning("Convex read failed: %s", e)
                state["achievements"] = []
                state["summary"] = {}

        # LanceDB (mastery vectors)
        if self.lance is not None:
            try:
                state["mastery_vector"] = await self.lance.get_mastery_vector(learner_id)
            except Exception as e:
                _log.warning("Lance read failed: %s", e)
                state["mastery_vector"] = []

        # FalkorDB (skill graph)
        if self.falkor is not None:
            try:
                state["graph"] = self.falkor.get_full_graph()
            except Exception as e:
                _log.warning("Falkor read failed: %s", e)
                state["graph"] = {}

        return state

    @staticmethod
    def _infer_next_outcome(
        subject_slug: str, current_outcome_code: str
    ) -> str | None:
        """Infer the next outcome in the subject sequence.

        For "MA-LC-MA-1.1" → "MA-LC-MA-1.2" (increment the trailing
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
