# Spec Delta: orchestration-equivalency-graph (Phase 2 — Dagster cross-walk assets)

This delta is applied by the OpenSpec change
[`2026-08-31-learning-graph-equivalency-graph-v1`](../proposal.md). It describes the
**ADDED** Requirements to the canonical `orchestration-equivalency-graph` capability
that this change introduces.

## ADDED Requirements

### Requirement: `orchestration/defs/3_model_lifecycle/uk_ncce_learning_graph_equivalencies.py` SHALL define 48 cross-walk assets
The system SHALL meet the requirement: `orchestration/defs/3_model_lifecycle/uk_ncce_learning_graph_equivalencies.py` SHALL define 48 cross-walk assets.
The module SHALL expose 48 Dagster assets, one per
`(jurisdiction × subject)` pair where:

- `jurisdiction ∈ {ENGLAND, WALES, NORTHERN_IRELAND, SCOTLAND, ISLE_OF_MAN, JERSEY, GUERNSEY}` (7 jurisdictions — UK_NCCE is the source, never a target)
- `subject ∈ {computer_science, mathematics, english, gaeilge, chemistry, geography}` (6 priority subjects)

Total: `7 × 6 = 42` jurisdiction pairs (the source jurisdiction is UK_NCCE in every pair).

Each asset SHALL depend on the corresponding `uk_ncce_learning_graphs` asset (from Change A) and on the corresponding per-jurisdiction `dlt` resource.

Each asset SHALL materialise a `LearningGraphCrossReference` to:

- Firestore `prerequisiteEdges/{edge_id}` collection
- FalkorDB `:CellEquivalentEdge` graph (when FalkorDB is available)

#### Scenario: All 48 assets materialize successfully

- **WHEN** `dg launch --assets uk_ncce_cs_england_equivalencies` is run
- **THEN** the asset SHALL emit a non-empty `LearningGraphCrossReference` JSON
- **AND** the corresponding Firestore document SHALL be created
- **AND** the SQLite row SHALL be inserted

#### Scenario: Cross-walk graph asset aggregates all 48 edges

- **WHEN** the `learning_graph_equivalency_graph` asset runs
- **THEN** it SHALL read all 48 `LearningGraphCrossReference` documents from Firestore
- **AND** write the unified graph to FalkorDB `:CellEquivalentEdge`
- **AND** return the total edge count

### Requirement: The Equivalencies tab in the Gradio studio SHALL render the cross-walk
The system SHALL meet the requirement: The Equivalencies tab in the Gradio studio SHALL render the cross-walk.
The `gemini_hackathon_gradio/an_learning_graph/equivalencies_tab.py`
SHALL render a Sankey-style diagram (Plotly) showing the flow from the
source cell to its 7 equivalents in the other jurisdictions. The tab
SHALL be reachable from the studio's tab bar at runtime.

#### Scenario: Picking a cell shows the cross-walk

- **WHEN** a user picks a cell in the NCCE Y8 Python learning graph
- **THEN** the tab SHALL display the 7 equivalent cells in the other jurisdictions
- **AND** the Sankey diagram SHALL show the flow with confidence scores as link widths