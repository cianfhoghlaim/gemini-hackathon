# Tasks

## Status: deferred (bookkeeping change)

This is a documentation-only change that records the deferred consolidation
of `gemini_hackathon/` back into `cianfhoghlaim/tuatha/` (the canonical
British Isles educational platform).

## Tasks

- [x] Audit `cianfhoghlaim/docs/sruth/tuath/` for features NOT in `gemini_hackathon/`
- [x] Audit `/dev/tuatha/` for features NOT in `gemini_hackathon/`
- [x] Record the dropped features (the "what's NOT in gemini_hackathon" tables)
- [x] Record the 5-step consolidation plan
- [x] Identify the affected specs (tuatha-british-isles-mmo, cianfhoghlaim-educational-mmo, gemini-hackathon-architecture, this spec)

## Acceptance

- The proposal.md documents every dropped feature explicitly (no silent loss).
- The 5-step consolidation plan names the canonical post-hackathon PR.
- The change is deferred (no code modification beyond this documentation).

## Post-hackathon follow-up

A single openspec change at the cianfhoghlaim monorepo level:
- `cianfhoghlaim/openspec/changes/<date>-refactor-tuatha-absorb-gemini-hackathon-v1/`
- Executes the 5 consolidation steps.
- Updates `subapp_manifest.yaml`.
- Closes this spec.
