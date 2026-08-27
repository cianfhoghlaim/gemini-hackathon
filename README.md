# gemini_hackathon — The British Isles Education Platform

> **Google All Things Agentic 2026 Hackathon submission.** Built with
> **Gemini 3.5** (Vertex AI) + **Gemma 4 26B-A4B** (Unsloth Studio) + the
> **Google ADK 2** agent framework. Deployed on **Google Cloud Run**
> with the editorial canvas on **Hugging Face Spaces**.
> The British Isles education system: **Aistear → Bunscoil → MeanScoil
> → Scoil Sinsearach → Ollscoil** across **6 subnations** (Ireland +
> England for the hackathon; NI / Wales / Scotland / IoM as Phase 2).

[![MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)
[![Gradio 5.28+](https://img.shields.io/badge/gradio-5.28%2B-orange)](requirements.txt)
[![CI](https://img.shields.io/badge/CI-GitHub_Actions-blue)](.github/workflows/ci.yml)

---

## The August 2026 refactor

The codebase was restructured per the implementation plan (17 workstreams):

| W | What |
|---|---|
| W0 | minimal unblock (re-pin mise, ignore .agents/, document dupe web/components, add KNOWN_ISSUES.md) |
| W1 | dependency pin: `google-adk 2.7.1+`, `gradio 5.28+`, `huggingface_hub 0.30+`, `lancedb`, `falkordb`, `graphiti-core`, `cognee`, `fastmcp` |
| W2 | **5 NCCA policy PDFs** as committed data — the certificate source of truth |
| W3 | `gemini_hackathon_gradio/` — the 5 editorial studios + shared library |
| W4 | lift `sruth/tuath` non-mythology + `/dev/tuatha` subject wiring + deferred-tuatha openspec change |
| W5 | Ireland K-12 BAML + DLT + CocoIndex (Primary + Secondary) |
| W6 | leabharlann general sources + UoG archives (manifests only — PDFs fetched via `./data/leabharlann/fetch_full_corpus.sh`) |
| W7 | **5 ADK 2 stage coordinators** + 5 reusable workflow pillars (the 3 pillars from `adk2-tutorial` + monstertix + loop-lab-table) |
| W8 | memory layer (`MarkdownMemoryService`) + `knowledge_graph/hybrid_search.py` |
| W9 | skill-progression ledger (Convex + LanceDB + FalkorDB) |
| W10 | FIBO image generation — **14 NCCA subjects × 5 stages** prompt bank |
| W11 | 6 subnations (Ireland + England active; NI/Wales/Scotland/IoM Phase 2) |
| W12 | the big Gradio editorial studio on Cloud Run (monolithic + `gr.Workflow` canvas) |
| W13 | 5 HF Spaces at `cianfhoghlaim/gemini_hackathon_<stage>` |
| W14 | **the LC/JC certificate pipeline** — the SHOWCASE (see below) |

The Celtic 5-element palette (Talamh / Uisce / Tine / Aer / Anam) was
REPLACED with the 5-stage British Isles education palette (Aistear /
Bunscoil / MeanScoil / Scoil Sinsearach / Ollscoil). The Hades
Shadow-First dark theme is preserved.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full picture, or
[docs/TUATHA_CONSOLIDATION_MAP.md](docs/TUATHA_CONSOLIDATION_MAP.md)
for what was absorbed from `sruth/tuath` and `/dev/tuatha`.

---

## The LC/JC certificate pipeline (the SHOWCASE — W14)

Every claim on every generated certificate cites a page from one of
the 5 NCCA policy PDFs:

```
SC-L1-L2-Programme-Statement.pdf,
key-competencies-in-senior-cycle_en.pdf,
the-potential-of-online-learning-environments_en.pdf,
the-potential-of-technology-to-support-online-certification-and-reporting.pdf,
scr-advisory-report_en.pdf
```

The pipeline (7 stages): extract_criteria → decompose_outcomes →
extract_paper+marking → search_official → generate_background →
compose_certificate → save_to_provenance.

Output: PNG (~80 KB) + PDF (~700 B) with the awarding-body palette
background + competency strip + provenance footer + UNOFFICIAL banner.

## Quick start (offline, no GCP keys required)

```bash
# 1. Verify the Python package offline
uv run python scripts/smoke_test.py
# → 11/11 steps green

# 2. Generate BAML clients + run BAML tests
uv run baml-cli generate
uv run baml-cli test

# 3. Boot the Python backend on a free port, hit /api/health, kill it
uv run python scripts/backend_smoke.py
# → /api/health + /api/themes + /api/models + /api/agents/find-resources all green

# 4. Run the Gemini-vs-Gemma4 comparison harness (writes to DuckDB)
uv run python scripts/compare_demo.py
