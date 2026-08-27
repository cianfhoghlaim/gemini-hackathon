"""gemini_hackathon.ledger — the skill-progression ledger.

3-layer persistence + the unified `MasteryLedger` API:

  - Convex (`ConvexLedger`): per-learner achievement ledger rows (UI-facing).
    The schema: `achievements: {learner_id, subject_slug, outcome_code,
    mastery_score, evidence_id[], unlocked_by, awarded_certificate_ids}[]`.

  - LanceDB (`LanceMasteryVectors`): per-learner mastery vectors (320-dim
    per the BIEP v1 spec — 5 NCCA Key Competencies × 8 subjects ×
    4 levels × 2 languages). Backed by `bge-m3` embeddings.

  - FalkorDB (`FalkorSkillGraph`): the skill-prerequisite graph.
    Nodes: Skill (per learning outcome). Edges: PREREQUISITE_OF,
    ASSESSED_BY_ARTEFACT, UNLOCKS, CONTRIBUTES_TO_COMPETENCY.

The `MasteryLedger` facade unifies all 3 + the markdown memory layer
(gemini_hackathon/memory/MarkdownMemoryService — W8) into a single
read/write API. Every mastery update writes to all 3 backends + the
markdown memory, atomically (best-effort).

Driven by:
  - The W7 ADK 2 stage coordinators (`agents/stages/cross_subject/`)
    — the 5 NCCA Key Competencies fan-out writes here
  - The W14 LC/JC certificate pipeline — reads the per-learner mastery
    vector to populate the certificate
"""

from gemini_hackathon.ledger.types import (
    MasteryRecord,
    MasteryUpdate,
    AchievementRecord,
    SkillGraphNode,
    SkillGraphEdge,
)
from gemini_hackathon.ledger.backends.convex_ledger import ConvexLedger
from gemini_hackathon.ledger.backends.lance_vectors import LanceMasteryVectors
from gemini_hackathon.ledger.backends.falkor_graph import FalkorSkillGraph
from gemini_hackathon.ledger.mastery_ledger import MasteryLedger


__all__ = [
    "MasteryRecord",
    "MasteryUpdate",
    "AchievementRecord",
    "SkillGraphNode",
    "SkillGraphEdge",
    "ConvexLedger",
    "LanceMasteryVectors",
    "FalkorSkillGraph",
    "MasteryLedger",
]
