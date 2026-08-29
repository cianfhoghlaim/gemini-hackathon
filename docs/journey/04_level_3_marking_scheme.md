# Level 3 — Mark an answer

> **Per-criterion graders (one BAML `ExtractMarkingSchemeGuideline` call per
> marking criterion) run in parallel via `ParallelAgent`. `JoinNode`
> aggregates into the strategy agent's input.** A real past-paper mark
> attempt — the same Pillar-1 pattern that powers `gemini_hackathon/
> agents/workflows/pillar1_grading.py`.

The 4-node ADK 2 Workflow:

```
START -> grade_criterion_1 ──┐
START -> grade_criterion_2 ──┼─► join_criterion_grades ─► synthesise_strategy
START -> grade_criterion_3 ──┘
```

Each `grade_criterion_N` is the same function node parameterized by the
per-criterion metadata. The strategy node writes the final grade
paragraph + cites the NCCA policy PDFs.

## What you'll learn

| Concept | Source |
|---|---|
| **Pillar-1 parallel grading** | `gemini_hackathon/agents/workflows/pillar1_grading.py` |
| **ParallelAgent + JoinNode** | `adk2-tutorial/L2a_parallel_join/workflow.py` |
| **BAML marking extraction** | `baml_extracts/subjects/<sub>.baml`'s marking functions |
| **Strategy synthesis** | one Agent node after the JoinNode (per `adk2-tutorial/L1_graph_basics`) |

## What you'll build

By the end of Level 3:
- 3 per-criterion grade dicts (`AO1`, `AO2`, `AO3` for Leaving Cert Maths)
- Total marks awarded + max
- Strategy summary paragraph citing the NCCA policy PDF
- The studio's "Mark an answer" tab shows all 3 criterion grades + total

## Prerequisites

- Level 0 completed (subject + subnation)
- A real student answer to mark (or use the default sine-rule demo answer)
- Optional: `baml-cli generate` has produced the BAML client

## Quickstart

```bash
# 1. Launch the studio
python -m gemini_hackathon.journey.level_3_marking_scheme.app --port 7863

# 2. In the UI:
#    - Subject:        mathematics
#    - Question ID:    Q5
#    - Student answer: "Using the sine rule: a/sin(A) = b/sin(B) = c/sin(C)
#                       ... so a = 5 cm, sin(A) = 0.5 → a = b·sin(A)/sin(B) = 4.3 cm"
#    - Click "Mark"
#
# 3. Inspect the result:
#    - 3 criterion grades (AO1, AO2, AO3 — each marks_awarded/max_marks)
#    - Total (out of 100 for Leaving Cert Maths)
#    - Strategy summary: "Total: 70/100. Per criterion: AO1 21/30, ..."
#    - Cited: SC-L1-L2-Programme-Statement.pdf
```

## What the verify gate checks (between Level 3 and Level 4)

```
$ ./journey/scripts/verify.sh
=== 6. MasteryLedger facade ===
  [OK]   MasteryLedger round-trip works
...
```

The MasteryLedger round-trip test (`journey/scripts/verify.sh` tick #6)
already exercises the same 4-backend fan-out Level 4 will use — so by
the time you get to Level 4, you know the substrate is sound.
