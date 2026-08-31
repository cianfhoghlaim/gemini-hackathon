# INDEX — the 28 openspec changes for the gemini_hackathon All Things Agentic 2026 hackathon

> **Note:** the original INDEX header reads "26 changes"; with the
> 3 NEW 2026-08-31 Learning Graph era changes (this one + Change B +
> Change C) **plus** the new `2026-08-31-replace-mise-with-make-v1` (Phase D — drops `mise.toml`, replaces with `Makefile` + `scripts/dev.sh` + `scripts/verify.sh` + `docs/LOCAL_DEV.md`), the working surface is **30 changes**. The header is
> preserved verbatim for canonical-row parity with the generator; the
> "Total" row below is the source of truth.

Per the implementation plan (W16): one openspec change per workstream,
plus the 2 deferred changes for the post-hackathon Phase 2 / expansion
pack, plus the 4 NEW 2026-08-30 GCP-first changes, plus the 4 NEW
2026-08-31 changes (3 Learning Graph era + 1 task-runner swap).

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
| `2026-08-27-skill-progression-ledger-v1` | W9 | closed | Skill-progression ledger (Firestore + Vertex AI Vector Search + Firestore graph) |
| `2026-08-27-fibo-image-generation-v1` | W10 | closed | FIBO image generation — 14 subjects × 5 stages prompt bank |
| `2026-08-27-ireland-england-subnations-v1` | W11 | closed | 9 subnations (Ireland + England + NCCE active; 6 Phase 2) |
| `2026-08-27-gradio-editorial-studio-on-cloud-run-v1` | W12 | closed | Editorial studio Cloud Run deploy scaffold |
| `2026-08-27-hf-spaces-headline-demos-v1` | W13 | closed | HF Spaces (5 headline demos at cianfhoghlaim/gemini_hackathon_*) |
| `2026-08-27-official-lc-jc-certificate-pipeline-v1` | W14 | closed | **Official-style LC/JC certificate pipeline (the SHOWCASE)** |
| `2026-08-27-defer-tuatha-consolidation-v1` | W4c | deferred | Records the absorbed + dropped features for the post-hackathon tuatha consolidation |

## The 2 deferred post-hackathon changes

| Change | Status | One-line |
|---|---|---|
| `2026-08-27-defer-ni-wales-scotland-iom-v1` | deferred | The 4 Phase 2 subnations (NI + Wales + Scotland + IoM) — live scraping + DLT + BAML deferred to post-hackathon |
| `2026-08-27-deferred-jersey-guernsey-v1` | deferred | The 2 expansion-pack subnations (Jersey + Guernsey) — awarding-body palettes + DLT deferred |

## The 5 NEW 2026-08-30 / 2026-08-31 changes (GCP-first era)

| Change | Phase | Status | One-line |
|---|---|---|---|
| `2026-08-30-retire-letta-wire-vertex-memory-bank-v1` | Phase 0 (memory) | **archived** (2026-08-31) | Replace Letta with `VertexAiMemoryBankService` + `MarkdownMemoryService` + `InMemoryMemoryService` |
| `2026-08-30-observability-otel-completeness-v1` | Phase 1 (OTLP) | **archived** (2026-08-31) | ADK OTel OTLP path + OpenInference Langfuse instrumentor + 6 Stackdriver env vars |
| `2026-08-30-cocoindex-pdf-pipeline-v1` | Phase 2 (PDF→Markdown) | **archived** (2026-08-31) | pdf_to_markdown App (Docling converter) + Dagster asset + MLflow benchmark |
| `2026-08-30-gcp-first-iac-refactor-v1` | Phase 0 IaC | closed | Drops Komodo/Pangolin/Locket/Infisical for Cloud Run + Secret Manager + WIF + 11 Terraform modules |
| `2026-08-31-gcp-infra-secrets-v1` | Phase 3 IaC | **archived** (2026-08-31) | GCP-first IaC completion — adds 8 module instantiations (`firestore`, `workflows`, `tasks`, `scheduler`, `kms`, `vpc`, `artifact-registry`, `cloud-build`) at `cloud/terraform/envs/dev/main.tf:168-260` + spec delta `gcp-infra` |

## The 4 NEW 2026-08-31 changes (Learning Graph era + task-runner swap)

| Change | Phase | Status | One-line |
|---|---|---|---|
| `2026-08-31-uk-ncce-learning-graph-showcase-v1` | Phase A | **active** | **The NCCE learning graph SHOWCASE** — lift 5 NCCE PDFs, build BAML `learning_graph.baml` (8 classes + 9 functions), 11 Dagster assets, 4-tab Gradio studio + HF Space |
| `2026-08-31-learning-graph-equivalency-graph-v1` | Phase B | **active** | Cell-level cross-jurisdiction equivalencies — `ExtractCellEquivalencies` + 42 Dagster assets (7 jurisdictions × 6 subjects) + FalkorDB `:CellEquivalentEdge` graph |
| `2026-08-31-pedagogy-overlay-renderer-v1` | Phase C | **active** | Dynamic extraction of 12 NCCE pedagogy principles + disk + Cognee cache + 6 Dagster assets + annotated SVG renderer |
| `2026-08-31-replace-mise-with-make-v1` | Phase D | **archived** (2026-08-31) | **Drops `mise.toml`** (357 LOC, 47 tasks). Replaces with `Makefile` (27 phony targets) + `scripts/dev.sh` + `scripts/verify.sh` (8-tick gate) + `docs/LOCAL_DEV.md` (5-step recipe). Aligns with `docs/cocoindex_examples/*` + `docs/adk-examples/*` shape. |

## Generation

`scripts/generate_openspec_changes.py` — the single source of truth for the 18
generated changes (16 W0-W14 + 2 deferred). Each change records:

  - Why the change exists (what surfaced in the workstream)
  - The scope (what's lifted / dropped / deferred)
  - The acceptance criteria (the smoke tests + visual checks)

Run `python scripts/generate_openspec_changes.py` to regenerate.

The 4 NEW 2026-08-30 changes and the 3 NEW 2026-08-31 changes are
authored by hand (not generated) — they are too cross-cutting for the
W16 generator pattern.

## File structure

Each change directory contains:
  - `proposal.md` — the formal openspec proposal (why + what + acceptance)
  - `tasks.md` — the task checklist (status + workstream + key bullets)
  - `specs/<capability>/spec.md` — the spec deltas (the formal requirements)

The W4 deferred-tuatha change additionally has `specs/deferred-consolidation/spec.md`
(the canonical "what's NOT in gemini_hackathon" record for the post-hackathon
consolidation).

## Summary

| Era | Changes | Status |
|---|---|---|
| Pre-refactor | 2 | closed |
| W0–W14 refactor | 16 + 1 deferred-tuatha | closed |
| Phase 2/expansion-pack deferred | 2 | deferred |
| 2026-08-30 GCP-first era | 4 | closed (4/4 archived) |
| 2026-08-31 Learning Graph era + task-runner swap | 4 | 3 active + 1 archived |
| **Total** | **30** | 27 completed + 3 active |
