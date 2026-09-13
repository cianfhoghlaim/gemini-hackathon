# Change: Codify the gemini_hackathon sister-umbrella contract

## Why

Per `cianfhoghlaim/openspec/changes/cianchosaint-handoff-v1/proposal.md`
§4 (drift #5), `gemini_hackathon` uses a deliberately **divergent
layout** from cianfhoghlaim:

1. `baml_src -> baml_extracts` (symlink, NOT the canonical
   cianfhoghlaim directory)
2. `dlt_pipelines/` (NOT `dlt_sources/`)
3. 6 sister-owned HF Spaces at `hf_spaces/gemini_hackathon_<stage>/`
4. GCP-first IaC surface (`cloud/terraform/modules/`) replacing
   the cianfhoghlaim bonneagar/stacks/ pattern
5. Standalone `gemini_hackathon/model_registry.py` (a trimmed
   port of `meaisinfhoghlaim/models/model_registry.py`,
   promoted on 2026-09-13 to include the 9 M3 chokepoint aliases)

This change codifies these differences as an explicit sister-umbrella
contract so future sister-repo audits don't mistake the divergence
for drift, and so the wholesale-copy invariants from
`cianchosaint-handoff-v1/Shared-1..5` are satisfied by gemini_hackathon's
**equivalent** (not identical) surface.

## What changes

- New spec: `openspec/specs/sister-shared/gemini-hackathon-divergence.md`
  (5 Requirements, one per divergence point above)
- New entry in `openspec/AGENTS.md`: "gemini_hackathon is a
  deploy-target sister (Cloud Run) — not a platform sister"

## Impact

- **Affected code**: doc + spec only — no code changes
- **Affected specs**: `sister-shared` (add the gemini_hackathon-specific
  divergence clause)
