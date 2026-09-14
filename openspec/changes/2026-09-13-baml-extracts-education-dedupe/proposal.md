# Change: De-duplicate the `baml_extracts_education` schema into a single BAML source

## Why

Subagent B (2026-09-13 mega-3a sweep) added `catch_all` blocks +
`render_null_as="-1"` annotations to the 6 LC subject extractor files
at `baml_extracts_education/subjects/*.baml`. Investigation
(`task_result` from that subagent) flagged a critical pre-existing
issue: **`baml-cli generate` silently excludes the entire
`baml_extracts_education/` directory from the generated Python
client**, so the new catch_all fallbacks never reach runtime.

### Root causes (in 2026-09-13 audit)

1. **Symlink skip**: `baml_extracts/education -> ../baml_extracts_education`
   is a symlink that `baml-cli`'s default `find` walk does not follow.
   `find -L baml_extracts` shows the 35 .baml files under
   `baml_extracts_education/`, but `find baml_extracts` (which is what
   `baml-cli generate` does internally) shows only the 8 top-level files.
2. **Class `extends` is invalid BAML**: even after making the dir real
   (verified by removing the symlink + copying the files), `baml-cli`
   errors out with `error: This line is invalid. It does not start with any
   known Baml schema keyword` at every `class XLearningOutcome extends LCLearningOutcome` line. **BAML 0.223.0+ does NOT support class inheritance** — the lift from
   `cianfhoghlaim/baml_src/british_isles/_shared/lc_extraction_template.baml`
   pre-dates this constraint.
3. **Gaeilge enum non-ASCII**: `enum GaeilgeGenre { FILÍOCHT PRÓS DRÁMAÍOCHT
   ... }` uses accented characters that violate BAML's
   "all caps, no accents" enum rule.
4. **Duplicate strand enums**: `MathsStrand` is declared in BOTH
   `baml_extracts/learning_graph.baml` (line 70) AND
   `baml_extracts_education/stages/leaving_cycle.baml` (line 73) AND
   `baml_extracts_education/subjects/mathematics.baml` (line 9). Once the
   dir is visible to baml-cli, the duplicate name causes
   "duplicate type" errors.

### Impact

The 6 `Extract*` functions in `baml_extracts_education/subjects/*.baml`
are unreachable at runtime:
- `ExtractMathsSyllabus`, `ExtractChemistrySyllabus`, `ExtractBiologySyllabus`,
  `ExtractPhysicsSyllabus`, `ExtractEnglishSyllabus`, `ExtractGaeilgeSyllabus`,
  `ExtractGeographySyllabus`, `ExtractComputerScienceSyllabus`

The 16 canonical LC6 extraction functions in
`baml_extracts_education/stages/leaving_cycle.baml` (per the comment
in that file) are also unreachable, replaced by the 8-stub fallback in
`gemini_hackathon_backend/main.py:build_app()`.

This means the gemini_hackathon LC extraction is currently stub-fallback
only — the BAML lift from cianfhoghlaim (W14 of the 2026-08-27 hackathon
refactor) is NOT in effect.

## What changes

This is a multi-PR refactor. The minimum viable scope:

### PR 1 (this change): De-duplicate + compose

1. **Replace inheritance with composition** in all 8 subjects files:
   - Remove `extends LCLearningOutcome` from `MathsLearningOutcome`,
     `BiologyLearningOutcome`, etc.
   - Add the parent fields (`lo_id`, `code`, `title`,
     `learning_outcomes`, `blooms_level`) inline as duplicated field
     definitions.
2. **Replace inheritance with composition** for `XLearningSyllabus extends LCSyllabusDocument`:
   - Remove `extends LCSyllabusDocument`
   - Duplicate the parent fields (`subject`, `language`, `stage`,
     `source_pdf`, `source_pages`, `module_topics`,
     `total_learning_outcomes`) inline.
3. **Fix `GaeilgeGenre` enum** to use ASCII-only values:
   `FILIOCHT`, `PROS`, `DRAMAIOCHT`, `SCEAL`, `FILIOCHT_BHEO`,
   `SCANNAN` (or transliterate)
4. **De-duplicate strand enums** between `baml_extracts/learning_graph.baml`,
   `baml_extracts_education/stages/leaving_cycle.baml`, and the 8
   subjects files — keep ONE copy in `stages/leaving_cycle.baml`,
   re-export from `learning_graph.baml`.
5. **Make `baml_extracts/education/` a real directory** (copy content
   from the symlink). Add `.gitignore` entry for the duplicate until
   the de-dup PR lands.
6. **Verify**: `uv run baml-cli generate` produces 17+ files (was
   14) and `from baml_client.sync_client import b; b.ExtractMathsSyllabus(...)` is callable.
7. **`8/8 verify ticks green` + Cloud Run redeployed.**

### Out of scope (deferred)

- Renaming the BAML package (from `baml_extracts_education` to
  something flatter like `lc_extraction/`).
- Migrating the 16 canonical LC6 functions to the new flatter
  structure (they're in `stages/leaving_cycle.baml`, which has the
  same inheritance-incompatible structure).
- The GaeilgeComposer migration from cianfhoghlaim (separate
  concern).

## Impact

- **Affected code**:
  - `baml_extracts_education/stages/leaving_cycle.baml`
  - `baml_extracts_education/subjects/{mathematics,biology,chemistry,
    physics,english,gaeilge,geography,computer_science}.baml` (8 files)
  - `baml_extracts/learning_graph.baml` (de-dup)
  - `baml_extracts/education` symlink → real directory
- **Affected specs**: `baml-extracts` (new spec for the LC6
  extraction contract)
