# Spec Delta: learning-graph-equivalency (Phase 1 — BAML cell-level equivalencies)

This delta is applied by the OpenSpec change
[`2026-08-31-learning-graph-equivalency-graph-v1`](../proposal.md). It describes the
**ADDED** Requirements to the canonical `learning-graph-equivalency` capability
that this change introduces.

## ADDED Requirements

### Requirement: `baml_extracts/extract_equivalency.baml` SHALL expose a `CellEquivalent` class + `ExtractCellEquivalencies` function
The system SHALL meet the requirement: `baml_extracts/extract_equivalency.baml` SHALL expose a `CellEquivalent` class + `ExtractCellEquivalencies` function.
The module SHALL add:

- `CellEquivalent` class — `(cell_id, jurisdiction, subject, year_level, confidence, notes)` where `cell_id` matches the `LearningGraphCell.id` schema from `baml_extracts/learning_graph.baml`
- `ExtractCellEquivalencies(source_cell, source_jurisdiction, target_jurisdictions)` function returning `map<Jurisdiction, CellEquivalent>`

The function SHALL follow the same confidence rules as the existing `ExtractEquivalencies`:

- `1.00` — exact 1:1 cell equivalence
- `0.85` — strong overlap (80-95% of syllabus content shared)
- `0.70` — partial overlap (50-80%)
- `< 0.50` — should not be persisted

#### Scenario: All 8 jurisdictions are covered

- **WHEN** `ExtractCellEquivalencies` is called with `target_jurisdictions = [ENGLAND, WALES, NORTHERN_IRELAND, SCOTLAND, ISLE_OF_MAN, JERSEY, GUERNSEY]`
- **THEN** the result SHALL contain 7 entries (one per target jurisdiction)
- **AND** every entry SHALL have a confidence ≥ 0.0

### Requirement: `baml_extracts/learning_graph_crossref.baml` SHALL expose a `LearningGraphCrossReference` class
The system SHALL meet the requirement: `baml_extracts/learning_graph_crossref.baml` SHALL expose a `LearningGraphCrossReference` class.
The module SHALL define `LearningGraphCrossReference`:

- `source_graph_id` — the source `LearningGraph.id`
- `target_graph_id` — the target `LearningGraph.id`
- `jurisdiction_pair` — tuple `(source_jurisdiction, target_jurisdiction)`
- `cell_edges` — `CellEquivalent[]` linking cells across the two graphs
- `overall_confidence` — the mean confidence of the cell edges
- `generated_at` — UTC ISO-8601 timestamp

#### Scenario: Cross-reference compiles

- **WHEN** `uv run baml-cli generate` is run
- **THEN** the generated Python client SHALL expose `LearningGraphCrossReference`
- **AND** the command SHALL exit 0