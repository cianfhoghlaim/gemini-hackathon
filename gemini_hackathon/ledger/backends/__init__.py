"""gemini_hackathon.ledger.backends — the 3 ledger backends (Google-native, Phase 6).

Convex + LanceDB + FalkorDB were replaced outright (not migrated — none
of the three was ever actually deployed; see each module's docstring)
with a single Firestore-first substrate:

  - FirestoreLedger        (was ConvexLedger)         — UI-facing rows
  - FirestoreMasteryVectors (was LanceMasteryVectors)  — per-learner
    mastery fingerprints, via the Phase 2 VectorTarget (Firestore
    FindNearest / Vertex AI Vector Search)
  - FirestoreSkillGraph    (was FalkorSkillGraph)      — skill-prerequisite graph
"""

from gemini_hackathon.ledger.backends.firestore_graph import FirestoreSkillGraph
from gemini_hackathon.ledger.backends.firestore_ledger import FirestoreLedger
from gemini_hackathon.ledger.backends.firestore_vectors import FirestoreMasteryVectors

__all__ = [
    "FirestoreLedger",
    "FirestoreMasteryVectors",
    "FirestoreSkillGraph",
]
