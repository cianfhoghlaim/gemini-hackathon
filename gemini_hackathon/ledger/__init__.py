"""gemini_hackathon.ledger — the skill-progression ledger.

Google-native persistence (Phase 6 of the GCP-first refactor) + the
unified `MasteryLedger` API:

  - Firestore (`FirestoreLedger`): per-learner achievement ledger rows
    (UI-facing). The schema: `learners/{learner_id}/achievements/
    {subject_slug}__{learning_outcome_code}: {mastery_score,
    unlocked_outcome_codes, key_competency_codes, evidence_ids,
    created_at, last_updated}`.

  - Firestore/Vertex AI Vector Search (`FirestoreMasteryVectors`):
    per-learner mastery vectors (320-dim — 5 NCCA Key Competencies x
    8 subjects x 4 levels x 2 languages), via the same dual-backed
    `VectorTarget` the CocoIndex embedding layer uses (Phase 2).

  - Firestore (`FirestoreSkillGraph`): the skill-prerequisite graph.
    Nodes: Skill (per learning outcome). Edges: PREREQUISITE_OF,
    ASSESSED_BY_ARTEFACT, UNLOCKS, CONTRIBUTES_TO_COMPETENCY.

Replaces Convex + LanceDB + FalkorDB outright — none of the three was
ever actually deployed (each backend's own prior docstring described an
in-memory-only fallback with the real deployment "deferred"), so this is
a clean swap to a single Google-native substrate, not a migration.

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

from gemini_hackathon.ledger.backends.firestore_graph import FirestoreSkillGraph
from gemini_hackathon.ledger.backends.firestore_ledger import FirestoreLedger
from gemini_hackathon.ledger.backends.firestore_vectors import FirestoreMasteryVectors
from gemini_hackathon.ledger.mastery_ledger import MasteryLedger
from gemini_hackathon.ledger.types import (
    AchievementRecord,
    MasteryRecord,
    MasteryUpdate,
    SkillGraphEdge,
    SkillGraphNode,
)

__all__ = [
    "AchievementRecord",
    "FirestoreLedger",
    "FirestoreMasteryVectors",
    "FirestoreSkillGraph",
    "MasteryLedger",
    "MasteryRecord",
    "MasteryUpdate",
    "SkillGraphEdge",
    "SkillGraphNode",
]
