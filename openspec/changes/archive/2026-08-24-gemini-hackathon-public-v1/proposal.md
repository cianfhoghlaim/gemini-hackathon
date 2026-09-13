# Change: gemini-hackathon-public-v1

> **opened-by:** gemini-hackathon-public-v1
> **target repo:** `gemini_hackathon` (this repo)
> **hackathon:** Google "All Things Agentic" Hackathon, Aug 2026
> **author:** Cian Mac Aindréisigh

## Why

The Google "All Things Agentic" Hackathon (Aug 2026) asks for projects
that demonstrate **agentic systems** — projects in which autonomous
agents reason, act, and observe across multi-step workflows, with
human-in-the-loop only where strictly necessary.

The British Isles have **eight jurisdictions** (Ireland, England,
Scotland, Wales, Northern Ireland, Isle of Man, Jersey, Guernsey)
and **multiple awarding bodies** (NCCA, AQA, OCR, Pearson, SQA, WJEC,
CCEA, IoM Government). Each of these publishes its own
**official examination PDFs** with its own brand identity, palette,
typography, and iconography. A pupil preparing for the Leaving Cert
in Dublin has no easy way to navigate to the equivalent specification
in SQA's National 5 or WJEC's A-Level. A safeguarding lead at the
Department of Education (Ireland) cannot quickly find the matching
policy in the Department for Education (UK) without manually opening
eight websites.

The **gemini_hackathon** project tackles four concrete ideas on top of
the **Cianfhoghlaim Fleet primitives** (see `openspec/specs/agent-fleet-orchestration`):

1. **Per-source theming across the British Isles.** Extract the
   brand palette, typography, and iconography from each of the eight
   jurisdictions' official PDFs and inject the resulting CSS custom
   properties at runtime, so the same application can render as NCCA
   green-and-gold for one pupil, SQA blue for another, and WJEC red
   for a third.
2. **Cross-jurisdiction equivalency generator.** Given a Leaving
   Cert topic, produce the matching specification in SQA, WJEC, AQA,
   CCEA, and Pearson using a BAML `ExtractEquivalencies` function
   that walks the official syllabus PDFs and emits a confidence
   score per equivalency.
3. **Safeguarding policy map.** Given a safeguarding topic (e.g.
   "online learning environments"), find the matching policy across
   the five government departments (gov.ie, gov.uk, gov.scot,
   gov.wales, NI Education) with the source-palette UI to keep each
   government's visual identity intact.
4. **Curriculum drift detector.** Given a current syllabus PDF and
   a fresh published version, extract the structural changes
   (new topics, removed topics, assessment-weight shifts) using the
   BAML `DetectCurriculumChanges` function and emit a redline diff.

These four ideas together demonstrate that a single **agent fleet**
can cover the British Isles end-to-end — a use case the
Cianfhoghlaim architecture was designed for but had not previously
applied to this domain.

## What Changes

- **3 NEW canonical specs** with ADDED Requirements:
  - `theming` — per-source palette extraction + CSS custom property
    injection
  - `model-policy` — the 3-tier LiteLLM router policy
    (minimax-m3 → unsloth/gemma-4-26B → vertex_ai/gemini-3.5-flash)
  - `equivalency` — the cross-jurisdiction BAML extraction
- **7 Fleet primitives** are reused unchanged from the upstream
  Cianfhoghlaim architecture (per the `agent-fleet-orchestration`
  spec): `Gateway`, `Identity`, `Armor`, `Observability`, `Memory`,
  `AG-UI`, `MCP`
- **The 3-tier model policy** is enforced at the LiteLLM router
  level, not at the agent level: every `call_llm()` invocation in
  the codebase goes through `gemini_hackathon.llm.call_llm()` which
  routes to the next tier on failure
- **Observability** is wired to Langfuse (cost + prompt management) +
  MLflow (experiment tracking) + structlog (per-tier trace logs)
  from day one
- **DLT pipelines** fetch the official PDFs for the 13 sources
  (8 jurisdictions + 5 safeguarding bodies) and load them into
  DuckLake + MotherDuck
- **Per-source official-document theming** is the foundational
  pattern that unifies all four ideas (the equivalency generator
  re-uses the per-source palette to render the result in the
  destination body's brand)

## Model Policy

The **3-tier model policy** is enforced project-wide:

| Tier | Model | Role | Litellm name |
|-----:|-------|------|-------------|
| 1    | **minimax-m3** | Primary (default) | `minimax-m3` |
| 2    | **unsloth/gemma-4-26B-A4B-it-GGUF** | Fallback when minimax-m3 is unavailable | `unsloth/gemma-4-26B-A4B-it-GGUF` |
| 3    | **vertex_ai/gemini-3.5-flash** | Final fallback (Google Cloud Vertex AI) | `vertex_ai/gemini-3.5-flash` |

### Explicitly excluded models

- **Cloudflare Workers AI** (`@cf/meta/llama-3.1-8b-instruct`,
  `@cf/google/gemma-7b-it`, etc.) — **EXCLUDED**. Cloudflare's
  Workers AI models have inconsistent quality across regions,
  unpredictable cost (per-request pricing that does not match
  billing expectations), and create vendor lock-in to a single
  edge platform. The Cianfhoghlaim architecture is
  cloud-agnostic by design; Workers AI contradicts that posture.
- **Qwen3-coder-*** (`qwen3-coder-32b-instruct`, etc.) —
  **EXCLUDED**. Coding-tuned models do not suit the pedagogical
  use case: they over-format prose, hallucinate code comments
  inside natural-language answers, and prioritise completion
  accuracy over factual recall.

Every `call_llm()` invocation emits a structlog event with the
`llm.tier` field set to `"1"` / `"2"` / `"3"` so that operators
can verify in Langfuse which tier actually served the request.

## Capabilities

### New Capabilities

- `theming`: The per-source palette extraction capability, with 13
  source palettes (8 BI jurisdictions + 5 safeguarding bodies)
  loaded from `themes/*.json` + `themes/safeguarding/*.json` and
  exposed to the frontend as CSS custom properties.
- `model-policy`: The 3-tier LiteLLM router policy with Cloudflare
  Workers AI + Qwen3-coder exclusion.
- `equivalency`: The cross-jurisdiction equivalency generator
  backed by the BAML `ExtractEquivalencies` function.

## Impact

- **1 NEW BAML function family** (`ExtractSourcePalette` +
  `ExtractEquivalencies` + `DetectCurriculumChanges`) under
  `baml_src/gemini_hackathon/`
- **1 NEW 13-row palette catalog** at `themes/` + `themes/safeguarding/`
  (the 13 JSON files already shipped with this repo)
- **1 NEW Python loader** at `gemini_hackathon/theming.py`
  (already shipped) — exposes `load_palette(source_key)`,
  `list_all_palettes()`, and the `Palette` dataclass
- **1 NEW Hono + oRPC backend** at `backend/`
- **1 NEW TanStack Start frontend** at `web/`
- **2 NEW DLT pipelines** at `dlt_pipelines/`
  (`official_doc_fetcher`, `safeguarding_fetcher`)
- **1 NEW marimo notebook** at `notebooks/theming_extraction.py`
  (operator-facing palette-authoring dashboard)

### Breakage

None. This is a fresh repository — there is no prior API surface
to break. The model policy is the only enforcement point that any
external consumer of `gemini_hackathon.llm.call_llm()` would need
to be aware of.

## Dependencies

- **Blocked by:** nothing (this is a fresh-repo bootstrap change).
- **Cross-repo:** the Fleet primitives (`Gateway`, `Identity`,
  `Armor`, `Observability`, `Memory`, `AG-UI`, `MCP`) are
  wholesale-copied from Cianfhoghlaim, **not** introduced as a new
  dependency. The wholesale-copy convention lives at
  `openspec/specs/wholesale-copy-convention/spec.md` (upstream).
- **Affected repos:** `gemini_hackathon` only.

## Cross-references

- [`themes/ncca_palette.json`](../../../themes/ncca_palette.json) —
  the NCCA palette (Ireland, Senior Cycle)
- [`themes/aqa_palette.json`](../../../themes/aqa_palette.json) —
  the AQA palette (England, A-Level + GCSE)
- [`themes/safeguarding/ie_dept_education_palette.json`](../../../themes/safeguarding/ie_dept_education_palette.json) —
  the Department of Education (Ireland) safeguarding palette
- [`gemini_hackathon/theming.py`](../../../gemini_hackathon/theming.py) —
  the Python palette loader + the `Palette` dataclass + the
  `extract_source_palette_from_pdf()` stub
- [`openspec/changes/2026-08-24-gemini-hackathon-public-v1/tasks.md`](tasks.md) —
  the task checklist
- [`openspec/changes/2026-08-24-gemini-hackathon-public-v1/specs/theming/spec.md`](specs/theming/spec.md) —
  the theming spec delta
- [`openspec/changes/2026-08-24-gemini-hackathon-public-v1/specs/model-policy/spec.md`](specs/model-policy/spec.md) —
  the model-policy spec delta
- [`openspec/changes/2026-08-24-gemini-hackathon-public-v1/specs/equivalency/spec.md`](specs/equivalency/spec.md) —
  the equivalency spec delta