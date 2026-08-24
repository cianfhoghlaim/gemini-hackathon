# gemini_hackathon — Per-Source Theming Across the British Isles

> The Google All Things Agentic Hackathon submission that turns 13 official
> British-Isles education sources into a single themable surface, with
> Gemini 3.5 as the primary model and Gemma 4 26B-A4B via Unsloth Studio
> as the fallback.

[![MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)
[![CI](https://img.shields.io/badge/CI-GitHub_Actions-blue)](.github/workflows/ci.yml)

---

## The 4 Hackathon Ideas

| Idea | What it does |
|---|---|
| **Marking Grader Workflow** | Compares a student's LC answer to the marking scheme, produces a per-question mark breakdown using the NCCA assessment vocabulary (Exceptional / Above / In line / Yet to meet) |
| **Adaptive Tutor** | Personalised tutoring grounded in the active source's palette + jurisdiction + syllabus outcomes |
| **Cross-Jurisdiction Equivalency Generator** | Given an Ireland LC Mathematics topic, generates the equivalent topics in AQA, OCR, Pearson, SQA, WJEC, CCEA, Jersey, Guernsey, IoM |
| **Curriculum Change Sensor** | Detects new syllabus PDFs / official source changes and re-runs the theming extraction + BAML ExtractPalette |

## The 7 Fleet Primitives

| Primitive | Purpose |
|---|---|
| `FleetGateway` | Routes user queries to the right idea agent based on LiteLLM keyword matching |
| `FleetIdentity` | Authentication + role-based access (anonymous / pupil / teacher / safeguarding_lead) |
| `FleetModelArmor` | Input sanitisation: prompt-injection + jailbreak + PII redaction |
| `FleetObservability` | Langfuse + MLflow + structlog tracing |
| `FleetMemory` | Letta long-term memory layer |
| `FleetMcpCurriculum` | MCP curriculum-lookup tool exposed to all 4 idea agents |
| `FleetAguiBridge` | 17-event AG-UI streaming protocol bridge for the CopilotKit frontend |

## Dual-Profile Model Policy

The active `MODEL_PROFILE` env var gates which registry entries are visible. The submission and docs use the `hackathon` profile only.

### `hackathon` profile (default — exposed in submission)

| Tier | Model | Backend | Notes |
|---|---|---|---|
| 1 (primary) | `gemini-3.5-flash` | Vertex AI (default) / AI Studio | Promotes Google Cloud usage; toggle via `GEMINI_BACKEND` |
| 2 (fallback) | `gemma-4-26b-a4b` | Unsloth Studio :8888 | Same family as the vision variant, served from the same endpoint |

### `dev` profile (harness only — NOT exposed in submission)

| Tier | Model | Backend |
|---|---|---|
| 1 | `gemini-3.5-flash` | Vertex / AI Studio |
| 2 | `gemma-4-26b-a4b` | Unsloth Studio |
| 3 (dev) | `minimax-m3` | api.minimax.io |
| extras | `qwen3.8-27b`, `deepseek-v4-flash`, `kimi-k2.6` | Unsloth Studio |

**Hard-rejected at runtime (via `gemini_hackathon.call_llm._assert_model_allowed`):**

- Cloudflare Workers AI (`@cf/*` model strings)
- Qwen3-coder-* model strings

## British Isles Coverage

### Jurisdictions (8 — per `bie-8-jurisdictions` spec)

- 🇮🇪 Ireland (NCCA, LC + JC)
- 🏴󠁧󠁢󠁥󠁮󠁧󠁿 England (AQA + OCR + Pearson — board axis)
- 🏴󠁧󠁢󠁳󠁣󠁴󠁿 Scotland (SQA)
- 🏴󠁧󠁢󠁷󠁬󠁳󠁿 Wales (WJEC, Welsh-medium + EN)
- 🇬🇧 Northern Ireland (CCEA)
- 🇯🇪 Jersey (Crown Dependency, EN + French hybrid)
- 🇬🇬 Guernsey (Crown Dependency)
- 🇮🇲 Isle of Man (gov.im/education)

### Safeguarding (5)

- 🇮🇪 Department of Education (DEIS + Well-Being)
- 🇬🇧 Department for Education (KCSiE 2026)
- 🏴󠁧󠁢󠁳󠁣󠁴󠁿 Scottish Government (Included, Engaged and Involved)
- 🏴󠁧󠁢󠁷󠁬󠁳󠁿 Welsh Government (Keeping Learners Safe)
- 🇬🇧 CCEA (Safeguarding and Child Protection)

## Generative Asset Pipeline (Phase 8)

The BAML extraction outputs flow into an `AssetControlRecord` (FIBO-compatible JSON control) and dispatch to one of three image-gen backends:

| Backend | Models | Use |
|---|---|---|
| **ComfyUI + FIBO** | FIBO | Provenance-critical artefacts (certificates) — JSON-native, 1B+ licensed, commercial indemnity |
| **InvokeAI** | FLUX.2-dev, Z-Image-Turbo, Qwen-Image | Quality / fast / bilingual |
| **Unsloth Studio** | DiffusionGemma 26B-A4B, Qwen-Image 2512 | Gemma-consistent path |

Every generated asset carries a `asset_provenance` row: `source_pdf_path`, `source_page`, `learning_outcome_id`, `control_record_hash`, `seed`, `backend`, `model_key`.

## Phase 11 Substrate — Certificate-Ready

Three Convex tables already exist in the schema (deferred feature):

- `learningOutcomes` — one row per syllabus learning outcome across all jurisdictions + boards
- `assessmentEvents` — formative / diagnostic / summative learner attempts at outcomes (CBA descriptor vocabulary)
- `outcomeMastery` — per-(learner, outcome) mastery ledger
- `certificates` — generated certificates for Leaving Cycle / Junior Cycle / CBA / Short Course / L1LP / L2LP / Special Education (always marked "unofficial")

These land now so the certificate substrate is additive, not a schema migration.

## Quick Start

```bash
# 1. Install + run the BAML generator
uv sync
uv run baml-cli generate

# 2. Run the DLT pipelines (downloads 134 LC PDFs + 5 safeguarding policies)
uv run python -m dlt_pipelines.official_doc_fetcher
uv run python -m dlt_pipelines.safeguarding_fetcher

# 3. Verify theming
uv run python -c "from gemini_hackathon import list_all_palettes; print(len(list_all_palettes()))"
# → 15 (7 jurisdictions + 3 boards + 5 safeguarding)

# 4. Run the Gemini-vs-Gemma4 comparison harness
uv run gemini-hackathon compare --pdf /tmp/lc_chem_2024.pdf

# 5. Frontend (separate package)
cd web
bun install
bun run dev
```

## Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                            Browser (TanStack Start)                    │
│                                                                        │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────────┐  │
│  │ BritainIslesMap  │  │ Comparison       │  │ Doc Explorer        │  │
│  │ (MapLibre+deck)  │  │ Leaderboard      │  │ (DuckDB-WASM)       │  │
│  └──────────────────┘  └──────────────────┘  └─────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  SourcePaletteProvider (CSS-variable injection, 13 palettes)     │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  CopilotKit + AGUIChat (17-event AG-UI streaming)                │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────┬───────────────────────────────────────┘
                                 │
                  /api/copilotkit + /api/agents (Hono)
                                 │
┌────────────────────────────────▼───────────────────────────────────────┐
│                           Python Backend                                │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │   gemini_hackathon.call_llm  (3-tier LiteLLM router)             │  │
│  │   ─ profile=hackathon  : gemini-3.5 → gemma-4-26b-a4b           │  │
│  │   ─ profile=dev        : + minimax-m3 + Unsloth text set       │  │
│  │   ─ exclusion guard    : @cf/* + qwen3-coder-*                  │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │   gemini_hackathon.ocr  (capability router — 7 capabilities ×     │  │
│  │                             6 backends; llama-swap :8080 live)   │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │   gemini_hackathon.assets  (FIBO + InvokeAI + Unsloth Studio;     │  │
│  │                             AssetControlRecord + provenance)     │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │   gemini_hackathon.compare (RAGAS-fidelity harness → DuckDB)     │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │   dlt_pipelines/  (148 LC PDFs → DuckDB official_documents)      │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │   gemini_hackathon.observability  (Langfuse :3001, MLflow :5050) │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────┬───────────────────────────────────────┘
                                 │
                  DuckDB (local)  ←  MotherDuck (managed DuckLake)
                                 │
                  llama-swap :8080  (live, 12 OCR/VLM models)
                  Unsloth Studio :8888  (live, Gemma 4 + DiffusionGemma)
                  Vertex AI / AI Studio  (gemini-3.5-flash)
                  ComfyUI :8188  (FIBO)  [down in this env]
                  InvokeAI :9090  (FLUX.2-dev)  [down in this env]
```

## What's Verified Live (this box)

| Service | URL | Status |
|---|---|---|
| Unsloth Studio | `127.0.0.1:8888` | OPEN (Gemini-3.5 backend fallback target) |
| llama-swap | `127.0.0.1:8080` | OPEN (12 OCR/VLM models) |
| Langfuse | `127.0.0.1:3001` | OPEN (LLM observability) |
| MLflow | `127.0.0.1:5050` | OPEN (experiment tracking) |
| MotherDuck | `md:cianfhoghlaim` | OPEN (managed DuckLake) |
| ComfyUI | `127.0.0.1:8188` | down (Phase 8 adapter has stub fallback) |
| InvokeAI | `127.0.0.1:9090` | down (Phase 8 adapter has stub fallback) |

## Tests

```
$ uv run pytest tests/ -q
164 passed, 13 skipped in 0.37s
```

The 13 skips are Python 3.11+ DLT tests where this box's venv runs 3.9.

## License

MIT — see [LICENSE](LICENSE).
