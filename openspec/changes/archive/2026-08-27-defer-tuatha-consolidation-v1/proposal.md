# 2026-08-27-defer-tuatha-consolidation-v1

> Defer the consolidation of `gemini_hackathon/` back into the canonical
> `cianfhoghlaim/tuatha/` (or the standalone `github.com/cianfhoghlaim/tuatha`)
> sub-project to a post-hackathon pass.

## Why

The `gemini_hackathon` repo (the All Things Agentic 2026 hackathon submission)
absorbed useful parts of both `cianfhoghlaim/docs/sruth/tuath/` and the
standalone `/dev/tuatha/` (a sibling fork) during the
2026-08-27 refactor (W4 of the implementation plan).

The two tuath forks each have features that gemini_hackathon does NOT have:
the deferred-consolidation is therefore NOT a silent loss — it must be
recorded + scheduled for a post-hackathon refactor that re-absorbs them
into a single canonical tuatha.

## What's NOT in gemini_hackathon that lives in the two tuath forks

### From `cianfhoghlaim/docs/sruth/tuath/` (the canonical in-tree copy)

- `baml_src/mythology_extraction.baml` (Celtic mythology extraction) — out of scope for the education system.
- `baml_src/game_content.baml` (quests / NPCs / game zones) — out of scope.
- `agents/adk/mythology_narrator.py` and `agents/adk/quest_guide.py` (the Celtic-mythology NPC agents) — out of scope.
- `asset_generation/exporters/{babylon,godot,unity,unreal}_exporter.py` (the 3D game-engine exporters) — out of scope (the user explicitly excluded the MMO framing).
- `dlt_sources/{geospatial,mythology}/` (the Celtic-mythology DLT sources) — out of scope.
- `cocoindex_flows/mythology_embedding.py` (the mythology ColPali embed) — out of scope.
- `dagster_assets/mythology_assets.py` (the mythology Dagster assets) — out of scope.
- `knowledge_graph/graphiti/` (the deeper Graphiti temporal-episode streaming) — deferred (FalkorDB + LanceDB hybrid_search is the current implementation).
- `api/` (the FastAPI / Hono API endpoints) — replaced by `gemini_hackathon/agents/fleet/fleet_agui.py` (the canonical AG-UI bridge).
- `crates/` + `api-rs/` (the Rust rewrite) — out of scope.
- `ui/` + `game/` (the Babylon / PixiJS game client) — out of scope.

### From `/dev/tuatha/` (the standalone fork)

- `web/` (the TanStack Start web surface) — the gemini_hackathon
  `web/` is a sibling TanStack Start app; the consolidation will pick
  the better of the two + cross-port the other.
- `educational/` (the Tuatha education surface) — deferred (Phase 2 of
  the gemini_hackathon refactor; only Aistear / Bunscoil / MeanScoil /
  Scoil Sinsearach are in scope per the user instruction; Ollscoil is
  deferred to the post-hackathon tertiary pipeline).
- `notebooks/` (the marimo dashboards) — partially lifted to
  `gemini_hackathon/notebooks/` (W5).
- `dagster_assets/` + `dlt/per_subject.py` — templates lifted to
  `gemini_hackathon/dlt_pipelines/ireland/{stage}.py` (W5).
- `badges/` (the x402 hybrid educational credential) — out of scope
  per the user's explicit exclusion of the blockchain / learn-to-earn.
- `orchestrator.py` (the multi-agent orchestrator) — the
  ADK 2 stage coordinators (W7) supersede this.

## Consolidation plan (post-hackathon)

When the hackathon is over, the consolidation steps are:

1. **Promote `gemini_hackathon/` to be the canonical tuatha education surface.**
   The `cianfhoghlaim/tuatha/` sub-project becomes the British Isles
   educational platform; `docs/sruth/tuath/` (the in-tree copy) is
   archived as `docs/sruth/_tuath_legacy_2026-08-27/`.

2. **Re-absorb the dropped features.** Re-lift the mythology + game +
   exporters modules into `tuatha/asset_generation/_legacy_mythology/`
   for historical reference; the production path stays on
   `gemini_hackathon_assets_fibo/` (the British Isles education FIBO).

3. **Port the cross-cutting helpers back.** The lifted modules
   (`_common/baml_client.py`, `_common/i18n.py`, `_common/theme.py`,
   `_common/anam_bonneagar.py`, `_common/hf_hub_push.py`,
   `_common/demo_recorder.py`, `_common/baml_pydantic_bridge.py`)
   become the canonical shared library at `tuatha/_shared/` (the
   tuath shared library).

4. **Drop `gemini_hackathon_gradio/`.** Its studios (an_scrudu,
   anam_education, oideachais_mission_control, oideachais_pdf_review,
   editorial_studio) become the 5 HF Spaces under the canonical
   `tuatha/spaces/` directory; the Cloud Run editorial studio becomes
   `tuatha/spaces/editorial_studio/`.

5. **Update `subapp_manifest.yaml`.** Add the gemini_hackathon
   editorial studio + the 5 HF Spaces as the TIER 3 sub-app entry
   that the cianfhoghlaim monorepo's `sync_subapps.py` reads.

## What this change does

- Records the dropped features in the consolidation map above.
- Records the consolidation plan.
- Marks the implementation as deferred (no code change beyond the
  documentation).
- Lays the groundwork for the post-hackathon refactor PR (to be opened
  in `cianfhoghlaim/tuatha/` once the hackathon is judged).

## What this change does NOT do

- Does NOT remove any code from `gemini_hackathon/`.
- Does NOT modify `docs/sruth/tuath/` or `/dev/tuatha/`.
- Does NOT touch any of the 17 openspec changes in the
  gemini_hackathon refactor (W0-W16 of the implementation plan).

## Affected specs

- `tuatha-british-isles-mmo` — the canonical tuath spec. Will be
  updated post-hackathon to reflect the gemini_hackathon merger.
- `cianfhoghlaim-educational-mmo` — the canonical cianfhoghlaim
  education spec. Will be updated post-hackathon.
- `gemini-hackathon-architecture` (new) — the gemini_hackathon
  refactor's architecture spec. Records the new package layout
  (`gemini_hackathon_gradio/`, `gemini_hackathon_assets_fibo/`,
  `baml_extracts_education/`).
- `deferred-consolidation` (this spec).

## Future work

A single follow-up openspec change at the cianfhoghlaim monorepo
level will execute the 5 consolidation steps above. Anticipated PR title:
`refactor(tuatha): absorb gemini_hackathon/ post-hackathon consolidation`.
