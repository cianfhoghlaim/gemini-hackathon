# INDEX — the 20 openspec changes for the gemini_hackathon All Things Agentic 2026 hackathon

Per the implementation plan (W16): one openspec change per workstream,
plus the 2 deferred changes for the post-hackathon Phase 2 / expansion pack.

Run `python scripts/generate_openspec_changes.py` to regenerate any
of these (idempotent — preserves the W4 deferred-tuatha change + skips
changes whose files already exist).

## Original (pre-refactor)

| Change | Description |
|---|---|
| `2026-08-24-gemini-hackathon-public-v1` | The original gemini-hackathon-public openspec change (pre-refactor) |
| `2026-08-25-per-subnation-user-context` | The original per-subnation user-context openspec change |

## The 16 W0-W14 refactor changes + the W4 deferred-tuatha

| Change | W | Status | One-line |
|---|---|---|---|
| `2026-08-27-minimal-unblock-v1` | W0 | closed | Re-pin mise, ignore .agents/, document dupe web/components |
| `2026-08-27-dependency-pin-to-verified-versions-v1` | W1 | closed | google-adk 2.7.1+, gradio 5.28+, huggingface_hub 0.30+ |
| `2026-08-27-ncca-policy-corpus-as-certificate-source-v1` | W2 | closed | 5 NCCA policy PDFs as committed data — certificate source of truth |
| `2026-08-27-gemini-hackathon-gradio-package-v1` | W3 | closed | gemini_hackathon_gradio/ package — 5 editorial studios + shared library |
| `2026-08-27-lift-sruth-tuath-non-mythology-v1` | W4a | closed | Lift sruth/tuath BAML contracts + agents + asset_generation (non-mythology) |
| `2026-08-27-lift-dev-tuatha-subject-wiring-v1` | W4b | closed | Lift /dev/tuatha SUBJECT_WIRING_REGISTRY + per-subject scaffolds |
| `2026-08-27-lift-ireland-k12-baml-dlt-cocoindex-v1` | W5 | closed | Lift cianfhoghlaim Ireland K-12 + LC BAML + DLT + CocoIndex (Primary + Secondary) |
| `2026-08-27-lift-leabharlann-personal-archive-v1` | W6 | closed | Lift leabharlann corpus + UoG archive manifests (verbatim) |
| `2026-08-27-adk-2-stage-coordinators-v1` | W7 | closed | ADK 2 stage coordinators + 5 reusable workflow pillars |
| `2026-08-27-memory-knowledge-graph-v1` | W8 | closed | Memory layer + knowledge_graph hybrid_search (FalkorDB + LanceDB) |
| `2026-08-27-skill-progression-ledger-v1` | W9 | closed | Skill-progression ledger (Convex + LanceDB + FalkorDB) |
| `2026-08-27-fibo-image-generation-v1` | W10 | closed | FIBO image generation — 14 subjects × 5 stages prompt bank |
| `2026-08-27-ireland-england-subnations-v1` | W11 | closed | 6 subnations (Ireland + England for hackathon; 4 Phase 2) |
| `2026-08-27-gradio-editorial-studio-on-cloud-run-v1` | W12 | closed | Editorial studio Cloud Run deploy scaffold |
| `2026-08-27-hf-spaces-headline-demos-v1` | W13 | closed | HF Spaces (5 headline demos at cianfhoghlaim/gemini_hackathon_*) |
| `2026-08-27-official-lc-jc-certificate-pipeline-v1` | W14 | closed | **Official-style LC/JC certificate pipeline (the SHOWCASE)** |
| `2026-08-27-defer-tuatha-consolidation-v1` | W4c | deferred | Records the absorbed + dropped features for the post-hackathon tuatha consolidation |

## The 2 deferred post-hackathon changes

| Change | Status | One-line |
|---|---|---|
| `2026-08-27-defer-ni-wales-scotland-iom-v1` | deferred | The 4 Phase 2 subnations (NI + Wales + Scotland + IoM) — live scraping + DLT + BAML deferred to post-hackathon |
| `2026-08-27-deferred-jersey-guernsey-v1` | deferred | The 2 expansion-pack subnations (Jersey + Guernsey) — awarding-body palettes + DLT deferred |

## Generation

`scripts/generate_openspec_changes.py` — the single source of truth for the 18
generated changes (16 W0-W14 + 2 deferred). Each change records:

  - Why the change exists (what surfaced in the workstream)
  - The scope (what's lifted / dropped / deferred)
  - The acceptance criteria (the smoke tests + visual checks)

Run `python scripts/generate_openspec_changes.py` to regenerate.

## File structure

Each change directory contains:
  - `proposal.md` — the formal openspec proposal (why + what + acceptance)
  - `tasks.md` — the task checklist (status + workstream + key bullets)

The W4 deferred-tuatha change additionally has `specs/deferred-consolidation/spec.md`
(the canonical "what's NOT in gemini_hackathon" record for the post-hackathon
consolidation).
