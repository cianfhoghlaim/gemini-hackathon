# gemini_hackathon — Architecture (August 2026 refactor)

> The All Things Agentic 2026 hackathon submission. The British Isles
> Education Platform — Aistear → Bunscoil → MeanScoil → Scoil Sinsearach →
> Ollscoil — across 6 subnations (Ireland + England ship for the hackathon;
> NI / Wales / Scotland / IoM are Phase 2).

This ARCHITECTURE.md describes the current state after the August 2026
refactor (17 workstreams). The diagram is drawn from the running code
(per the `adk2-tutorial/L5_capstone` lesson: "the picture is read out of
`Workflow.graph.edges`").

## 1. High-level layout

```
gemini_hackathon/
├── pyproject.toml + requirements.txt + mise.toml
├── gemini_hackathon/                       ← the Python package
│   ├── agents/                             ← W7 — 5 stage coordinators + 5 pillars
│   ├── assets/                             ← the image-gen router
│   ├── call_llm.py + backend.py            ← the LLM gateway
│   ├── certificate/                        ← W14 — the LC/JC certificate pipeline
│   ├── cli.py + __main__.py + compare.py
│   ├── knowledge_graph/                    ← W8 — hybrid search (LanceDB + FalkorDB)
│   ├── ledger/                             ← W9 — skill-progression ledger
│   ├── memory/                             ← W8 — MarkdownMemoryService
│   ├── models/ + model_registry.py
│   ├── observability.py
│   ├── ocr.py
│   ├── progression/                       ← existing LC/JC certificate schema
│   ├── session/
│   ├── sources.py + theming.py
│   └── subnations.py                       ← W11 — 6 active + 2 deferred
├── gemini_hackathon_gradio/                ← W3 — the 5 editorial studios
│   ├── _common/                            ← shared library (theme, baml, pclm, hlml, ...)
│   ├── an_scrudu/                          ← LC past-paper heatmap studio
│   ├── anam_education/                     ← 7-feature integration studio
│   ├── oideachais_mission_control/          ← 5-stage control
│   ├── oideachais_pdf_review/              ← human review
│   └── editorial_studio/                   ← W12 — the big canvas (Cloud Run + gr.Workflow)
├── gemini_hackathon_assets_fibo/            ← W10 — the FIBO image-gen pipeline
│   ├── models.py, schemas.py, cache.py, assets.py
│   ├── processors/texture_processor.py      ← resize + format + watermark
│   └── education_prompts.py                 ← 14 subjects × 5 stages prompt bank
├── baml_extracts/                          ← existing (kept)
├── baml_extracts_education/                ← W4+W5 — lifted from cianfhoghlaim
│   ├── stages/{aistear,primary,junior_cycle,senior_cycle}.baml
│   ├── celtic_curriculum.baml, player_assessment.baml
│   └── certification_criteria.baml          ← W14 (referenced)
├── cocoindex_flows/                        ← W5 — Ireland education embeds
│   ├── _shared/                             ← shared_lifespan
│   └── ireland/                             ← per-stage embedding apps
├── dlt_pipelines/                           ← W5 — Ireland K-12 + LC DLT sources
│   ├── ireland/{_shared,primary,junior_cycle,leaving_cert,ncca_*}.py
│   ├── official_doc_fetcher.py + safeguarding_fetcher.py + pdf_page_metadata.py
│   └── _shared.py
├── data/
│   ├── ireland/ncca_policy/                ← W2 — 5 NCCA policy PDFs (source of truth)
│   ├── leabharlann/                         ← W6 — leabharlann corpus (manifests only)
│   ├── equivalencies/, jurisdictions/, marking_schemes/, policies/, sources/, syllabi/
├── themes/                                  ← awarding-body palettes (NCCA, AQA, OCR, ...)
├── web/                                    ← existing TanStack Start web app
├── hf_spaces/                               ← W13 — 5 headline demos
│   ├── _generate.py
│   ├── gemini_hackathon_{aistear,bunscoil,junior_cycle,leaving_certificate,editorial_studio}/
├── openspec/changes/                       ← W16 — 17 openspec changes
├── docs/                                   ← W15 — the docs (TUATHA_CONSOLIDATION_MAP, KNOWN_ISSUES, ...)
├── cloudbuild.yaml + mise.toml + README.md
└── hf_spaces/README.md
```

## 2. The 5-stage British Isles education palette

```
Aistear (0-6) → Bunscoil (4-12) → MeanScoil (12-15) → Scoil Sinsearach (15-19) → Ollscoil (Phase 2)
```

The Celtic 5-element palette (Talamh/Uisce/Tine/Aer/Anam) was REPLACED with
the 5-stage education palette in W3:

```
aistear          dawn-orange       #e8915c
bunscoil         sea-blue          #1e80c6
meanscoil        meadow-green      #28955e
scoil_sinsearach harvest-gold      #cc9966
ollscoil         scholarship-indigo #5a4fcf
```

Hades Shadow-First is preserved as the dark-mode foundation.

## 3. The 14-subject SUBJECT_WIRING_REGISTRY

W4 — the canonical routing table for the ADK 2 stage coordinators:

```
8 NCCA subjects + 6 NCCA-adjacent = 14 total

SUBJECT_WIRING_REGISTRY: dict[slug, SubjectAgentWiring]
  where SubjectAgentWiring has 8 fields:
    ncca_subject / module_slug / display_name / baml_prefix /
    langfuse_trace_name / cognee_dataset / letta_agent_id / litellm_routing_key

The routing keywords (`ROUTING_KEYWORDS`) classify learner messages to
the right subject bucket (10/10 typical questions route correctly in
the smoke test).
```

## 4. The 5 ADK 2 stage coordinators

W7 — `gemini_hackathon/agents/stages/<stage>/__init__.py` each builds
an ADK 2 `Workflow(name, description, edges=[...])`:

```
stages/
├── early_years/          Aistear 4-themes workflow
├── primary/              Bunscoil 12-area parallel-fetch + JoinNode (Pillar 1)
├── junior_cycle/         MeanScoil 10-subject dict-edge router (Pillar 1/2)
├── leaving_certificate/  Scoil Sinsearach 14-subject router + 14 specialists
└── cross_subject/        Pillar 3 dynamic fan-out for the 5 NCCA Key Competencies
```

The 5 reusable **ADK 2 pillars** in `gemini_hackathon/agents/workflows/`:

```
pillar1_grading.py          L2a parallel_join (parallel grading + JoinNode)
pillar2_collab_tutor.py     L3a collaborative (sub_agents + mode="single_turn")
pillar3_dynamic_research.py L4a flat_research (parallel_worker + synthesise)
pillar4_long_running.py      monstertix pattern (LongRunningFunctionTool + RequestInput)
pillar5_eval_flywheel.py     loop-lab-table pattern (adk eval + adk optimize GEPA)
```

## 5. The 5 NCCA policy PDFs as the source of truth

W2 — `data/ireland/ncca_policy/` contains 5 PDFs lifted verbatim from
`cianfhoghlaim/leaving_certificate/`:

```
SC-L1-L2-Programme-Statement.pdf
key-competencies-in-senior-cycle_en.pdf
the-potential-of-online-learning-environments_en.pdf
the-potential-of-technology-to-support-online-certification-and-reporting.pdf
scr-advisory-report_en.pdf
```

Every claim on every generated LC/JC certificate cites a page from one
of these PDFs (W14).

## 6. The LC/JC certificate pipeline (W14 — the showcase)

7 stages:

```
extract_criteria     → BAML extract from the 5 NCCA PDFs
decompose_outcomes    → split learner outcomes by mastery score
extract_paper+marking → DLT from data/ireland/lc_subject/
search_official       → RAG over the 5 NCCA policy corpus
generate_background   → Flux + W10 prompt bank (subject × stage)
compose_certificate   → PIL (1200×850): subject header + award pill +
                         learner name + top-5 outcomes + Key Competencies
                         strip + provenance footer + UNOFFICIAL banner
save_to_provenance     → W9 MasteryLedger (Convex + LanceDB + FalkorDB)
```

Output: `CertificateRecord` with PNG (~80 KB) + PDF (~700 B) + provenance
+ skill-progression summary. **Every claim cites a NCCA PDF page.** The
UNOFFICIAL banner is always present (per the user's spec).

## 7. The skill-progression ledger (W9, Google-native as of the GCP-first refactor)

4 backends unified by `MasteryLedger` facade — Convex was never deployed
(the original backend's own docstring called it a dev-only stub) and is
replaced outright, not migrated:

```
Firestore         UI-facing achievement rows (per-learner + per-outcome)
                   — replaces ConvexLedger
VectorTarget       320-dim -> 1536-d per-learner mastery vectors (5 Key
                   Competencies x 8 subjects x 4 levels x 2 languages),
                   dual-backed: Firestore FindNearest (default) or
                   Vertex AI Vector Search (VECTOR_BACKEND env var) —
                   replaces LanceDB
Firestore graph    skill-prerequisite graph (skill -> unlocks ->
                   assessed_by_artefact) as a `skillEdges` collection —
                   replaces FalkorDB
MarkdownMemory     per-user long-term memory (W8 — from monstertix),
                   persisted to Cloud Storage in production
```

`MasteryLedger.update_mastery(MasteryUpdate)` writes atomically to all 4.
`MasteryLedger.get_learner_state(learner_id)` reads all 4.

See `gemini_hackathon/ledger/backends/firestore_ledger.py` and
`gemini_hackathon/ledger/backends/firestore_graph.py`.

## 8. The 5 editorial studios (W3) + the 5 HF Spaces (W13)

```
gemini_hackathon_gradio/
├── _common/                                shared library
│   ├── theme.py (5-stage British Isles palette + Hades)
│   ├── baml_client.py (3-tier LiteLLM → Unsloth → HF)
│   ├── baml_pydantic_bridge.py
│   ├── pclm_emitter.py + hlml_emitter.py
│   ├── anam_bonneagar.py (Anam Faisnéise footer)
│   ├── hf_hub_push.py + demo_recorder.py
├── an_scrudu/             LC past-paper heatmap
├── anam_education/        7-feature integration
├── oideachais_mission_control/  5-stage control
├── oideachais_pdf_review/      human review
└── editorial_studio/     W12 — the big canvas (Cloud Run + gr.Workflow)

hf_spaces/                 ← published to cianfhoghlaim/gemini_hackathon_<stage>
```

Each Space has README.md (HF frontmatter) + app.py (lazy-imports the
studio) + requirements.txt. Generated by `hf_spaces/_generate.py`.

## 9. The 6 subnations (W11)

```
6 active subnations:
  1. Ireland (NCCA + SEC + DES)          — active (full implementation)
  2. England (DfE + AQA + OCR + Pearson)  — active (full implementation)
  3. Northern Ireland (CCEA)            — phase_2 (deferred)
  4. Wales (WJEC / CBAC)                 — phase_2 (deferred)
  5. Scotland (SQA)                      — phase_2 (deferred)
  6. Isle of Man (IoM Government Ed)     — phase_2 (default_meanscoil)

2 deferred (expansion pack):
  7. Jersey    — States of Jersey Education
  8. Guernsey  — States of Guernsey Education

All 6 active subnations have a corresponding awarding-body palette in
`themes/<key>_palette.json` (verified by smoke test).
```

## 10. The deferred-tuatha consolidation (W4 + W16)

```
W4 openspec change (already shipped):
  2026-08-27-defer-tuatha-consolidation-v1
  → documents the dropped features from sruth/tuath + /dev/tuatha
  → 5-step post-hackathon consolidation plan

Future openspec change at the cianfhoghlaim monorepo level:
  → absorbs gemini_hackathon/ back into cianfhoghlaim/tuatha/
  → closes the deferred-consolidation spec
```

See `docs/TUATHA_CONSOLIDATION_MAP.md` for the full details.

## 11. The 17 openspec changes

```
2026-08-27-minimal-unblock-v1                       (W0)
2026-08-27-dependency-pin-to-verified-versions-v1    (W1)
2026-08-27-ncca-policy-corpus-as-certificate-source-v1  (W2)
2026-08-27-gemini-hackathon-gradio-package-v1         (W3)
2026-08-27-lift-sruth-tuath-non-mythology-v1          (W4a)
2026-08-27-lift-dev-tuatha-subject-wiring-v1         (W4b)
2026-08-27-defer-tuatha-consolidation-v1             (W4c)
2026-08-27-lift-ireland-k12-baml-dlt-cocoindex-v1     (W5)
2026-08-27-lift-leabharlann-personal-archive-v1       (W6)
2026-08-27-adk-2-stage-coordinators-v1               (W7)
2026-08-27-memory-knowledge-graph-v1                 (W8)
2026-08-27-skill-progression-ledger-v1              (W9)
2026-08-27-fibo-image-generation-v1                  (W10)
2026-08-27-ireland-england-subnations-v1            (W11)
2026-08-27-gradio-editorial-studio-on-cloud-run-v1   (W12)
2026-08-27-hf-spaces-headline-demos-v1               (W13)
2026-08-27-official-lc-jc-certificate-pipeline-v1     (W14 — SHOWCASE)
+ 2026-08-27-deferred-ni-wales-scotland-iom-v1      (Phase 2 openspec)
+ 2026-08-27-deferred-jersey-guernsey-v1            (expansion pack)
```

## 12. Local dev topology

```
gemini-hackathon     (the app container; Dockerfile.cloudrun builds)
llama-swap          (OCR/VLM gateway; uses the canonical cianfhoghlaim config)
duckdb               (named-volume mount for the .duckdb file)

Unsloth Studio and the LLM backends run **outside Docker** on the host:
Unsloth Studio at 127.0.0.1:8888, Gemini via Vertex ADC, etc.
```

## 13. Observability

`gemini_hackathon.observability` ports the cianfhoghlaim/observability/*
modules. Emits:

- `llm.invocation` (canonical — `llm.tier` / `llm.model` / `llm.backend` /
  `llm.latency_ms` / `llm.tokens_in` / `llm.tokens_out` /
  `llm.fallback_reason`)
- `agent.trace_opened` + `agent.trace_closed` (per-agent spans)
- `asset.generated` (per-asset provenance)

Langfuse :3001 + MLflow :5050 are both live and wire in when the env
vars are set.

## 14. The 3-tier model policy

W1 update:

```
Tier 1 (production):  gemini-3.5-flash  via Vertex AI / AI Studio
Tier 2 (dev / local):  unsloth/gemma-4-26B-A4B-it-GGUF  via Unsloth Studio
Tier 3 (offline):     HuggingFace Inference Providers
                       (Qwen 7B → Llama 8B → Gemma 9b fallback chain)

Hard-rejected: `@cf/*` (Cloudflare Workers AI), `qwen3-coder-*`.
```

Every call routes through `gemini_hackathon.call_llm.call_llm(messages)`.
