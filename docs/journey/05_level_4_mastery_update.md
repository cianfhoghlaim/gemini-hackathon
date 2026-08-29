# Level 4 — Update the mastery ledger

> **`MasteryLedger.update_mastery()` writes to all 4 backends in one shot
> (Firestore ledger + Firestore/Vector-Search mastery vectors + Firestore
> skill graph + GCS Markdown memory).** Mirrors Phase 6's
> `MasteryLedger` facade; the journey just calls it and surfaces the
> per-backend status to the studio.

The single-node ADK 2 Workflow:

```
START -> update_mastery_node -> (HITL pause: RequestInput) -> next_level
```

## What you'll learn

| Concept | Source |
|---|---|
| **MasteryLedger facade** | `gemini_hackathon.ledger.MasteryLedger` (Phase 6) |
| **Firestore 4-backend fan-out** | `FirestoreLedger` + `FirestoreMasteryVectors` + `FirestoreSkillGraph` + Markdown |
| **HITL pause** | `RequestInput` event (per `loop-lab-table/hello_workflow.py`) |
| **Per-backend status board** | A Gradio `gr.JSON` showing each backend's OK/WARN |

## What you'll build

By the end of Level 4:
- `FirestoreLedger.upsert_achievement()` writes the achievement row
- `FirestoreMasteryVectors.upsert_mastery_vector()` writes the 320-dim vector
- `FirestoreSkillGraph.upsert_edge()` adds an UNLOCKS edge
- Markdown memory session persisted (optional)
- The studio's "Mastery update" tab shows the per-backend status board

## Prerequisites

- Level 3 completed (you have a recorded grade to update the mastery with)
- A `learner_id` + subject slug + outcome code

## Quickstart

```bash
# 1. Launch the studio
python -m gemini_hackathon.journey.level_4_mastery_update.app --port 7864

# 2. In the UI:
#    - learner_id:    alice@school.ie
#    - subject_slug:  mathematics
#    - outcome_code:  MA-LC-MA-1.1
#    - mastery_score: 0.78
#    - Click "Update mastery"
#
# 3. The per-backend status board appears:
#    - firestore_achievements: OK — 1 row(s)
#    - mastery_vector:         OK — 320-dim Firestore/Vector-Search upsert
#    - skill_graph:            OK — UNLOCKS edge added
#    - markdown_memory:        OK — session persisted
```

## Why this matters (per `docs/ideas/Ontology and Temporal Graphs Research.md`)

`MasteryLedger` is the unified **temporal ontology** entry point that
the British Isles education platform writes to. Every level-up, every
exit-card result, every formative assessment updates the same 4-backends.
The skill graph (Firestore `skillEdges`) preserves prerequisite
relationships — the next time the workshop host runs this journey with a
learner, they can ask "what's the next step for this learner?" and
traverse the graph from the just-unlocked outcome.

## HITL pause between Level 4 and Level 5

After Level 4 confirms, the orchestrator emits a `RequestInput` event
(per `loop-lab-table/hello_workflow.py`). The studio's "Continue to
Level 5?" button is the participant's confirmation; the ADK Runner
pauses until they click it. This is the human-in-the-loop checkpoint
where a workshop host can review the per-backend status board before
generating an asset.
