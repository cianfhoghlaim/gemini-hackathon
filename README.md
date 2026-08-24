# gemini_hackathon — Per-Source Theming Across the British Isles

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![GitHub Actions CI](https://img.shields.io/badge/GitHub_Actions-CI-2088FF?logo=githubactions&logoColor=white)](.github/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org)

> **An agentic system that recognises every British Isles jurisdiction's
> brand identity — and renders itself accordingly.**

The British Isles have **eight jurisdictions** and **multiple
awarding bodies**, each with its own official palette, typography,
and iconography. `gemini_hackathon` builds a single agent fleet
that recognises all of them and adapts in real time — a Leaving
Cert pupil sees NCCA green + Barlow headings, an SQA pupil sees
SQA blue + the saltire flag, a WJEC pupil sees WJEC red + the
dragon, and so on.

This repo is the submission for the **Google "All Things Agentic"
Hackathon, Aug 2026**.

---

## The four hackathon ideas

| # | Idea | What it demonstrates |
|--:|------|---------------------|
| 1 | **Per-source theming** | BAML `ExtractSourcePalette` extracts the brand palette, typography, and iconography from each official PDF; the frontend injects the CSS custom properties at runtime |
| 2 | **Cross-jurisdiction equivalency generator** | BAML `ExtractEquivalencies` finds the SQA / AQA / WJEC / CCEA / OCR / Pearson equivalent of a Leaving Cert topic, with a confidence score per match |
| 3 | **Safeguarding policy map** | The 5 government bodies' safeguarding policies (gov.ie, gov.uk, gov.scot, gov.wales, NI Education) appear side-by-side, each rendered in its own brand |
| 4 | **Curriculum drift detector** | BAML `DetectCurriculumChanges` redline-diffs the previous + current syllabus PDFs and surfaces new / removed topics |

---

## The seven Fleet primitives

The agent fleet is built on the canonical **Cianfhoghlaim Fleet
primitives**, wholesale-copied from the upstream
`agent-fleet-orchestration` spec:

1. **Gateway** — OpenClaw channel-fanout (WebChat + Telegram +
   Slack + Discord + WhatsApp + Teams)
2. **Identity** — BetterAuth + SIWE (Sign-In With Ethereum)
3. **Armor** — Turnstile + PocketID admin auth + TinyAuth proxy
4. **Observability** — Langfuse + MLflow + structlog
5. **Memory** — Cognee knowledge graph + Graphiti temporal KG +
   LanceDB vector RAG
6. **AG-UI** — AG-UI protocol bindings for TanStack Start +
   CopilotKit
7. **MCP** — Firecrawl MCP server + the canonical 12-tool surface

---

## The 3-tier model policy

Every `call_llm()` invocation routes through this 3-tier LiteLLM
chain (the canonical Cianfhoghlaim model policy):

| Tier | Model | Role | Litellm name |
|-----:|-------|------|-------------|
| 1    | **minimax-m3** | Primary (default) | `minimax-m3` |
| 2    | **unsloth/gemma-4-26B-A4B-it-GGUF** | Fallback when minimax-m3 is unavailable | `unsloth/gemma-4-26B-A4B-it-GGUF` |
| 3    | **vertex_ai/gemini-3.5-flash** | Final fallback (Google Cloud Vertex AI) | `vertex_ai/gemini-3.5-flash` |

**Cloudflare Workers AI** (`@cf/meta/llama-3.1-8b-instruct`,
`@cf/google/gemma-7b-it`, etc.) is **explicitly excluded** —
the rationale is documented at
[`docs/MODEL_POLICY.md`](docs/MODEL_POLICY.md).

See [`docs/MODEL_POLICY.md`](docs/MODEL_POLICY.md) for the full
rationale + the LiteLLM router config + the structlog trace
format.

---

## British Isles coverage (8 jurisdictions)

```
                  ┌───────────────────────────────────────────┐
                  │           British Isles coverage          │
                  ├───────────────────────────────────────────┤
                  │ Ireland        (ncca.ie)        NCCA green│
                  │ England AQA    (aqa.org.uk)     AQA navy  │
                  │ England OCR    (ocr.org.uk)     OCR red   │
                  │ England Pearson (qualifications Pearson blue│
                  │                .pearson.com)              │
                  │ Scotland       (sqa.org.uk)     SQA blue  │
                  │ Wales          (wjec.co.uk)     WJEC red  │
                  │ Northern       (ccea.org.uk)    CCEA blue │
                  │   Ireland                                   │
                  │ Isle of Man    (gov.im/education) IoM red │
                  └───────────────────────────────────────────┘
```

Each palette lives at `themes/<source_key>_palette.json` (e.g.
`themes/ncca_palette.json`).

---

## Safeguarding coverage (5 bodies)

The safeguarding policy map covers 5 government bodies:

| Body | Source key | Palette file |
|------|-----------|--------------|
| Department of Education (Ireland) | `gov.ie/education` | `themes/safeguarding/ie_dept_education_palette.json` |
| Department for Education (UK) | `gov.uk/dfe` | `themes/safeguarding/uk_dfe_palette.json` |
| Scottish Government Education | `education.gov.scot` | `themes/safeguarding/scotland_gov_palette.json` |
| Welsh Government Education | `gov.wales/education` | `themes/safeguarding/wales_gov_palette.json` |
| CCEA Safeguarding (NI) | `ccea.org.uk/safeguarding` | `themes/safeguarding/ni_ccea_palette.json` |

---

## Quick start

```bash
# Clone the repo
git clone https://github.com/your-org/gemini_hackathon.git
cd gemini_hackathon

# One-shot setup (Python 3.11+, uv)
./setup.sh

# Run the theming extraction notebook
uv run marimo edit notebooks/theming_extraction.py

# Run the tests
mise run test

# Validate the openspec change
openspec validate 2026-08-24-gemini-hackathon-public-v1 --strict
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          TanStack Start UI                           │
│        (Convex + CopilotKit + AG-UI + the 4 chat surfaces)          │
└─────────────────────────────────────────────────────────────────────┘
                                 │ AG-UI / SSE
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          Hono + oRPC backend                         │
│    (4 idea agents + 7 Fleet primitives + the 3-tier LLM router)     │
└─────────────────────────────────────────────────────────────────────┘
        │                  │                    │           │
        ▼                  ▼                    ▼           ▼
   ┌─────────┐      ┌──────────┐        ┌──────────┐  ┌──────────┐
   │  BAML   │      │   DLT    │        │  Duck    │  │ Langfuse │
   │ extract │      │  pipes   │        │ Lake +   │  │ + MLflow │
   │ palette │      │ (PDFs)   │        │MotherDuck│  │+ structlog│
   │equiv.   │      │          │        │          │  │          │
   │changes  │      │          │        │          │  │          │
   └─────────┘      └──────────┘        └──────────┘  └──────────┘
```

For the full architecture deep-dive, see
[`ARCHITECTURE.md`](ARCHITECTURE.md).

---

## Project structure

```
gemini_hackathon/
├── backend/                       # Hono + oRPC backend
├── web/                           # TanStack Start frontend
├── baml_src/gemini_hackathon/     # BAML extraction functions
├── dlt_pipelines/                 # DLT source definitions
├── notebooks/                     # marimo dashboards
├── themes/                        # 8 jurisdiction palettes
│   └── safeguarding/              # 5 safeguarding body palettes
├── gemini_hackathon/              # Python package
│   ├── __init__.py
│   └── theming.py                 # palette loader
├── openspec/                      # OpenSpec change proposals
│   ├── changes/                   # active changes
│   │   └── archive/               # archived changes
│   └── specs/                     # canonical specs (post-archive)
├── docs/                          # project documentation
├── infra/                         # Pulumi IaC
├── tests/                         # pytest test suite
├── setup.sh                       # one-shot setup
├── Dockerfile                     # multi-stage, uv-based
├── docker-compose.yaml            # backend + frontend + observability
├── ARCHITECTURE.md                # architecture deep-dive
├── AGENTS.md                      # root agent routing file
└── README.md                      # this file
```

---

## License

This project is released under the **MIT License**. See
[`LICENSE`](LICENSE) for the full text.

Copyright © 2026 Cian Mac Aindréisigh.