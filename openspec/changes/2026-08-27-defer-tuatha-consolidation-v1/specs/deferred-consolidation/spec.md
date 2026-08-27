# Deferred tuatha consolidation spec

## Purpose

`deferred-tuatha-consolidation` is a bookkeeping spec that records:

1. What the `gemini_hackathon/` repo absorbed from both `sruth/tuath/`
   (in-tree) and `/dev/tuatha/` (standalone fork) during the
   2026-08-27 refactor.
2. What `gemini_hackathon/` did NOT absorb (the dropped features).
3. The post-hackathon consolidation plan that re-absorbs the dropped
   features back into a single canonical `tuatha/`.

The motivation is to prevent silent loss of features from the two
forks during the gemini_hackathon refactor.

## Background

`gemini_hackathon` is the All Things Agentic 2026 hackathon submission.
It is built around the British Isles education system (5 stages × 8
subnations × 14 NCCA LC subjects), not the Celtic mythology + MMO framing
that the canonical `tuatha/` sub-project embodies.

During W4 of the implementation plan (the refactor), useful parts of
both tuath forks were absorbed into `gemini_hackathon/`:

- From `sruth/tuath/`: BAML contracts, asset generation pipeline, knowledge_graph hybrid_search, the editorial canvas scaffolding, the 5-stage palette + i18n + trust-signal footer.
- From `/dev/tuatha/`: SUBJECT_WIRING_REGISTRY (14 LCs), per-subject ADK scaffolding, per-subject qpack BAMLs.

The refactor deliberately dropped the Celtic-mythology content (NPCs,
quests, mythology extraction, soulbound tokens, Babylon 3D scene,
Godot/Unity/Unreal exporters) because the user instruction was
"focus on the education system, not the MMO framing".

This spec records those drops + the future consolidation plan.

## Requirements

### Requirement: No silent loss

The refactor that absorbs useful parts of both tuath forks MUST NOT
silently lose features. Every dropped feature MUST be documented in
the proposal.md with:
  - The source path (sruth/tuath or /dev/tuatha)
  - The feature name
  - The reason for dropping it (out of scope for the education system)
  - The post-hackathon consolidation target (which file in tuatha/ will re-absorb it)

#### Scenario: Refactor drops a feature

- **GIVEN** the gemini_hackathon refactor is absorbing useful parts of
  sruth/tuath and /dev/tuatha
- **WHEN** a feature is dropped
- **THEN** the proposal.md MUST list the feature with the 4 attributes above
- **AND** the post-hackathon consolidation plan MUST identify where it lives next

### Requirement: Post-hackathon consolidation

The post-hackathon consolidation PR (to be opened in `cianfhoghlaim/tuatha/`)
MUST:

- Re-absorb the dropped features into their original locations (or
  their canonical successor locations).
- Update the canonical `tuatha-british-isles-mmo` spec to reflect the
  new merged shape.
- Drop the standalone `gemini_hackathon/` repo as a standalone (it
  becomes a sub-package of `tuatha/`).

#### Scenario: Post-hackathon PR opened

- **GIVEN** the All Things Agentic 2026 hackathon has been judged
- **AND** the user has reviewed the gemini_hackathon submission
- **WHEN** the consolidation PR is opened
- **THEN** the PR MUST close this openspec change
- **AND** the PR MUST pass the canonical BIEP v3 asset-check gates
- **AND** the PR MUST NOT regress any of the 250 test functions in
  the existing `tests/` directory

### Requirement: Affected specs

This spec affects:
- `tuatha-british-isles-mmo` (the canonical tuath spec — updated post-hackathon)
- `cianfhoghlaim-educational-mmo` (the canonical cianfhoghlaim education spec — updated post-hackathon)
- `gemini-hackathon-architecture` (NEW — the gemini_hackathon refactor's architecture spec, to be added to cianfhoghlaim/openspec/specs/ when the refactor ships)

#### Scenario: gemini-hackathon-architecture spec is added

- **GIVEN** the gemini_hackathon refactor W0-W16 has landed
- **WHEN** a new spec is added to cianfhoghlaim/openspec/specs/gemini-hackathon-architecture/
- **THEN** the spec MUST describe:
  - The new gemini_hackathon_gradio/ package (5 studios + shared _common)
  - The new baml_extracts_education/ BAML contracts
  - The new gemini_hackathon_assets_fibo/ FIBO pipeline
  - The 5 NCCA policy PDFs as the certificate source of truth
  - The 14-subject SUBJECT_WIRING_REGISTRY
- **AND** the spec MUST reference this deferred-consolidation spec

## Cross-references

- `openspec/changes/2026-08-27-defer-tuatha-consolidation-v1/proposal.md` — the change proposal
- `openspec/changes/2026-08-27-defer-tuatha-consolidation-v1/tasks.md` — the (deferred) task list
- `docs/TUATHA_CONSOLIDATION_MAP.md` (to be created in W15) — the canonical consolidation map

## See also

- `openspec/specs/tuatha-british-isles-mmo/spec.md` — the canonical tuath spec
- `openspec/specs/cianfhoghlaim-educational-mmo/spec.md` — the canonical cianfhoghlaim education spec
- `openspec/specs/british-isles-education-pipeline-v3/spec.md` — the BIEP v3 umbrella
