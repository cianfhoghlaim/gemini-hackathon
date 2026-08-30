# Local dev — step-by-step guide

> The 5-step recipe to take a fresh clone → a running gemini_hackathon
> backend with the full lakehouse + 6 jurisdiction learning graphs +
> the NCCE showcase.

This document follows the canonical Google project-management pattern
(see `docs/GOOGLE_PROJECT_MANAGEMENT.md`) — every command is a direct
invocation or a `make <target>` from the self-documenting `Makefile`
(`make help` lists all 27 targets). There is **no `mise.toml`**, no
`task` file, no `justfile`.

```
$ make help

gemini-hackathon — make targets

  help              show this help message (the default target)
  install           uv sync --all-extras (deps + dev + docs + lint groups)
  baml              regenerate the BAML client + run BAML tests
  setup             full bootstrap — uv install + sync + .env + baml + verify
  lint              ruff check + ruff format --check
  format            ruff format (in-place)
  typecheck         mypy gemini_hackathon/ (strict, dignified-python-312)
  test              pytest tests/ -v
  test-cov          pytest + coverage report
  verify            the 8-tick verify gate (calls scripts/verify.sh)
  run               uv run python -m gemini_hackathon.cli (the canonical CLI entry)
  backend           boot the Python backend on :8000 (FastAPI + ADK 2)
  web               boot the TanStack Start web surface on :3000
  notebook          launch marimo edit notebooks/ (reactive UI)
  docs              export marimo notebooks to site/ (for gh-pages deploy)
  shell             drop into a uv-managed Python REPL (project on PYTHONPATH)
  dlt-smoke-all     run every DLT pipeline (offline-safe; writes to DuckDB)
  cocoindex-update  run every CocoIndex App (offline-safe; writes to local FS)
  ncce-extract      run the NCCE DLT + CocoIndex pipeline (the 2026-08-31 batch)
  ncce-visualise    launch the 4-tab Gradio studio (Render / Equivalencies / Generate / Pedagogy)
  compare-demo      run the Gemini-vs-Gemma4 comparison harness (writes to DuckDB)
  docker-build      docker build -t gemini-hackathon:dev .
  dev               docker compose up --build (the local stack: backend + lakehouse + observability)
  down              docker compose down -v (nuclear: wipes the duckdb volume)
  cloudbuild        gcloud builds submit --config=cloudbuild.yaml (the prod deploy)
  hf-publish        regenerate + push the 6 HF Spaces mirrors
  clean             remove build artefacts + caches
  clean-data        nuke the DuckDB file (DESTRUCTIVE)
```

---

## Step 1 — Install + configure (5 min)

### Clone + uv sync
```bash
git clone https://github.com/cianfhoghlaim/gemini_hackathon && cd gemini_hackathon
make install            # = uv sync --all-extras
```

The first time you run `make install`, `uv` resolves ~250 packages
(deps + dev + docs + lint groups) into `.venv/`. Subsequent runs are
~1 second (uv caches the lock file).

### Copy the env template
```bash
make setup              # = ./scripts/dev.sh — does steps 1-5 in one shot
cp .env.example .env   # OR run manually
```

The canonical env vars (see `.env.example` for the full list):

| Var | Default | Purpose |
|---|---|---|
| `MODEL_PROFILE` | `hackathon` | Gates the model registry (the only profile docs/UI reference) |
| `GEMINI_BACKEND` | `vertex` | `vertex` (ADC) or `aistudio` (API key) |
| `GEMINI_MODEL` | `gemini-3.5-flash` | The canonical Tier 1 model |
| `GOOGLE_CLOUD_PROJECT` | (empty) | Your GCP project id (required for `GEMINI_BACKEND=vertex`) |
| `GOOGLE_CLOUD_LOCATION` | `us-central1` | The Vertex AI region |
| `GEMINI_API_KEY` | (empty) | Only required when `GEMINI_BACKEND=aistudio` |
| `UNSLOTH_API_KEY` | (empty) | Tier 2 fallback (Unsloth Studio) |
| `UNSLOTH_BASE_URL` | (empty) | Tier 2 endpoint |

For local-only dev (no GCP creds): every key has a sensible default.
The 3 PDF→Markdown + BAML extraction tasks use `localfs` +
sentence-transformers + SQLite by default — no network egress required.

### Verify the install
```bash
make verify             # the 8-tick verify gate (see scripts/verify.sh)
```

Expected output:
```
  1. Imports           ✓ 16 modules imported OK
  2. BAML              ✓ baml-cli generate
                       ⊘ baml-cli test (skipped — requires network)
  3. Lint              ✓ ruff check .
                       ✓ ruff format --check .
  4. Typecheck         ✓ mypy gemini_hackathon/
  5. DLT smoke         ✓ 6 dlt modules imported
  6. CocoIndex smoke   ✓ 9 cocoindex modules imported
  7. Gradio imports    ✓ 6 gradio modules imported
  8. Dagster imports   ✓ 9 dagster modules imported

✓ 8/8 verify ticks green
```

---

## Step 2 — Bring up the lakehouse + observability stack (10 min)

The local dev stack is the 6-service compose (per
`docker-compose.yml` + `docker-compose.local.yaml`, consolidated per
commit `a92d8c8` of the GCP-first IaC refactor):

```bash
make dev                # = docker compose up --build
```

What comes up:

| Service | Port | Purpose | Where to find data |
|---|---|---|---|
| `gemini-hackathon-backend` | 8080 | The ADK 2 backend (FastAPI + AG-UI SSE) | `data/bi_ep/extracted_syllabi.sqlite` |
| `gemini-hackathon-frontend` | 3000 | The Firebase-native TanStack Start web | `web/src/routes/*` |
| `langfuse` | 3001 | LLM observability | `http://localhost:3001/api/public/health` |
| `mlflow` | 5050 | ML experiment tracking | `http://localhost:5050/health` |
| `pgvector/pgvector:pg17` | 5432 | Postgres + pgvector (for CocoIndex pgvector backends) | `postgres://cocoindex:cocoindex@localhost/cocoindex` |
| `lake-keeper-rust` | 8181 | Iceberg REST catalog (Lance namespace backend) | `http://localhost:8181/management/v1/config` |
| `lance-namespace` | 9100 | Lance namespace (the dual-backend vector target) | `http://localhost:9100/v1/namespace` |

**Verify every service** is up:
```bash
curl http://localhost:8080/health
curl http://localhost:3001/api/public/health
curl http://localhost:5050/health
psql "postgres://cocoindex:cocoindex@localhost/cocoindex" -c "SELECT 1;"
curl http://localhost:8181/management/v1/config   # Iceberg REST root
curl http://localhost:9100/v1/namespace          # Lance namespace list
```

**Stop everything** (and wipe the DuckDB volume):
```bash
make down               # = docker compose down -v
```

**Re-up without wiping**:
```bash
docker compose up -d    # or just `make dev`
```

---

## Step 3 — Run the data plane (3 min)

The data plane is **5 DLT pipelines → 8 CocoIndex Apps → 6 BAML extractions**, in this order:

### 3.1 — DLT pipelines (fetch raw PDFs into DuckDB)

```bash
# Ireland: 6 LC subject PDFs (filesystem-based) + safeguarding
make ncce-extract       # = dlt_pipelines.uk_ncce_learning_graphs + cocoindex_flows.uk_ncce.learning_graphs_app
# OR run them individually:
uv run python -m dlt_pipelines.official_doc_fetcher   # → ~8 rows (Ireland NCCA + SEC + DES)
uv run python -m dlt_pipelines.safeguarding_fetcher   # → 5 rows (safeguarding bodies)
uv run python -m dlt_pipelines.uk_ncce_learning_graphs   # → 11 rows (5 PDF + 6 per-subject)
uv run python -m dlt_pipelines.pdf_downloader           # → 7 PDFs (downloads remote → local)
uv run python -m dlt_pipelines.corpus_downloader         # → 8-jurisdiction sample corpus

# The canonical aggregate target
make dlt-smoke-all      # runs every DLT pipeline above
```

**Total**: ~31 OFFICIAL_DOC_COLUMNS rows in `official_documents` DuckDB table
+ 13 PDF files in `data/bi_ep/syllabi_raw/`.

**Verify**:
```bash
duckdb gemini_hackathon.duckdb -c "
SELECT jurisdiction, count(*) FROM official_documents GROUP BY jurisdiction ORDER BY jurisdiction;
"
-- Expected: England=8, Ireland=5, Jersey=1, Guernsey=1, IoM=1, NI=1, Scotland=1, UK NCCE=11, Wales=1
-- Plus 5 safeguarding rows (gov.ie, gov.uk, education.gov.scot, ...)
```

### 3.2 — CocoIndex Apps (PDF → Markdown → embeddings)

```bash
# The canonical aggregate target
make cocoindex-update    # runs every CocoIndex App

# OR run them individually:
uv run python -m cocoindex_flows.pdf.pdf_to_markdown_app               # → 13 .md files
uv run python -m cocoindex_flows.uk_ncce.learning_graphs_app          # → 5 .md files (NCCE learning graphs)
uv run python -m cocoindex_flows.ireland.lc_subject_embedding         # → Ireland LC subjects
uv run python -m cocoindex_flows.ireland.junior_cycle_embedding       # → Ireland JC subjects
uv run python -m cocoindex_flows.education.lc6_extraction_app         # → W14 BAML extraction target
uv run python -m cocoindex_flows.equivalency.equivalency_graph_app     # → Phase 4a cross-jurisdiction graph
```

**Total**: 8+ CocoIndex Apps, each memoised on input PDF SHA256 (re-runs are O(1) cache hits).

**Verify**:
```bash
ls data/bi_ep/syllabi_md/uk_ncce/           # 5 .md files (one per NCCE artefact)
ls data/bi_ep/syllabi_md/ireland/           # .md files for Ireland LC subjects
duckdb gemini_hackathon.duckdb -c "SELECT count(*) FROM learning_graphs;"   # the 11 NCCE structured learning graphs
```

### 3.3 — BAML extractions (structured output)

```bash
# Generate the BAML client (always first)
make baml                                    # = baml-cli generate + baml-cli test

# Test the 9 NCCE BAML functions (the 2026-08-31 batch)
uv run baml-cli test baml_extracts/learning_graph.baml        # 10 tests, 1 per function

# Test the existing BAML functions
uv run baml-cli test baml_extracts/extract_equivalency.baml
uv run baml-cli test baml_extracts_education/celtic_curriculum.baml
```

**Where to find the BAML schemas**:

| What | Where |
|---|---|
| **Learning graph** (NCCE) | `baml_extracts/learning_graph.baml` — 9 classes (`LearningGraph`, `LearningGraphRow`, `LearningGraphColumn`, `LearningGraphCell`, `PrerequisiteEdge`, `PedagogyPrinciple`, `CurriculumJourney`, `SkillRibbon`, `AnnotatedLearningGraph`) + 10 functions |
| **Learning graph crossref** | `baml_extracts/learning_graph_crossref.baml` — `LearningGraphCrossReference` class |
| **Equivalencies** | `baml_extracts/extract_equivalency.baml` — `ExtractEquivalencies` (linear topics) + `ExtractCellEquivalencies` (cell-level) + `TopicMapping` + `CellEquivalent` |
| **Celtic curriculum** (legacy 5-stage palette) | `baml_extracts_education/celtic_curriculum.baml` — `LearningOutcome`, `CurriculumSpec`, `GrammarTopic`, `VocabularySet`, etc. |
| **Per-subject strands + Bloom** | `baml_extracts_education/subjects/{mathematics,chemistry,computer_science,biology,physics,english,gaeilge,geography}.baml` |
| **England qualifications** (AQA / OCR / Edexcel) | `baml_extracts_education/england/curriculum_syllabus.baml` + `subject_taxonomy.baml` |
| **British Isles subject registry** | `baml_extracts_education/_cross/biep_subject.baml` — 6 canonical enums (`Jurisdiction`, `EducationalStage`, `AwardingBody`, `Language`, `LCSubjectSlug`, `BIEPSubject`) |

---

## Step 4 — Run the Dagster assets (5 min)

The 5-layer `orchestration/defs/` tree:

```
orchestration/defs/
├── 1_ingestion/                 # DLT pipeline assets
├── 2_materials/                 # CocoIndex App assets
├── 3_model_lifecycle/           # NCCE learning graph assets (11) + equivalency (42) + pedagogy (6)
├── 4_asset_generation/          # FIBO image-gen assets
└── 5_agent_ops/                 # Fleet memory + observability assets
```

### Webserver (for browsing the asset graph)

```bash
make typecheck  # or `uv run dagster dev -m orchestration.defs`
# → opens at http://localhost:3000
```

### CLI: list every asset
```bash
uv run dg list assets --module orchestration.defs
```

### CLI: materialize the NCCE learning graph batch (the new 2026-08-31 work)
```bash
dg launch --assets uk_ncce_learning_graph_y8_python,uk_ncce_learning_graph_y7_scratch,uk_ncce_learning_graph_y6_variables,uk_ncce_pedagogy_principles,uk_ncce_curriculum_journey

dg launch --assets uk_ncce_cs_extracted_graph,uk_ncce_maths_extracted_graph,uk_ncce_english_extracted_graph,uk_ncce_gaeilge_extracted_graph,uk_ncce_chemistry_extracted_graph,uk_ncce_geography_extracted_graph
```

### CLI: the cross-walk + overlay (Change B + Change C)
```bash
dg launch --assets uk_ncce_cs_england_equivalencies,uk_ncce_cs_wales_equivalencies,...    # 42 cross-walks
dg launch --assets pedagogy_overlay_cs,pedagogy_overlay_maths,pedagogy_overlay_english,...   # 6 overlays
```

**Where to find the Dagster assets**:

| Asset group | Where |
|---|---|
| 11 NCCE learning graph assets | `orchestration/defs/3_model_lifecycle/uk_ncce_learning_graphs.py` |
| 42 cross-walk assets | `orchestration/defs/3_model_lifecycle/uk_ncce_learning_graph_equivalencies.py` |
| 1 aggregation asset (FalkorDB) | `orchestration/defs/3_model_lifecycle/learning_graph_equivalency_graph.py` |
| 6 pedagogy overlay assets | `orchestration/defs/3_model_lifecycle/pedagogy_overlay.py` |
| 1 pedagogy cache wrapper | `orchestration/defs/3_model_lifecycle/pedagogy_principles_cache.py` |
| 1 polling sensor | `orchestration/defs/3_model_lifecycle/sensors/uk_ncce_pdf_sensor.py` |

---

## Step 5 — Launch the Gradio studio + HF Space (2 min)

The 4-tab Gradio studio for the NCCE showcase:

```bash
make ncce-visualise       # = uv run python -m gemini_hackathon_gradio.an_learning_graph
# → opens at http://localhost:7860
```

The 4 tabs:

- **Render** — pick `(jurisdiction, subject, year_level)` → render the SVG (Plotly)
- **Equivalencies** — pick a cell → show the 7 equivalent cells in other jurisdictions (Plotly Sankey)
- **Generate from PDF** — upload a syllabus PDF → run the BAML extractor → preview the grid
- **Pedagogy overlay** — pick a learning graph → cells coloured by which pedagogy principle they use (Plotly heatmap)

### For the HF Space (production mirror)

```bash
make hf-publish            # regenerates hf_spaces/* + prints the upload commands
# OR manually:
cd hf_spaces/gemini_hackathon_learning_graphs
hf upload cianfhoghlaim/gemini_hackathon_learning_graphs . --repo-type space
```

---

## Where to find key data + schemas (the cheat sheet)

### Raw data
| What | Where |
|---|---|
| **Raw PDFs** (the source of truth) | `data/ireland/ncca_policy/*.pdf` (5 NCCA) + `data/bi_ep/syllabi_raw/uk_ncce/curriculum/*.pdf` (4 NCCE) + `data/bi_ep/syllabi_raw/{jurisdiction}/{subject}/{lang}/*.pdf` (the rest) |
| **NCCE INDEX** (sha256 + provenance) | `data/bi_ep/syllabi_raw/uk_ncce/curriculum/INDEX.yaml` |
| **NCCA INDEX** (sha256 + provenance) | `data/ireland/ncca_policy/INDEX.yaml` |
| **PDF metadata** (sha256 + page_count + size) | `duckdb gemini_hackathon.duckdb -c "SELECT * FROM official_documents;"` |
| **leabharlann corpus manifests** | `data/leabharlann/*.manifest.csv` |

### Processed data
| What | Where |
|---|---|
| **Markdown output** (CocoIndex-converted PDFs) | `data/bi_ep/syllabi_md/{jurisdiction}/...md` |
| **BAML extraction results** (per-jurisdiction, per-subject) | `data/bi_ep/extracted_syllabi.sqlite` (the `uk_ncce_learning_graphs`, `learning_graph_crossrefs`, `annotated_learning_graphs` tables) |
| **Learning graph JSON** (structured NCCE artefacts) | `data/bi_ep/learning_graphs/{slug}.json` |
| **Pedagogy principles cache** | `data/bi_ep/syllabi_md/uk_ncce/pedagogy_principles.json` (sha256-keyed) |
| **DuckDB destination file** | `gemini_hackathon.duckdb` (the canonical DLT destination) |

### Cloud-side state (when GCP creds set)
| What | Where |
|---|---|
| **Structured cell data** | Firestore `learningGraphs/{graph_id}` + `annotatedLearningGraphs/{graph_id}` collections |
| **Cross-jurisdiction equivalencies** | Firestore `prerequisiteEdges/{edge_id}` (the 42 cross-walks) + FalkorDB `:CellEquivalentEdge` |
| **Pedagogy principles** | Cognee dataset `gh_cognee_pedagogy_dataset` |

### Curated reference data
| What | Where |
|---|---|
| **Awarding-body palettes** (the 15 themes) | `themes/{ncca,aqa,ocr,pearson,sqa,wjec,ccea,iom,jersey,guernsey}_palette.json` |
| **Model registry** | `gemini_hackathon/model_registry.py` (5 NCCE entries under the new `learning_graph` family) |
| **Awarding-body source URLs** | `data/sources/index.json` (7 jurisdictions + 3 England boards + 5 safeguarding bodies) |
| **Cross-jurisdiction topic equivalencies** (curated) | `data/equivalencies/cross_jurisdiction.json` |
| **Maths-specific equivalencies** | `data/equivalencies/mathematics.json` |
| **Test data** | `data/sourced_derived/test/` |
| **Journey assets** (per-learner progression images) | `data/journey_assets/lvl5_*.png` |

---

## What to do when something breaks

### Common issues + fixes

| Symptom | Cause | Fix |
|---|---|---|
| `make baml` fails: `from datetime import UTC` is a Python 3.11+ feature | System Python is 3.9/3.10 | `uv python install 3.12 && uv sync --all-extras --python 3.12` |
| `make baml` fails: `pydantic` version conflict between `google-adk` and `gradio` | Pre-existing dep conflict (visible across the whole BIEP) | Pin via `uv add 'pydantic>=2.12,<2.13'` (resolves the `google-adk` requirement without breaking `gradio`) |
| `make dlt-smoke-all` errors: `ModuleNotFoundError: dlt` | `uv sync --all-extras` didn't run | `make install` |
| `make cocoindex-update` does nothing | `cocoindex` not installed | `uv add 'cocoindex[docling,sentence_transformers]'` |
| `make ncce-visualise` opens blank tabs | `data/bi_ep/extracted_syllabi.sqlite` is empty | `make ncce-extract` |
| `make dev` won't start | Docker not running | `open -a Docker` (macOS) or `systemctl start docker` (Linux) |
| Firestore collections empty | GCP creds not set | `gcloud auth application-default login && export GCP_PROJECT=<your-project>` |
| Pedagogy overlay empty | The cache file is empty | `uv run python -m cocoindex_flows.uk_ncce.pedagogy_cache` (re-extracts from the PDF) |
| `make typecheck` fails: `gradio` import cycle | The `gemini_hackathon_gradio/*` modules import gradio at module load | Skip gradio modules from mypy (use `[tool.mypy.overrides]` in `pyproject.toml`) |
| `make test` fails: `ModuleNotFoundError: baml_client` | `make baml` didn't run | `make baml` |
| `make cloudbuild` errors: `gcloud: command not found` | `gcloud` CLI not installed | `brew install --cask google-cloud-sdk` (macOS) or `apt-get install google-cloud-cli` (Linux) |

### Reset to a clean state

```bash
make clean                # nuke .venv + caches + build artefacts
make clean-data           # nuke the DuckDB file (DESTRUCTIVE — wipes extracted data)
make down                 # docker compose down -v (wipes the postgres volume)
make install && make baml # fresh install
```

### Get help

- `make help` — the canonical Google `help` target (the default)
- `make verify` — the 8-tick verify gate (every CI gate in one script)
- `docs/GOOGLE_PROJECT_MANAGEMENT.md` — why we use Make + uv + Docker Compose + Cloud Build + GitHub Actions
- `docs/DEPLOYMENT.md` — Cloud Run deploy walkthrough
- `docs/DEV_DEPLOY.md` — local-dev + dev-deploy playbook
- `docs/IAC.md` — the GCP-first infrastructure refactor (per Phase 5 GCP-first IaC)
- `openspec/changes/2026-08-31-replace-mise-with-make-v1/` — this change's proposal + tasks + spec delta