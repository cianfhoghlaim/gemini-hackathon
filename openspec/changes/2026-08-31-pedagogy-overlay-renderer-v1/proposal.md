# 2026-08-31-pedagogy-overlay-renderer-v1

> **The 3rd change of the 2026-08-31 batch.** Dynamically extracts the
> 12 NCCE pedagogy principles from `pedagogy_principles.pdf` via BAML,
> caches them to disk + Cognee, and renders an **annotated learning
> graph** where each cell is coloured by which pedagogy principle(s) it
> uses (PRIMM, pair programming, semantic waves, etc.).

## Why

The `pedagogy_principles.pdf` is the cross-cutting teaching guidance
that **applies across all subjects**: every learning graph cell can be
tagged with one or more of the 12 principles. Without an overlay, the
BIEP has the structured learning graphs (rows × columns + prerequisites)
but no signal about **how** each cell should be taught.

The principles may also change over time as NCCE revises them — so we
**dynamically extract** them from the PDF (per your decision #6) rather
than hard-coding the 12 names. To avoid paying the extraction cost on
every render, we **cache** them to:
1. **Disk** (`data/bi_ep/syllabi_md/uk_ncce/pedagogy_principles.json`) — keyed on `sha256(pedagogy_principles.pdf)`
2. **Cognee** dataset `gh_cognee_pedagogy_dataset` — semantic search fallback when the disk cache is cold

The cache invalidates when the source PDF's sha256 changes (CI gate
fails the build if the new PDF is uploaded without bumping the cache
version).

## What changes

### Phase 0 — OpenSpec change folder (this commit)
- [x] T0.1: `openspec/changes/2026-08-31-pedagogy-overlay-renderer-v1/proposal.md` written
- [x] T0.2: `openspec/changes/.../specs/pedagogy-overlay/spec.md`
- [x] T0.3: `openspec/changes/.../tasks.md`
- [x] T0.4: `openspec validate 2026-08-31-pedagogy-overlay-renderer-v1 --strict` passes

### Phase 1 — BAML extraction contract

- **Extend `baml_extracts/learning_graph.baml`** with `ApplyPedagogyPrinciples` function:
  - Input: `LearningGraph`, `PedagogyPrinciple[]`
  - Output: `AnnotatedLearningGraph` where every `LearningGraphCell` gains `pedagogy_principle_ids: string[]`
- **New `AnnotatedLearningGraph` class** in the same file:
  - `(graph: LearningGraph, cell_annotations: map<cell_id, string[]>, pedagogy_source: "cache" | "cognee" | "live_pdf", generated_at)`

### Phase 2 — CocoIndex disk cache + Cognee dataset

- **New `cocoindex_flows/uk_ncce/pedagogy_cache.py`** — `@coco.fn(memo=True)` App that:
  - Reads `pedagogy_principles.pdf` from `data/bi_ep/syllabi_raw/uk_ncce/curriculum/`
  - Calls `ExtractPedagogyPrinciples` BAML function
  - Writes the result to `data/bi_ep/syllabi_md/uk_ncce/pedagogy_principles.json` (keyed on sha256)
  - Uploads to Cognee dataset `gh_cognee_pedagogy_dataset`
- The disk cache is the primary; Cognee is the semantic-search fallback

### Phase 3 — Dagster asset

- **New `orchestration/defs/3_model_lifecycle/pedagogy_overlay.py`** — Dagster asset per (jurisdiction × subject) that materialises the `AnnotatedLearningGraph`:
  - Depends on `uk_ncce_learning_graphs` (Change A) + the pedagogy cache (Phase 2)
  - Writes to Firestore `annotatedLearningGraphs/{graph_id}`

### Phase 4 — Activate the Pedagogy overlay tab in the Gradio studio

- **Extend `gemini_hackathon_gradio/an_learning_graph/pedagogy_tab.py`** — replace the stub from Change A with the real implementation:
  - Pick a learning graph → render the SVG with cells coloured by which pedagogy principle they use
  - Hover over a cell → show the principle name + summary + how_to_apply
  - Filter by principle (e.g. "show only cells using PRIMM")

### Phase 5 — Notebook walkthrough

- **New `notebooks/13_pedagogy_overlay_walkthrough.ipynb`** — marimo walkthrough of:
  - Loading the NCCE Y8 Python learning graph
  - Extracting the 12 pedagogy principles (with disk cache hit demo)
  - Applying the overlay → rendering the coloured SVG
  - Filtering by principle (e.g. show only "Lead with concepts" cells)

## Acceptance

- `baml_extracts/learning_graph.baml` defines `AnnotatedLearningGraph` + `ApplyPedagogyPrinciples`
- `baml-cli generate && baml-cli test baml_extracts/learning_graph.baml` passes for `ApplyPedagogyPrinciples`
- `python -m cocoindex_flows.uk_ncce.pedagogy_cache` writes 12 principles to disk + uploads to Cognee
- Re-running `pedagogy_cache` is a no-op (sha256 cache hit)
- Changing `pedagogy_principles.pdf` triggers a re-extraction
- `mise run dagster:list-assets | grep pedagogy_overlay` shows 6 assets (1 per priority subject)
- The Pedagogy overlay tab in the Gradio studio renders the coloured SVG
- `notebooks/13_*.ipynb` runs without error
- `openspec validate 2026-08-31-pedagogy-overlay-renderer-v1 --strict` passes
- `mise run lint && mise run py:typecheck && mise run turbo typecheck` green

## Dependencies

- **Blocked by:** `2026-08-31-uk-ncce-learning-graph-showcase-v1` (the structured learning graphs + the pedagogy cache pattern must exist).
- **Unblocks:** nothing (this is the final overlay layer).
- **Cross-repo:** the upstream cianfhoghlaim Cognee skill (`.agents/skills/cognee/SKILL.md`) is unchanged.

## Compatibility

- **No code changes required** for callers — `ApplyPedagogyPrinciples` is additive.
- The disk cache is versioned by sha256; old caches remain valid until the PDF changes.
- The new Firestore collection (`annotatedLearningGraphs`) is created with read-public / write-admin rules.
- The new Dagster asset slots into the existing 5-layer `orchestration/defs/` tree.