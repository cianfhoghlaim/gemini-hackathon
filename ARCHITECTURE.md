# Architecture — gemini_hackathon

> **Status:** bootstrap (proposed in
> [`openspec/changes/2026-08-24-gemini-hackathon-public-v1/`](openspec/changes/2026-08-24-gemini-hackathon-public-v1/))
> **Author:** Cian Mac Aindréisigh
> **Last updated:** 2026-08-24

---

## 1. The high-level shape

```
┌────────────────────────────────────────────────────────────────────────────┐
│                          TanStack Start UI                                  │
│            (Convex + CopilotKit + AG-UI + the 4 chat surfaces)              │
└────────────────────────────────────────────────────────────────────────────┘
                                  │ AG-UI / SSE
                                  ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                          Hono + oRPC backend                                │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ │
│  │ Theming    │ │ Equivalency│ │ Safeguarding│ │  Drift     │ │  call_llm()│ │
│  │ Agent      │ │ Generator  │ │ Mapper      │ │ Detector   │ │  3-tier    │ │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘ └────────────┘ │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ │
│  │  Gateway   │ │  Identity  │ │   Armor    │ │  Observ.   │ │   Memory   │ │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘ └────────────┘ │
│  ┌────────────┐ ┌────────────┐                                              │
│  │  AG-UI     │ │   MCP      │                                              │
│  └────────────┘ └────────────┘                                              │
└────────────────────────────────────────────────────────────────────────────┘
        │                   │                      │              │
        ▼                   ▼                      ▼              ▼
   ┌─────────┐        ┌──────────┐          ┌──────────────┐  ┌────────────┐
   │  BAML   │        │   DLT    │          │   DuckLake + │  │ Langfuse + │
   │ extract │        │  pipes   │          │  MotherDuck  │  │ MLflow +   │
   │ palette │        │ (PDFs)   │          │   (BIEP)     │  │ structlog  │
   │equiv.   │        │          │          │              │  │            │
   │changes  │        │          │          │              │  │            │
   └─────────┘        └──────────┘          └──────────────┘  └────────────┘
```

The architecture is a **layered agent fleet**: the frontend talks
to the backend via the AG-UI protocol, the backend orchestrates
the four idea agents and the seven Fleet primitives, and the
backend pulls data from the BAML extraction pipeline + the DLT
data plane + the DuckLake / MotherDuck lakehouse.

---

## 2. Frontend (TanStack Start + Convex + CopilotKit + AG-UI)

The frontend is a **TanStack Start** app at `web/` with the
following layers:

- **TanStack Start** — the SSR + file-based-routing framework
- **Convex** — the reactive backend database (the `palettes` +
  `equivalencies` + `policies` + `drift_events` tables live here)
- **CopilotKit** — the chat components (`CopilotChat` from
  `@copilotkit/react-core/v2`) + the `useAgent` hook for
  subscribing to the 4 idea agents
- **AG-UI protocol** — the SSE-based event protocol that wires
  the agent runtime to the UI (per the upstream
  `copilotkit-agui` skill)

The frontend has **four chat surfaces**, one per hackathon idea:

1. **Theming chat** at `/theming` — the operator-facing palette
   authoring dashboard (loads a PDF, runs `ExtractSourcePalette`,
   shows the JSON, lets the operator approve / edit / discard)
2. **Equivalency chat** at `/equivalency` — the pupil-facing
   "what is the SQA equivalent of Leaving Cert Maths 3.1?"
   surface
3. **Safeguarding map** at `/safeguarding` — the safeguarding
   lead's side-by-side policy view across the 5 government
   bodies
4. **Drift detector** at `/drift` — the curriculum lead's
   redline-diff view between the previous + current syllabus
   PDFs

The theming custom-properties injection happens at the root
`<html>` element (per the `theming` spec). The injection runs
both client-side (React hook) and server-side (TanStack Start
middleware that sets the variables on the streamed HTML
response) so the first paint is correctly themed.

---

## 3. Backend (Hono + oRPC + BAML)

The backend is a **Hono** HTTP server at `backend/` with
**oRPC** for typed RPC bindings to the frontend.

The backend hosts:

### 3.1 The 4 idea agents

Each agent is a Pydantic AI agent that wraps one BAML function
and exposes it via the AG-UI protocol:

| Agent | BAML function | AG-UI events |
|-------|---------------|--------------|
| `ThemingAgent` | `ExtractSourcePalette` | `PALETTE_EXTRACTED`, `PALETTE_REVIEW` |
| `EquivalencyGenerator` | `ExtractEquivalencies` | `EQUIVALENCY_RESULT` |
| `SafeguardingMapper` | `SearchSafeguardingPolicies` | `SAFEGUARDING_POLICY_RESULT` |
| `CurriculumDriftDetector` | `DetectCurriculumChanges` | `CURRICULUM_DRIFT_RESULT` |

### 3.2 The 7 Fleet primitives

The 7 Fleet primitives are wholesale-copied from Cianfhoghlaim's
`agent-fleet-orchestration` spec (see
[`openspec/specs/agent-fleet-orchestration/spec.md`](openspec/specs/agent-fleet-orchestration/spec.md)
for the canonical contract):

1. **Gateway** — OpenClaw channel-fanout (WebChat + Telegram +
   Slack + Discord + WhatsApp + Teams)
2. **Identity** — BetterAuth + SIWE
3. **Armor** — Turnstile + PocketID admin auth + TinyAuth proxy
4. **Observability** — Langfuse + MLflow + structlog
5. **Memory** — Cognee + Graphiti + LanceDB
6. **AG-UI** — the AG-UI protocol bindings
7. **MCP** — Firecrawl MCP server

### 3.3 The 3-tier LLM router

The router is a `litellm.Router` instance configured with the
3-tier model policy (see §6 below).

---

## 4. Data plane (DLT → DuckLake → MotherDuck)

The data plane mirrors the upstream **British-Isles Education
Pipeline (BIEP)**:

1. **DLT sources** at `dlt_pipelines/`:
   - `official_doc_fetcher` — fetches the official PDFs from
     the 8 jurisdictions + the 5 safeguarding bodies
   - `safeguarding_fetcher` — fetches the safeguarding-policy
     PDFs separately so the safeguarding theming roster is
     independent of the syllabus roster
2. **DuckLake** — the canonical lakehouse (DuckDB + Iceberg
   tables + Parquet on object storage)
3. **MotherDuck** — the managed DuckDB service (the `md:gemini_hackathon`
   database holds all the BIEP tables under the
   `gemini_hackathon.british_isles.*` + `gemini_hackathon.safeguarding.*`
   schemas)
4. **CocoIndex** — the v1 embedding pipeline that writes the
   per-source palette embeddings to LanceDB (the BAAI/bge-m3
   1024-d embedder, per the upstream `cocoindex` skill)

---

## 5. Observability (Langfuse + MLflow + structlog)

Three complementary observability tools:

### 5.1 Langfuse

The primary trace + cost + prompt-management tool. Every
`call_llm()` invocation emits a Langfuse trace with:

- The `llm.tier` (1 / 2 / 3) — the dimension the operator uses
  to see the distribution of fallbacks over time
- The `llm.model` (the resolved model name)
- The `llm.latency_ms`
- The `llm.fallback_reason` (when tier > 1)
- The input / output token counts + the cost in USD

The Langfuse project is `gemini_hackathon` (hosted on Langfuse
Cloud, free tier for the hackathon).

### 5.2 MLflow

The experiment-tracking tool. Every BAML extraction run is
logged as an MLflow experiment with:

- The input PDF path
- The output palette JSON
- The confidence score
- The wall-clock time

MLflow lets the operator compare the extraction quality across
runs (e.g. "did the new ExtractSourcePalette v1.1.0 produce a
better palette than v1.0.0?").

### 5.3 structlog

The structured-logging tool. Every `call_llm()` invocation emits
a structlog event (the format is documented at
[`docs/MODEL_POLICY.md`](docs/MODEL_POLICY.md#structlog-trace-format)).

---

## 6. The 3-tier model policy in detail

The model policy is the **single most important** architectural
decision in this repo. Every `call_llm()` invocation in the
codebase goes through `gemini_hackathon.llm.call_llm()`, which
routes through this LiteLLM Router:

```python
from litellm import Router

router = Router(
    model_list=[
        # Tier 1 — primary
        {
            "model_name": "primary",
            "litellm_params": {
                "model": "minimax-m3",
                "api_key": os.environ["MINIMAX_API_KEY"],
            },
        },
        # Tier 2 — fallback
        {
            "model_name": "fallback",
            "litellm_params": {
                "model": "unsloth/gemma-4-26B-A4B-it-GGUF",
                "api_base": "http://localhost:8080",  # llama.cpp server
            },
        },
        # Tier 3 — final fallback
        {
            "model_name": "emergency",
            "litellm_params": {
                "model": "vertex_ai/gemini-3.5-flash",
                "vertex_credentials": os.environ["GOOGLE_APPLICATION_CREDENTIALS"],
                "vertex_project": "gemini-hackathon",
                "vertex_location": "europe-west1",
            },
        },
    ],
    fallbacks=[
        {"primary": ["fallback"]},
        {"fallback": ["emergency"]},
    ],
)
```

The Cloudflare Workers AI and Qwen3-coder models are **not**
configured (the exclusion is enforced by absence — they cannot
be added without explicitly editing the router config and
removing the `BadRequestError` guard).

See [`docs/MODEL_POLICY.md`](docs/MODEL_POLICY.md) for the
full rationale + the structlog trace format + the BAML client
wiring.

---

## 7. The 7 Fleet primitives

The 7 Fleet primitives are wholesale-copied from Cianfhoghlaim
(per the upstream `agent-fleet-orchestration` spec). Each
primitive is a separate Python module at
`gemini_hackathon/fleet/<primitive>.py`:

| # | Primitive | Module | What it provides |
|--:|-----------|--------|------------------|
| 1 | **Gateway** | `fleet/gateway.py` | OpenClaw channel-fanout (6 channels: WebChat, Telegram, Slack, Discord, WhatsApp, Teams) |
| 2 | **Identity** | `fleet/identity.py` | BetterAuth + SIWE (Sign-In With Ethereum) |
| 3 | **Armor** | `fleet/armor.py` | Turnstile CAPTCHA + PocketID admin auth + TinyAuth proxy |
| 4 | **Observability** | `fleet/observability.py` | Langfuse + MLflow + structlog |
| 5 | **Memory** | `fleet/memory.py` | Cognee knowledge graph + Graphiti temporal KG + LanceDB vector RAG |
| 6 | **AG-UI** | `fleet/ag_ui.py` | AG-UI protocol bindings (per the upstream `ag-ui` skill) |
| 7 | **MCP** | `fleet/mcp.py` | Firecrawl MCP server + the 12-tool surface |

The wholesale-copy convention lives at
[`openspec/specs/wholesale-copy-convention/spec.md`](openspec/specs/wholesale-copy-convention/spec.md)
(upstream). The convention guarantees that every primitive is
**byte-for-byte** the upstream module, with only the import paths
rewritten.

---

## 8. The 4 hackathon ideas (in detail)

### 8.1 Idea 1: Per-source theming

- **Input**: an official PDF (e.g. `scr-advisory-report_en.pdf`)
- **BAML function**: `ExtractSourcePalette(pdf_path, source_name)`
- **Output**: a `SourcePalette` JSON with the brand palette +
  typography + iconography
- **Frontend**: the CSS custom properties are injected on the
  root `<html>` element so the brand identity is visible

### 8.2 Idea 2: Cross-jurisdiction equivalency generator

- **Input**: a `Topic` (subject, level, topic_id) + the source
  PDF
- **BAML function**: `ExtractEquivalencies(topic, pdf, target_jurisdiction)`
- **Output**: a list of `EquivalencyMatch` entries (one per
  candidate specification in the destination body)
- **Subjects at launch**: Mathematics, Chemistry, English

### 8.3 Idea 3: Safeguarding policy map

- **Input**: a safeguarding topic (e.g. "online learning
  environments")
- **Agent**: `SafeguardingMapper` (searches the 5 bodies'
  policies in parallel)
- **Output**: a side-by-side view of the 5 policies, each
  rendered in its own brand (the palettes from
  `themes/safeguarding/`)

### 8.4 Idea 4: Curriculum drift detector

- **Input**: the current syllabus PDF + the previous syllabus PDF
- **BAML function**: `DetectCurriculumChanges(current_pdf, previous_pdf)`
- **Output**: a `CurriculumChanges` JSON with new / removed /
  weight-shifted topics
- **Frontend**: a redline-diff view (the source PDF on the
  left, the destination PDF on the right, the changes highlighted
  in the middle)

---

## 9. The BAML extraction pipeline

The BAML extraction pipeline follows the upstream **4-path OCR/VLM
ensemble** pattern (per the BIEP v1 contract):

```
            Official PDF (e.g. scr-advisory-report_en.pdf)
                                  │
                                  ▼
            ┌──────────────────────────────────┐
            │       4-path OCR/VLM ensemble    │
            │                                  │
            │  Path 1: PyMuPDF text extraction │
            │  Path 2: Tesseract OCR           │
            │  Path 3: Google Document AI      │
            │  Path 4: Claude Sonnet VLM       │
            └──────────────────────────────────┘
                                  │
                                  ▼
            ┌──────────────────────────────────┐
            │       BAML extraction            │
            │                                  │
            │  ExtractSourcePalette            │
            │  ExtractEquivalencies            │
            │  DetectCurriculumChanges         │
            └──────────────────────────────────┘
                                  │
                                  ▼
            ┌──────────────────────────────────┐
            │       RAGAS consensus            │
            │                                  │
            │  - Palette confidence scoring    │
            │  - Topic match scoring           │
            │  - Drift delta scoring           │
            └──────────────────────────────────┘
                                  │
                                  ▼
            Final palette / equivalency / drift JSON
```

The 4 paths produce independent extractions; RAGAS scores the
agreement between them; the consensus output is the one with
the highest RAGAS score. The pipeline produces:

- A `SourcePalette` JSON per official PDF (Idea 1)
- A list of `EquivalencyMatch` entries per topic (Idea 2)
- A `CurriculumChanges` JSON per diff (Idea 4)

---

## 10. References

- [`README.md`](README.md) — the main project README
- [`AGENTS.md`](AGENTS.md) — the root agent routing file
- [`docs/MODEL_POLICY.md`](docs/MODEL_POLICY.md) — the model
  policy documentation
- [`docs/THEMING.md`](docs/THEMING.md) — the theming guide
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — the deployment
  guide
- [`openspec/changes/2026-08-24-gemini-hackathon-public-v1/proposal.md`](openspec/changes/2026-08-24-gemini-hackathon-public-v1/proposal.md) —
  the bootstrap OpenSpec proposal
- [`openspec/specs/theming/spec.md`](openspec/specs/theming/spec.md) —
  the canonical theming spec (post-archive)
- [`openspec/specs/model-policy/spec.md`](openspec/specs/model-policy/spec.md) —
  the canonical model-policy spec (post-archive)
- [`openspec/specs/equivalency/spec.md`](openspec/specs/equivalency/spec.md) —
  the canonical equivalency spec (post-archive)