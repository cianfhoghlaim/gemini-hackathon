# Submission scope — 2026-08-31

> **This submission's demo runs on a focused corpus — the 97 PDFs we already have on disk.**
> The full British Isles education system stays in scope for the wider project;
> what changes for this submission is the **demo path**.

## In scope (97 PDFs)

| Source | Count | Path |
|---|---|---|
| NCCA policy PDFs | 5 | `data/ireland/ncca_policy/` |
| NCCE artefacts | 5 | `data/bi_ep/syllabi_raw/uk_ncce/curriculum/` (4 PDFs + 1 placeholder) |
| English LC PDFs | 87 | `data/ireland/leaving_certificate/*/en/*.pdf` |
| Sample LC Maths | 1 | `data/syllabi/sample_lc_maths_2024.pdf` |

## Deferred (kept on disk + in code, not in demo path)

| Source | Count | Path |
|---|---|---|
| Gaeilge LC PDFs | 52 | `data/ireland/leaving_certificate/_deferred_ga/` |
| Non-LC + NCCA + NCCE DuckDB rows | 35 | `raw.official_documents_deferred` |
| DLT scrapers for 8 other subnations | — | `dlt_pipelines/_base/jurisdiction_pipeline_base.py` + `_subject_base.py` |

## Why (the hackathon argument)

For an agentic AI hackathon, running 8-subnation scrapers would burn hours of compute
for marginal demo value. The BIEP substrate (DLT + CocoIndex + BAML + Google ADK + Gemma 4 +
Gemini 3.5 + A2UI + Gradio + Web SPA) is already wired and demonstrated against the
97 in-scope PDFs. The full multi-subnation orchestration is preserved in code; what
changes is which corpus is exercised end-to-end at the demo surface.

## What's IN the demo flow (5 steps)

1. `/compare-models` — Gemma-4 vs Gemini-3.5 vision comparison (87 LC en PDFs)
2. `/learning-graphs` — NCCE showcase (5 artefacts) + 3 marimo iframes (10/17/19)
3. `/agents` — ADK chat with A2UI surfaces (cert generation, citation pills)
4. `make ncce-visualise` — 4-tab Gradio an_learning_graph studio on :7860
5. `editorial_studio` Gradio — 5-stage CertificatePipeline per stage tab on :7861

## The in-scope SQL view (canonical)

```sql
CREATE OR REPLACE VIEW raw.official_documents_in_scope AS
SELECT * FROM raw.official_documents
WHERE jurisdiction = 'United Kingdom (NCCE)'
   OR (jurisdiction = 'Ireland' AND UPPER(language) IN ('EN', 'E', 'ENGLISH', ''));
```

## Models (per docs/MODEL_POLICY.md)

- **Layout (PDF→MD)**: Docling (preserves NCCE row × column grids)
- **OCR fallback**: `gemma-4-26b-a4b-vision` via llama-swap
- **BAML extraction**: `gemini-3.5-flash` via Vertex AI (`BIEPV3Extract` client)
- **Embedding**: `BAAI/bge-m3` local (1024-d, multilingual)
- **Vector**: LanceDB local; swap to Firestore when `VECTOR_BACKEND=firestore`
- **Asset generation**: `diffusiongemma-26b-a4b` (per registry; Tier 2 = `fibo`)

## Demo evidence pointers

- Demo script: [`docs/DEMO_SCRIPT.md`](DEMO_SCRIPT.md)
- View + test recipe: [`docs/VIEW_AND_TEST.md`](VIEW_AND_TEST.md)
- In-scope DuckDB view DDL: see `notebooks/04_corpus_inventory.py`
- BAML extraction: `baml_extracts/learning_graph.baml` (8 classes + 9 functions)

## What this scope realignment DOES NOT change

- The full BIEP architecture stays intact (see [`ARCHITECTURE.md`](../ARCHITECTURE.md))
- The `_deferred_ga/` PDFs remain on disk for the post-hackathon expansion pack
- The 8-jurisdiction DLT scrapers remain in `dlt_pipelines/_base/` for re-enable
- The openspec changes for deferred jurisdictions (`defer-ni-wales-scotland-iom-v1`,
  `deferred-jersey-guernsey-v1`, `defer-tuatha-consolidation-v1`) remain deferred