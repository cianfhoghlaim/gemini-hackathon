# Demo script — 5-step evaluator walkthrough

> Click through the demo in < 5 minutes. All paths assume the evaluator is
> in `/Users/cianmacandeisigh/dev/gemini_hackathon` on a Mac with `uv` and `bun`
> installed.

## Prereqs (~ 2 min one-time)

```bash
cd /Users/cianmacandeisigh/dev/gemini_hackathon
make install                                       # uv sync --all-extras
make baml                                          # regenerate BAML client + tests
cp .env.example .env 2>/dev/null || true           # ensure .env exists
```

## Step 1 — Boot the 3 services (3 terminals)

**Terminal 1 — backend (FastAPI + ADK 2 + AG-UI SSE):**

```bash
make backend
# → http://localhost:8000 (the AG-UI SSE endpoint)
```

**Terminal 2 — web SPA (React Router 7 + Vite + CopilotKit v2 + A2UI):**

```bash
cd web && bun install && bun run dev
# → http://localhost:3000
```

**Terminal 3 — Gradio studios:**

```bash
make ncce-visualise
# → http://localhost:7860 (4-tab an_learning_graph: Render / Equivalencies / Generate / Pedagogy)
```

## Step 2 — Open the SPA home

Go to **http://localhost:3000**.

Click **Demo** in the header — opens `/compare-models`. You see a side-by-side
comparison of **Gemma-4-26B-A4B-vision** vs **Gemini-3.5-Flash-vision** on the
87 English Leaving Cert PDFs (the in-scope corpus). Per-subject OCR accuracy
+ latency + token cost over Mathematics, English, Gaeilge, Chemistry, Geography,
Computer Science.

**What this proves**: the Gemma-vs-Gemini vision comparison is a first-class
deliverable, not a footnote. The substrate exercises both models end-to-end
against real Leaving Cert PDFs.

## Step 3 — Browse the NCCE showcase

Click **Learning Graphs** in the header (or visit `/learning-graphs` directly).

You see:
- The 4-tab NCCE Gradio studio (iframe to HF Space)
- **Equivalencies** panel — cell-level cross-walk from a single NCCE source
  cell to its equivalents across the BI substrate
- **Pedagogy overlay** panel — the 12 NCCE pedagogy principles applied to
  every cell of the Y8 Python learning graph
- 3 marimo iframes:
  - **notebook 10** — NCCE learning graph end-to-end (DLT → CocoIndex → BAML → SQLite → Plotly)
  - **notebook 17** — LC syllabus browser over the 87 in-scope PDFs
  - **notebook 19** — NCCA policy citation explorer (the 5 policy PDFs)

**What this proves**: Docling preserves the NCCE row × column grid through
PDF → Markdown → BAML → SQLite → Plotly without losing the learning-graph
structure. The BAML `learning_graph.baml` (8 classes + 9 functions) drives the
extraction; the pedagogy overlay applies 12 NCCE principles per cell.

## Step 4 — Generate a certificate via the ADK chat

Click **Agent** in the header (or visit `/agents`).

Type: **"Generate a certificate for an LC Maths student named Maya who mastered Differentiation"**

The ADK agent fires the `generate_asset` tool which:
1. Calls `ExtractMathsSyllabus` (BAML) on a sample Maths PDF
2. Runs `CertificatePipeline.run(...)` to compose a PNG certificate
3. Emits an AG-UI `Raw` event carrying an A2UI `NccaPdfCard` + `CitationPill` surface

The `<A2UIRenderer>` in the chat page picks up the A2UI JSONL and renders the
card inline. The certificate PNG is downloadable from `/tmp/certificates/`.

**What this proves**: the end-to-end asset chain
**BAML → DiffusionGemma → certificate → A2UI surface in chat** is fully wired.

## Step 5 — Drive the Gradio studio end-to-end

In Terminal 3 (the Gradio terminal from Step 1), open the **Editorial Studio** tab
(or visit http://localhost:7861 if you've started `editorial_studio.app`).

Click **Extract Scoil Sinsearach certificate**. Pick a learner, name, and
subject (mathematics / english / chemistry / geography). Click **Extract**.

The `_on_extract_certificate` handler runs the full 7-stage `CertificatePipeline`
and returns a Markdown summary + the full `CertificateRecord` JSON (with PNG bytes
+ PDF bytes + provenance citations to the 5 NCCA policy PDFs).

**What this proves**: the per-stage `CertificatePipeline` orchestration works
for all 5 British Isles education stages (Aistear → Bunscoil → MeanScoil →
Scoil Sinsearach → Ollscoil), with the 14-subject `SUBJECT_WIRING_REGISTRY`
driving the per-subject BAML extractor selection.

## Bonus — the Gemma vision harness

```bash
marimo edit notebooks/21_vision_comparison_inscope.py
```

Opens a marimo canvas that side-bybars Gemma-4-26B-vision vs Gemini-3.5-Flash-vision
on the 6 BIEP priority subjects (Mathematics / English / Gaeilge / Chemistry /
Geography / Computer Science). Per-subject accuracy + a heatmap.

## Bonus — the full pipeline walkthrough

```bash
marimo edit notebooks/20_full_pipeline_run.py
```

Opens a marimo canvas that lists every in-scope PDF, its processing latency,
and its BAML extraction status. Uses `scripts/process_inscope_pdfs.py` as the
underlying CLI.

## What the evaluator should look for

1. **All 4 surfaces boot** — web SPA, backend, Gradio, marimo (all wired to the
   same DuckDB substrate)
2. **A2UI surfaces render in chat** — `NccaPdfCard`, `CitationPill`, `NCCEHeatmap`
   visible after the chat fires the `generate_asset` tool
3. **Gemma vs Gemini is real, not a footnote** — the `/compare-models` page + notebook 21
4. **The full BIEP substrate is preserved** — DLT, CocoIndex, BAML, ADK, Gradio,
   Web SPA all wired; only the corpus scope narrowed (8 jurisdictions deferred
   to a `_deferred_*` location + table per `docs/SUBMISSION_SCOPE.md`)

## Cleanup

```bash
make down                                           # tear down the Docker Compose stack
```

Per `AGENTS.md`, no commits / pushes / deploys were made during this session.
The 30 openspec changes + 8 archived changes + the new submission-scope change
remain in the `openspec/changes/` tree for the user to commit + deploy when ready.