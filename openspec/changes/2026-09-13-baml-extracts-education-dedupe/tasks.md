# Tasks: De-duplicate the baml_extracts_education schema into a single BAML source

## Phase 0 — Make the directory real

- [ ] 0.1. `rm baml_extracts/education` (the symlink)
- [ ] 0.2. `cp -R baml_extracts_education baml_extracts/education` (now a real dir)
- [ ] 0.3. Verify `ls -la baml_extracts/education` shows a real directory
- [ ] 0.4. Verify `find baml_extracts -name "*.baml" | wc -l` reports 35+ (was 8)

## Phase 1 — Fix the class extends issue

For each of the 8 subjects files in `baml_extracts/education/subjects/`:

- [ ] 1.1. `Maths` - flatten `class MathsLearningOutcome extends LCLearningOutcome` into 5 inline fields (lo_id, code, title, learning_outcomes, blooms_level). Same for `MathsSyllabus extends LCSyllabusDocument`.
- [ ] 1.2. `Biology` - same flattening
- [ ] 1.3. `Chemistry` - same flattening
- [ ] 1.4. `Physics` - same flattening
- [ ] 1.5. `English` - same flattening
- [ ] 1.6. `Gaeilge` - same flattening, ALSO fix `GaeilgeGenre` enum (Phase 2)
- [ ] 1.7. `Geography` - same flattening
- [ ] 1.8. `ComputerScience` - same flattening

## Phase 2 — Fix the ASCII-only enum rule

- [ ] 2.1. `gaeilge.baml` - rename enum values to ASCII-only (FILIOCHT, PROS, DRAMAIOCHT, SCEAL, FILIOCHT_BHEO, SCANNAN)

## Phase 3 — De-duplicate the strand enums

- [ ] 3.1. Keep ONE canonical `MathsStrand` declaration in `stages/leaving_cycle.baml`
- [ ] 3.2. Remove `MathsStrand` from `baml_extracts/learning_graph.baml` (and any other duplicate)
- [ ] 3.3. Repeat for `ChemistryStrand`, `BiologyStrand`, `PhysicsStrand`, `EnglishStrand`, `GaeilgeStrand`, `GeographyStrand`, `ComputerScienceStrand`
- [ ] 3.4. Repeat for the 8 corresponding `BloomLevel` enums

## Phase 4 — Validation

- [ ] 4.1. `uv run baml-cli generate` produces 17+ files (was 14)
- [ ] 4.2. Smoke test: `from baml_client.sync_client import b; b.ExtractMathsSyllabus` is callable
- [ ] 4.3. `bash scripts/verify.sh` is 8/8 green
- [ ] 4.4. `uv run mypy gemini_hackathon/` is 0 errors
- [ ] 4.5. `openspec validate 2026-09-13-baml-extracts-education-dedupe --strict` exits 0

## Phase 5 — Spec authoring

- [ ] 5.1. Create `openspec/specs/baml-extracts/spec.md` with the 5 Requirements

## Phase 6 — Commit + redeploy

- [ ] 6.1. git add the modified files
- [ ] 6.2. git commit with descriptive message
- [ ] 6.3. Trigger Cloud Build + deploy to Cloud Run
- [ ] 6.4. Verify `/api/health` still returns 38 models
