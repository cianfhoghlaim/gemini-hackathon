# Journey integration — which `docs/ideas/` doc informed which level?

> **Audit trail.** The Journey is anchored on the official syllabus
> processing pipeline + all 8 British Isles subnations. Some of the 15
> deep-research docs in `docs/ideas/` directly informed a level; others
> are explicitly out of scope. This doc records the boundaries so a
> future workshop host knows what was absorbed, what was deferred, and
> why.

## In scope — absorbed into a level

| Idea doc | Level it informed | How it was absorbed |
|---|---|---|
| [AI Syllabus to JSON Schema.md](../ideas/AI Syllabus to JSON Schema.md) | L1 + L5 | The BAML `ExtractCurriculumSyllabus` Python caller (Level 1) + the `EducationAssetRequest` BAML re-call (Level 5) — both follow the "schema-first" discipline this doc argues for |
| [BAML Schemas for Irish Education.md](../ideas/BAML%20Schemas%20for%20Irish%20Education.md) | L1 + L3 | The per-subject extraction enum discipline + the marking-scheme BAML `ExtractMarkingSchemeGuideline` (Level 3) |
| [BAML for Syllabus-Driven Data Extraction.md](../ideas/BAML%20for%20Syllabus-Driven%20Data%20Extraction.md) | L1 + L3 | The "BAML as the deterministic semantic bridge" pattern that both levels' agent nodes use |
| [British Isles Education Map.md](../ideas/British%20Isles%20Education%20Map.md) | L0 | The 8-subnation table (Ireland + England x3 boards + Scotland + Wales + NI + IoM + Jersey + Guernsey) drives Level 0's `SUBNATIONS` dropdown + every downstream level's per-jurisdiction BAML extraction |
| [Agent Development Kit (ADK).md](../ideas/Agent%20Development%20Kit%20(ADK).md) | All | The Spanner-backed ADK agent pattern — adapted to use our Firestore substrate (Phase 6) instead of Spanner. The "Agent + tools + Runner" architecture is identical |
| [Google ADK with LiteLLM _ liteLLM.md](../ideas/Google%20ADK%20with%20LiteLLM%20_liteLLM.md) | All | Multi-provider model config (Gemini 2.5 Flash default, Gemma on Vertex, Unsloth fallback). The Voyage code's `Agent(model=LiteLlm(model=MODEL))` pattern is what `gemini_hackathon.call_llm` does |
| [useAgent Hook.md](../ideas/useAgent%20Hook.md) | All | The conceptual basis for the studio's Gradio client-side wiring. Voyage's `useAgent()` from React → our Gradio `.change` + `.click` events (no React/Next.js in this repo, same idea) |
| [Ontology and Temporal Graphs Research.md](../ideas/Ontology%20and%20Temporal%20Graph%20Research.md) | L4 | The temporal-graph idea behind `MasteryLedger` — already implemented as Firestore `skillEdges` (Phase 6) |
| [AI Chemistry Education Image Generation.md](../ideas/AI%20Chemistry%20Education%20Image%20Generation.md) | L5 | The FIBO JSON-native image generation pattern — Level 5's `fibo_generate_node` calls into `gemini_hackathon_assets_fibo` exactly as this doc prescribes |
| [knowledge-graph-infrastructure.md](../ideas/knowledge-graph-infrastructure.md) | L1 + L4 | The dual-engine (graph + vector) pattern that Level 1 (Firestore `FindNearest`) + Level 4 (Firestore skill graph) already implement |
| [Visualizing Cognee and Graphiti Graphs.md](../ideas/Visualizing%20Cognee%20and%20Graphiti%20Graphs.md) | L4 (deferred bonus) | The conceptual basis for an optional skill-graph visualisation (`render_skill_graph_html()`) — NOT built into the journey yet but the path is documented for a future workshop |
| [Agentic Education Platform Development.md](../ideas/Agentic%20Education%20Platform%20Development.md) | L4 + L5 | The ADK 2 architecture sections (Pillar 1/2/3, Memory Bank, hybrid search) — already absorbed by Phase 4 + Phase 6 |
| [Leaving Certificate Subject Analysis Plan.md](../ideas/Leaving%20Certificate%20Subject%20Analysis%20Plan.md) | L1 + L3 | The NCCA "Strand → Topic → LO" traversal that Level 1's chunking (per-strand) and Level 3's per-criterion grading (per-AO) both honour |
| [Backend Strategy For Educational Tutoring System.md](../ideas/Backend%20Strategy%20For%20Educational%20Tutoring%20System.md) | All | The overall architectural pattern (BAML + CocoIndex + Cognee + Graphiti) — Journey uses the GCP-first substrate equivalents (Vertex + Firestore + VectorTarget + MasteryLedger) |

## Out of scope — explicitly NOT absorbed (with reason)

| Idea doc | Why excluded | Future expansion pack |
|---|---|---|
| [x402 / EAS / UMÁ oracle / Brehon / Pinginn / Screpall tokens](../ideas/Agentic%20Education%20Platform%20Development.md) | The user's "Strictly syllabus-relevant" scope explicitly excludes the educational-cryptocurrency stack. Crypto dependencies have no direct relationship with the official syllabus pipeline. | A future "British Isles Journey — Expansion Pack: Verified Bounty" workshop could pick this up. The 4-token model (Pinginn/Screpall/Ungae/Sét) is well-specified and could plug into the MasteryLedger's existing SBT-shaped Firestore schema with no architectural changes |
| A2A swarm via Kafka (per `level_5/agent/server.py`) | The journey's needs are deterministic function-or-agent steps in a single Workflow, not multi-agent consensus across services. We use the simpler `Workflow(edges=[...])` + Memory Bank instead. | A future "British Isles Journey — Expansion Pack: Multi-Org Coordination" could add A2A if/when workshops span multiple orgs |
| iOS / Swift / MLX local-inference tracks | No demo path; mobile is a future "study mode" optional track | Could land via React Native + mlc-llm bindings, behind the existing `gemini_hackathon/cocoindex_flows/_factory` factory pattern |
| Educational-game-dev pipeline (Godot / Unreal) | Visualization is via Gradio + an optional react-force-graph-2d HTML, not a 3D game engine | Could add a Three.js `/vr/` mirror route to the Cloud Run studio, but not in scope for the educational demonstration |
| Bardic gamification (Ollaire / Tamhan / Drisac / Cli / Anruth / Ollamh) | The journey uses real mastery scores (5 NCCA Key Competencies) for the gamification rank, not mythological titles. The 5-stage British Isles education palette is preserved at the theming level | The 6 bardic grades could be appended as a cosmetic label (`Ollaire (Novice) 0/100`) without changing any underlying data |
| [MMO Geospatial Data & Visual RAG.md](../ideas/MMO%20Geospatial%20Data%20&%20Visual%20RAG.md) | The Journey is a workshop experience, not a massively-multiplayer one. The British Isles Education Map (the doc's inspiration) is referenced in Level 0's theming but the gameplay layer is out of scope. | Could land as a "World Map" tab in the studio showing per-subnation mastery density |
| [Use Agent Hook.md — React-specific bindings](../ideas/useAgent%20Hook.md) (React bits only) | The studio uses Gradio, not React. We absorbed the **concept** (a participant can invoke a tool that observes their state) but not the React bindings. | If/when the journey adds a React-based mobile client, the patterns map 1:1 |

## Decisions made during integration (per the user's answers)

1. **Narrative framing** = "British Isles Journey" (no Way Back Home's
   rescue-on-an-alien-planet skin). Real British Isles education palette,
   real NCCA policy PDFs as the source of truth.
2. **Scope** = "Strictly syllabus-relevant". The crypto/A2A/mobile tracks
   are explicitly out (with explicit future expansion-pack homes).
3. **Level 5 reframe** = "Generate an asset" (NOT "mint a certificate").
   The pedagogical value of the syllabus pipeline is grounding AI
   output in the official specification; a generated asset demonstrates
   that every time.
4. **Both modes** = self-hostable (Cloud Build deploy) + demo (offline stub).
   Every level has an in-memory / stub path so the workshop works
   without GCP creds.

## How to verify this audit trail

```bash
# 1. Every level's source mentions its ADK 2 pattern source:
grep -rn "adk2-tutorial\|way-back-home\|loop-lab-table\|support-memory-lab" gemini_hackathon/journey/

# 2. Every level's source lifts from the corresponding pipeline surface:
grep -rn "cocoindex_flows\|ocr_ensemble\|ledger.MasteryLedger\|gemini_hackathon_assets_fibo" gemini_hackathon/journey/

# 3. No level imports anything from the out-of-scope list:
! grep -rn "x402\|EAS\|cumul\|pinginn\|screpall" gemini_hackathon/journey/ && echo OK
```
