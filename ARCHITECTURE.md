# gemini_hackathon — Architecture

## 1. Goals

Per-source theming across the British Isles + cross-jurisdiction
equivalency + generative asset pipeline + (deferred) NCCA-progressed
certificates. Everything flows through a 2-tier LiteLLM router whose
visible surface (the `hackathon` model profile) only ever mentions
Gemini 3.5 and Gemma 4 26B-A4B.

## 2. The dual-profile model policy

Every LLM call goes through `gemini_hackathon.call_llm.call_llm(messages)`.
The router reads `MODEL_PROFILE` (`hackathon` | `dev`) and walks the
matching tier list. Each tier is resolved via
`gemini_hackathon.models.model_for(family, role, profile=...)` against
the in-process `MODEL_REGISTRY` (ported from
`cianfhoghlaim/meaisinfhoghlaim/models/model_registry.py:v6`).

The registry holds 24 entries across 7 families:

```
text_llm       7  (hackathon: 3  / dev: +4)
ocr_vision     5
embedder       1
rerank         1
image_gen      7  (FIBO + 3 InvokeAI + 2 Unsloth Studio + SDXL legacy)
voice          2
translation    1
```

Excluded at runtime: Cloudflare Workers AI (`@cf/*`), Qwen3-coder-*.

## 3. The OCR/VLM capability router

`gemini_hackathon.ocr.ocr()` dispatches to one of 7 capabilities:

```
Capability        Default backend      Default model          Status
────────────────  ──────────────────  ─────────────────────  ──────────
forms             llama-swap           paddleocr-vl-1.6       ready
layout            llama-swap           qwen3-vl-8b            ready
tables+latex      olmocr               olmocr                 not deployed
doctags           docling-serve        docling-tags           not deployed
gaelic            llama-swap           gemma-4-26b-a4b        ready
english           llama-swap           qwen3-vl-8b            ready
tesseract-fallback llama-swap          paddleocr-vl-1.6       ready
```

The single decision table is `_DISPATCH_TABLE`; only the 4
llama-swap-backed capabilities work in this environment, and the rest
degrade with `CapabilityUnavailableError` (no hang).

## 4. The generative asset pipeline

BAML extraction outputs flow into `AssetControlRecord` (FIBO-compatible
JSON control), then dispatch to one of 4 image-gen backends:

```
AssetControlRecord → ImageGenRouter.generate()
    → ComfyUI + FIBO (provenance-critical)
    → InvokeAI  (FLUX.2-dev / Z-Image-Turbo / Qwen-Image)
    → Unsloth Studio  (DiffusionGemma 26B-A4B / Qwen-Image 2512)
    → Stub fallback  (deterministic PNG when all live backends are down)
```

The provenance row carries `source_pdf_path + page`, `learning_outcome_id`,
`control_record_hash`, `seed`, `backend`, `model_key`, `duration_ms`.

## 5. The DuckDB-WASM analytical surface

`web/lib/duckdb.ts` reads the same `.duckdb` file in the browser that
the Python backend writes to, so the SQL dialect is identical between
server and client. Two views:

- **Document Explorer** — every row in `official_documents`, joined with
  page-image URLs from the DLT pipeline.
- **Comparison Leaderboard** — every row in `model_comparisons`, ranked
  by RAGAS score.

## 6. The theming layer

13 palettes in `themes/` — 7 jurisdictions + 3 England boards + 5
safeguarding bodies. Each palette file is JSON with primary/secondary/
accent/background/text + typography + flag + logo URL.

`SourcePaletteProvider` (React context, `web/components/themes/`) fetches
the palettes via `/api/themes`, injects them as CSS custom properties,
and the entire UI re-themes live when the active palette changes.

## 7. The Convex schema

The schema splits the jurisdiction axis from the board axis and carries
the Phase-11 hooks:

- `palettes` — the 13 sources, indexed by axis (`jurisdiction` /
  `board` / `safeguarding`).
- `subjects` — per (source_key, level, board, subject).
- `learningOutcomes` — one row per syllabus learning outcome; the load-bearing
  artefact for the deferred Phase-11 certificate substrate.
- `assessmentEvents` — formative / diagnostic / summative learner attempts,
  with the NCCA CBA descriptor vocabulary.
- `outcomeMastery` — per (learner, outcome) mastery ledger.
- `certificates` — generated certs for Leaving Cycle / Junior Cycle /
  CBA / Short Course / L1LP / L2LP / Special Education (always marked
  "unofficial" on the artefact).
- `assetProvenance` — Phase-8 chain back to source.
- `equivalencies` + `changeEvents` + `policies` — cross-jurisdiction
  equivalents + the change-sensor event log + safeguarding policy docs.

## 8. Local dev topology

- `gemini-hackathon` (the app container; `Dockerfile` builds)
- `llama-swap` (OCR/VLM gateway; uses
  `cianfhoghlaim/bonneagar/stacks/llama-swap/config.yaml`)
- `duckdb` (named-volume mount for the .duckdb file)

Unsloth Studio and the LLM backends run **outside Docker** on the host:
Unsloth Studio at `127.0.0.1:8888`, Gemini via Vertex ADC, etc.

## 9. Observability

`gemini_hackathon.observability` ports the
`cianfhoghlaim/observability/*` modules. Emits:

- `llm.invocation` (canonical — `llm.tier` / `llm.model` / `llm.backend` /
  `llm.latency_ms` / `llm.tokens_in` / `llm.tokens_out` /
  `llm.fallback_reason`)
- `agent.trace_opened` + `agent.trace_closed` (per-agent spans)
- `asset.generated` (per-asset provenance)

Langfuse :3001 + MLflow :5050 are both live and wire in when the env
vars are set.
