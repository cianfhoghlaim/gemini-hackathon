# View & Test — gemini_hackathon BIEP v3

> Copy-paste commands to inspect, run, and visually verify every layer
> of the platform built in the 2026-08-31 session.

All commands assume `cwd = /Users/cianmacandeisigh/dev/gemini_hackathon`.

---

## 0. Pre-flight (one-time, ~30 s)

```bash
cd /Users/cianmacandeisigh/dev/gemini_hackathon

# Confirm deps installed
uv sync --all-extras

# Regenerate the BAML client + run BAML tests (offline-safe with BAML_TEST_MODE=true)
make baml

# Confirm DuckDB has the 185 rows
uv run python -c "import duckdb; print(duckdb.connect('gemini_hackathon.duckdb', read_only=True).execute('SELECT jurisdiction, COUNT(*) FROM raw.official_documents GROUP BY 1 ORDER BY 2 DESC').fetchall())"
# Expected: [('Ireland', 139), ('United Kingdom (NCCE)', 11), ('Scotland', 9), ('England', 8), ...]
```

---

## 1. Inspect the lifted PDFs (no UI)

```bash
# The 139 LC PDFs across 14 subjects
find data/ireland/leaving_certificate -name "*.pdf" | wc -l

# The 4 NCCE learning graphs + pedagogy
ls -la data/bi_ep/syllabi_raw/uk_ncce/curriculum/

# The 5 NCCA policy PDFs (the certificate source of truth)
cat data/ireland/ncca_policy/INDEX.yaml | head -30

# The lift manifest (sha256-verified provenance)
cat data/ireland/leaving_certificate/lift_manifest.json | uv run python -c "import json,sys; d=json.load(sys.stdin); print('Discovered:', d['stats']['discovered'], '| Lifted:', d['stats']['lifted'], '| Verified:', d['stats']['verified'])"
```

## 2. Inspect the DuckDB substrate

```bash
# All 185 rows grouped by jurisdiction
uv run python <<'PY'
import duckdb
con = duckdb.connect("gemini_hackathon.duckdb", read_only=True)
print("By jurisdiction:")
for r in con.execute("SELECT jurisdiction, COUNT(*) FROM raw.official_documents GROUP BY 1 ORDER BY 2 DESC").fetchall():
    print(f"  {r[0]:30s}  {r[1]}")
print("\nBy source_kind:")
for r in con.execute("SELECT source_kind, COUNT(*) FROM raw.official_documents GROUP BY 1 ORDER BY 2 DESC").fetchall():
    print(f"  {r[0]:30s}  {r[1]}")
print("\nSample Irish LC PDF row:")
print(con.execute("SELECT source_key, subject, language, page_count, file_size_bytes, source_kind FROM raw.official_documents WHERE jurisdiction='Ireland' AND language='en' LIMIT 1").fetchdf().to_string())
PY
```

## 3. Inspect the BAML extraction cache

```bash
# List the tables in the canonical SQLite mirror
uv run python <<'PY'
import sqlite3
con = sqlite3.connect("data/bi_ep/extracted_syllabi.sqlite")
for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
    n = con.execute(f"SELECT COUNT(*) FROM {row[0]}").fetchone()[0]
    print(f"  {row[0]:30s}  {n} rows")
con.close()
PY
```

Expected: `extracted_syllabi` (BAML extractions), `uk_ncce_learning_graphs` (11), `annotated_learning_graphs` (pedagogy overlay).

## 4. Browse the marimo notebooks (reactive UI)

The 17 marimo notebooks each open in your browser:

```bash
# Headline showcase — NCCE learning graph end-to-end
marimo edit notebooks/10_ncce_learning_graph_walkthrough.py

# LC syllabus browser (over the 139 lifted PDFs)
marimo edit notebooks/17_lc_syllabus_extract_browser.py

# Gaeilge / English bilingual view
marimo edit notebooks/18_gaeilge_bilingual_view.py

# NCCA policy citation explorer (the 5 policy PDFs)
marimo edit notebooks/19_ncca_policy_citation_explorer.py
```

**Browser-friendly WASM** (no install required) — already linked from `/learning-graphs`:
- https://marimo.app/github.com/cianfhoghlaim/gemini-hackathon/blob/main/notebooks/17_lc_syllabus_extract_browser.py/wasm
- https://marimo.app/github.com/cianfhoghlaim/gemini-hackathon/blob/main/notebooks/18_gaeilge_bilingual_view.py/wasm
- https://marimo.app/github.com/cianfhoghlaim/gemini-hackathon/blob/main/notebooks/19_ncca_policy_citation_explorer.py/wasm

## 5. View the 7 Gradio studios

```bash
# Pick any one — each launches on :7860 and opens in browser
make ncce-visualise                   # the 4-tab NCCE showcase
uv run python -m gemini_hackathon_gradio.editorial_studio     # the big editorial studio
uv run python -m gemini_hackathon_gradio.anam_education        # the 7-feature integration
uv run python -m gemini_hackathon_gradio.oideachais_mission_control   # 5 operator tabs
uv run python -m gemini_hackathon_gradio.oideachais_pdf_review        # human review of BAML output
uv run python -m gemini_hackathon_gradio.an_scrudu            # past-paper heatmap
uv run python -m gemini_hackathon_gradio.journey_studio       # 6-level orchestrator
```

Then open http://localhost:7860 in your browser.

## 6. Boot the FastAPI ADK backend (the AG-UI SSE endpoint)

```bash
make backend                          # → http://localhost:8000
```

The backend serves the AG-UI SSE stream at `POST /` (used by the web SPA's CopilotKit client). Smoke test:
```bash
curl -sN http://localhost:8000/ -H 'Content-Type: application/json' -d '{"messages":[{"role":"user","content":"hi"}]}' | head -20
```

## 7. Boot the React SPA (web/)

In a second terminal:
```bash
cd web && bun install && bun run dev    # → http://localhost:3000
```

The SPA mounts the `<CopilotKit>` provider that streams from `VITE_ADK_RUNTIME_URL` (default `http://localhost:8000`) and renders A2UI panels via `<A2UIRenderer>` in the chat routes.

**Pages to visit** (each is a one clickable link from the header):
- `/` — subnation home
- `/subjects` — 8 subject cards → `/subjects/:slug` (marimo iframe per subject)
- `/agents` — NCCA panel chat (3 tools + A2UI surfaces)
- `/find-resources` — cross-national resource discovery (A2UI surfaces)
- `/learning-graphs` — NCCE showcase (4-tab studio + Equivalencies + Pedagogy + the 3 marimo links)
- `/archipelago` — 8 subnations side-by-side
- `/compare` — leaderboard + document explorer (Firestore)
- `/equivalency` — Mathematics equivalency matrix
- `/drill-down` — subnation → stage → subject hierarchical drill-down
- `/safeguarding` — 5 subnations safeguarding policy summaries

## 8. Run the full Docker Compose stack (one-shot dev)

```bash
make dev                              # → backend + lakehouse + Langfuse + MLflow
```

Brings up the 8-service compose (`compose.yaml`): `gemini-hackathon`, `llama-swap`, `duckdb`, `langfuse-postgres`, `langfuse-clickhouse`, `langfuse-redis`, `langfuse-web`, `langfuse-worker`, `mlflow`.

```bash
make down                             # nuclear teardown (wipes the duckdb volume)
```

## 9. Run the DLT pipelines (idempotent — safe to re-run)

```bash
make dlt-smoke-all                    # all 5 DLT pipelines
uv run python -m dlt_pipelines.uk_ncce_learning_graphs     # 11 NCCE rows
uv run python -m dlt_pipelines.ireland.leaving_cert       # 139 LC PDFs
```

## 10. Run the CocoIndex Apps (offline-safe with `EMBED_BACKEND=sentence_transformers`)

```bash
EMBED_BACKEND=sentence_transformers uv run python -m cocoindex_flows.pdf.pdf_to_markdown_app
EMBED_BACKEND=sentence_transformers uv run python -m cocoindex_flows.uk_ncce.learning_graphs_app
```

## 11. Quality gates

```bash
make verify          # the 8-tick verify gate (calls scripts/verify.sh)
make lint           # ruff check + format
make typecheck      # mypy gemini_hackathon/ (needs baml-cli generate first)
make test           # pytest tests/ -v
```

Baseline expectations per `docs/KNOWN_ISSUES.md`: ~358 tests pass, 7 known failures (FIBO + Babylon + DLT + OCR llama-swap), 4 skipped.

---

## Deploy (when ready)

```bash
make cloudbuild                       # gcloud builds submit → Cloud Run gemini-hackathon-adk
cd web && firebase deploy --only hosting        # the React SPA
make hf-publish                       # regenerate + push the 6 HF Spaces
make docs                             # export marimo notebooks → site/ → gh-pages
```

---

## Env summary

The 30+ env vars live in `.env` (gitignored) and `.env.example` (committed). The critical toggles for offline dev:

```bash
MODEL_PROFILE=hackathon               # ONLY public profile
GEMINI_BACKEND=vertex                 # or `aistudio` if no ADC
EMBED_BACKEND=sentence_transformers   # offline-safe (bge-m3 local)
VECTOR_BACKEND=firestore              # or `vertex` for Vertex AI Vector Search
ADK_LOCAL_SECRETS=1                   # read from .env (no GSM)
ADK_LOAD_SECRETS=0                    # don't try Google Secret Manager in dev
BAML_TEST_MODE=true                   # deterministic BAML fixtures
VITE_ADK_RUNTIME_URL=http://localhost:8000
```

See `.env.example` for the full list with comments.