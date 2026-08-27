# TUATHA_CONSOLIDATION_MAP

The canonical map of what was absorbed from `sruth/tuath/` and
`/dev/tuatha/` into `gemini_hackathon/` during the August 2026 refactor,
plus the deferred consolidation plan.

See `openspec/changes/2026-08-27-defer-tuatha-consolidation-v1/` for
the formal openspec change + tasks + spec.

## What gemini_hackathon absorbed from sruth/tuath (in-tree copy)

### From `sruth/tuath/baml_src/`

| Source | New home |
|---|---|
| `celtic_curriculum.baml` (LearningOutcome / GrammarTopic / VocabularySet / Word / Example / CurriculumUnit) | `baml_extracts_education/celtic_curriculum.baml` (re-cast as British Isles education classes) |
| `player_assessment.baml` (ProficiencyLevel CEFR / AssessmentType / PExitCardSet / PPlayerResponseAnalysis + GenerateExitCardQuestions + AnalyzePlayerResponse + ScoreLearnerMastery + new PolicyCitation) | `baml_extracts_education/player_assessment.baml` (verbatim) |
| `clients.baml` (the 5 litellm clients: GPT4o + GPT4oMini + Claude + Qwen + OllamaIrish) | `baml_extracts/clients.baml` (extended in W1 with Tier 1 + Tier 2 + Tier 3 clients) |

### From `sruth/tuath/agents/adk/`

| Source | New home |
|---|---|
| `celtic_tutor.py` (the ADK 2 specialist scaffold) | `gemini_hackathon/agents/specialist_agent.py` (generic per-subject scaffold, dropped the Irish-language references) |
| `mythology_narrator.py` (Celtic mythology NPC agent) | **DROPPED** — out of scope for the education system |
| `quest_guide.py` (Celtic mythology quest agent) | **DROPPED** — out of scope |
| `research_assistant.py` (Celtic research agent) | **DROPPED** — out of scope |
| `root_agent.py` (the coordinator orchestrating the 4 specialists) | Replaced by the W7 stage coordinators + the SUBJECT_WIRING_REGISTRY |

### From `sruth/tuath/asset_generation/`

| Source | New home |
|---|---|
| `service.py:AssetCache` (LRU cache) | `gemini_hackathon_assets_fibo/cache.py` (verbatim, extended with sha256 cache key including subject + topic_code) |
| `models.py` (AssetType / CelticStyle / GenerationModel / LiteLLMConfig) | `gemini_hackathon_assets_fibo/models.py` (CelticStyle → SubjectStyle with 14 NCCA subjects + 5 stages; AssetType → EducationAssetType with 8 education assets; ClanId removed) |
| `prompts.py` (CelticPromptGenerator with 6 Celtic styles) | `gemini_hackathon_assets_fibo/education_prompts.py` (replaced with 14 NCCA subjects × 5 stages prompt bank) |
| `processors/texture_processor.py` (resize / format / watermark) | `gemini_hackathon_assets_fibo/processors/texture_processor.py` (kept essential ops; dropped mipmap / atlas / compression for the education system) |
| `exporters/{babylon,godot,unity,unreal}_exporter.py` | **DROPPED** — 3D game-engine exporters out of scope |

### From `sruth/tuath/fibo_generation/`

| Source | New home |
|---|---|
| `schemas.py` (SyllabusPage / CurriculumConcept / GeneratedAsset / FiboConfig) | `gemini_hackathon_assets_fibo/schemas.py` (verbatim + extended with `ncca_policy_citations`) |
| `assets.py` (Dagster assets: fibo_json_configs + generated_images + fibo_configs_from_syllabus_diagrams) | `gemini_hackathon_assets_fibo/assets.py` (Dagster templates — actual assets live in `orchestration/`) |
| `resources.py` (FiboResource + ValidationResource) | Stubbed in `assets.py` for W10 (real impl deferred) |

### From `sruth/tuath/dagster_assets/`

| Source | New home |
|---|---|
| `definitions.py`, `embedding_assets.py`, `curriculum_assets.py` | Templates in `gemini_hackathon_assets_fibo/` (W10); full implementation deferred |
| `mythology_assets.py` | **DROPPED** — out of scope |

### From `sruth/tuath/knowledge_graph/`

| Source | New home |
|---|---|
| `hybrid_search.py` (HybridSearchEngine with LanceDB + FalkorDB + RRF) | `gemini_hackathon/knowledge_graph/__init__.py` (rewritten with `ContentType` enum for 7 education surfaces) |
| `graphiti/` (the Graphiti temporal-episode streaming) | **DEFERRED** — out of W8 scope (FalkorDB + LanceDB hybrid covers the current use cases) |

### From `sruth/tuath/api/`

| Source | New home |
|---|---|
| `ag_ui_protocol.py` (the AG-UI SSE implementation) | Replaced by `gemini_hackathon/agents/fleet/fleet_agui.py` (existing canonical AG-UI bridge) |
| `routes/` (the FastAPI / Hono API endpoints) | **DROPPED** — Cloud Run studio uses `get_fast_api_app` (W12) |

### From `sruth/spaces/` (the HF Spaces library — IN-TREE)

| Source | New home |
|---|---|
| `_common/theme.py` (Celtic 5-element palette + Hades) | `gemini_hackathon_gradio/_common/theme.py` (5-stage British Isles education palette + Hades preserved) |
| `_common/baml_client.py` (3-tier HF Inference fallback) | `gemini_hackathon_gradio/_common/baml_client.py` (3-tier LiteLLM → Unsloth → HF, rewritten for gemini_hackathon) |
| `_common/i18n.py` (bilingual EN/GA + 5 Celtic TODO) | `gemini_hackathon_gradio/_common/i18n.py` (EN/GA + Welsh/Scottish/Manx as second-tier + 2 TODO) |
| `_common/baml_pydantic_bridge.py` (BAML → Pydantic mirror + regex fallback) | `gemini_hackathon_gradio/_common/baml_pydantic_bridge.py` (verbatim) |
| `_common/anam_bonneagar.py` (per-Space footer) | `gemini_hackathon_gradio/_common/anam_bonneagar.py` (renamed to "Anam Faisnéise", updated content) |
| `_common/hf_hub_push.py` (HF dataset pusher) | `gemini_hackathon_gradio/_common/hf_hub_push.py` (verbatim, user_id→repo_id builder) |
| `_common/demo_recorder.py` (programmatic demo recording) | `gemini_hackathon_gradio/_common/demo_recorder.py` (verbatim) |
| `an_scrudu/{app,extraction,heatmap}.py` (LC past-paper heatmap) | `gemini_hackathon_gradio/an_scrudu/{__init__,app,extraction,heatmap}.py` (rewritten with `MarkingSchemeExtraction` Pydantic model) |
| `anam_tuatha/{chemistry_visual,gaelscribhneoir,soulbound_local,mac_leinn,fiosraigh}.py` | `gemini_hackathon_gradio/anam_education/app.py` (skeleton + lazy-imports for the per-feature modules that land in W12) |
| `oideachais_mission_control/app.py` (5-tab Gradio) | `gemini_hackathon_gradio/oideachais_mission_control/app.py` (rewritten with 5-stage tabs) |
| `oideachais-pdf-review/app.py` (human review with Gemma 4 26B-A4B @spaces.GPU) | `gemini_hackathon_gradio/oideachais_pdf_review/app.py` (scaffold + `@spaces.GPU` pattern preserved) |

## What gemini_hackathon absorbed from /dev/tuatha (standalone fork)

| Source | New home |
|---|---|
| `routing.py:SUBJECT_WIRING_REGISTRY` (the 14-subject canonical wiring) | `gemini_hackathon/agents/registry.py` (rewritten for British Isles — NCCA + AQA/OCR/Pearson awarding-body palettes, Irish + English + Welsh + Scottish + Manx languages) |
| `agents/adk/{celtic_tutor,mythology_narrator,quest_guide,research_assistant,root_agent}.py` | `gemini_hackathon/agents/specialist_agent.py` (generic per-subject scaffold) + the W7 stage coordinators |
| `dlt/per_subject.py` (the per-subject DLT factory) | Templates in `gemini_hackathon/dlt_pipelines/ireland/` (W5) |
| `subjects/<subject>.py` (the 14 per-subject ADK agents) | W7 stage coordinator subjects (lazy-built via `build_subjects_registry()`) |
| `baml/qpack_<subject>.baml` (the 14 per-subject qpack BAMLs) | Templates referenced in W11 docs (deferred — lift only the LC subject BAMLs that W14 needs) |
| `web/` (the TanStack Start web surface) | **NOT LIFTED** — the existing `gemini_hackathon/web/` (TanStack Start) is kept as the consumer surface; the new editorial canvas lives in `gemini_hackathon_gradio/` |
| `ui/`, `game/`, `badges/`, `crates/`, `api-rs/` | **DROPPED** — Babylon 3D, PixiJS, Rust, x402 badges out of scope |
| `notebooks/` (marimo dashboards) | Partially lifted to `gemini_hackathon/notebooks/` (W5 — see the 8-tab pattern from the 3 UoG marimo notebooks) |
| `educational/` (the Tuatha education surface) | Deferred to Phase 2 (the tertiary pipeline is W14+ future work) |

## What lives in sruth/tuath that did NOT come across (and why)

For full transparency — these features were deliberately dropped:

- `tuath/baml_src/mythology_extraction.baml` — Celtic mythology extraction. Out of scope for the education system.
- `tuath/baml_src/game_content.baml` — quests / NPCs / game zones. Out of scope.
- `tuath/agents/adk/{mythology_narrator,quest_guide}.py` — the Celtic-mythology NPC agents. Out of scope.
- `tuath/asset_generation/exporters/{babylon,godot,unity,unreal}_exporter.py` — the 3D game-engine exporters. Out of scope (user explicitly excluded the MMO framing).
- `tuath/dlt_sources/{geospatial,mythology}/` — the Celtic-mythology DLT sources. Out of scope.
- `tuath/cocoindex_flows/mythology_embedding.py` — the mythology ColPali embed. Out of scope.
- `tuath/dagster_assets/mythology_assets.py` — the mythology Dagster assets. Out of scope.
- `tuath/knowledge_graph/graphiti/` — the deeper Graphiti temporal-episode streaming. Deferred (FalkorDB + LanceDB hybrid_search covers current use cases).
- `tuath/api/` — the FastAPI / Hono API endpoints. Replaced by `gemini_hackathon/agents/fleet/fleet_agui.py` (the canonical AG-UI bridge).
- `tuath/crates/` + `tuath/api-rs/` — the Rust rewrite. Out of scope.
- `tuath/ui/` + `tuath/game/` — the Babylon / PixiJS game client. Out of scope.
- `tuath/badges/` — the x402 hybrid educational credential. Out of scope (user explicitly excluded the blockchain / learn-to-earn framing).

## What's deferred to the post-hackathon tuatha consolidation

When the gemini_hackathon refactor is judged and shipped, the
post-hackathon consolidation refactor (in `cianfhoghlaim/tuatha/`)
will:

1. Promote `gemini_hackathon/` to be the canonical tuatha education surface.
   The `cianfhoghlaim/tuatha/` sub-project becomes the British Isles
   educational platform; `docs/sruth/tuath/` (the in-tree copy) is
   archived as `docs/sruth/_tuath_legacy_2026-08-27/`.

2. Re-absorb the dropped features. Re-lift the mythology + game +
   exporters modules into `tuatha/asset_generation/_legacy_mythology/`
   for historical reference; the production path stays on
   `gemini_hackathon_assets_fibo/` (the British Isles education FIBO).

3. Port the cross-cutting helpers back. The lifted modules
   (`_common/baml_client.py`, `_common/i18n.py`, `_common/theme.py`,
   `_common/anam_bonneagar.py`, `_common/hf_hub_push.py`,
   `_common/demo_recorder.py`, `_common/baml_pydantic_bridge.py`)
   become the canonical shared library at `tuatha/_shared/`.

4. Drop `gemini_hackathon_gradio/`. Its studios (an_scrudu,
   anam_education, oideachais_mission_control, oideachais_pdf_review,
   editorial_studio) become the 5 HF Spaces under the canonical
   `tuatha/spaces/` directory; the Cloud Run editorial studio becomes
   `tuatha/spaces/editorial_studio/`.

5. Update `subapp_manifest.yaml`. Add the gemini_hackathon editorial
   studio + the 5 HF Spaces as the TIER 3 sub-app entry that the
   cianfhoghlaim monorepo's `sync_subapps.py` reads.

A single openspec change at the cianfhoghlaim monorepo level will
execute these 5 steps.

## Verification

This map is consistent with the lifted-files audit + the dropped-features
list in `openspec/changes/2026-08-27-defer-tuatha-consolidation-v1/proposal.md`.
A future `git log --stat` against the cianfhoghlaim/tuatha/ repo will
show exactly which files were re-absorbed.
