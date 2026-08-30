# Google project management — the gemini_hackathon stack

> **The 1-page rationale** for why we deleted `mise.toml` and adopted
> the canonical Google-flavoured project management stack: a self-
> documenting `Makefile` + `uv` + `docker compose` + `cloudbuild.yaml`
> + GitHub Actions. Mirrors every example in `docs/cocoindex_examples/*`
> + every project in `docs/adk-examples/*`.

## TL;DR

| Tool | What it does | Why we use it |
|---|---|---|
| **`pyproject.toml`** | PEP 621 dependency + tool config | The canonical Python project file (replaces setup.py + requirements.txt) |
| **`.env.example`** | Env var template | The canonical secret-management pattern (committed, gitignored `.env`) |
| **`uv`** | Python package manager + venv | The 2026 standard (replaces pip + virtualenv + pyenv — pins via `.python-version`) |
| **`Makefile`** | Self-documenting local-dev runner | The canonical GNU make pattern (Google projects all ship a `make help`) |
| **`scripts/dev.sh`** | One-shot bootstrap | Mirrors `journey/scripts/setup.sh` — wraps the 5-step recipe |
| **`scripts/verify.sh`** | 8-tick verify gate | Mirrors `journey/scripts/verify.sh` — `[OK]` / `[FAIL]` per tick |
| **`docker compose`** | Local lakehouse + observability stack | The canonical containerised local dev (no Komodo, no Pangolin, no Locket) |
| **`cloudbuild.yaml`** | Prod deploy pipeline | The canonical GCP-native CI/CD (replaces Jenkins, GitLab CI, Travis) |
| **`cloud/terraform/{envs,modules}/`** | GCP infra-as-code | The canonical Terraform pattern for GCP (12 modules per `cloud/terraform/envs/dev/main.tf`) |
| **`.github/workflows/ci.yml`** | CI gate on PR | The canonical Google-flavoured CI (lint + typecheck + test + baml test on Py 3.11 + 3.12) |
| **Google Secret Manager** | Production secrets | GCP-native (replaces Infisical + Locket + JSON keys) |
| **Workload Identity Federation** | Auth between CI and GCP | GCP-native (no JSON keys for Cloud Build → Cloud Run) |

**What we removed**:
- ❌ `mise.toml` (357 LOC, 47 tasks, tool-version pins that drifted from `pyproject.toml`)
- ❌ `jdx/misse-action` CI step (saves ~15s per CI run)
- ❌ `infra/stacks/` (the 4 NEW gemini-hackathon IaC stacks — deleted by the GCP-first IaC refactor)
- ❌ Komodo + Pangolin + Locket + Infisical (the upstream Cianfhoghlaim 4-stack pattern — all replaced by GCP-native equivalents)
- ❌ The legacy `mise run <task>` syntax in every doc

## The example-project pattern (what we copied)

Every example in `docs/cocoindex_examples/*` follows this shape:

```
example_dir/
├── README.md                  # the canonical 4-step "How to run"
├── main.py                    # the entire pipeline (~150-200 LOC)
├── pyproject.toml             # PEP 621; dependencies inline
├── .env.example               # env vars to copy to .env
└── (no mise.toml, no Makefile beyond a thin shim)
```

The README structure is canonical:
1. **What it does** (1-line hero + 3-line summary)
2. **How it works** (the `target_state = transformation(source_state)` mental model)
3. **Why it's worth a star** (the 4-5 differentiation bullets)
4. **Run it** (4 numbered steps: install → configure → index → query)

Our `README.md` + `docs/LOCAL_DEV.md` follow the same shape.

## The Google-flavoured additions (when the project touches BigQuery / Vertex AI / Cloud Storage)

When the project uses GCP-native services, the canonical Google
pattern adds 4 more pieces:

1. **`cloudbuild.yaml`** at the repo root — 4 steps: baml-generate → docker build → push → deploy
2. **`cloud/terraform/{envs,modules}/`** tree — 12 modules per `cloud/terraform/envs/dev/main.tf`
3. **`.github/workflows/ci.yml`** — lint + mypy + pytest + baml test on Python 3.11 + 3.12
4. **Workload Identity Federation** for auth between CI and GCP (no JSON keys)

## What `mise` did and what replaced each task

The 47 `mise.toml` tasks collapse into 27 `Makefile` targets:

| `mise` category | `make` target | Google-native tool |
|---|---|---|
| `[tools]` version pins | (none — `uv` + `.python-version` handle it) | `uv` |
| `lint` + `format` + `lint:format-check` | `make lint` (= `ruff check` + `ruff format --check`) | GitHub Actions |
| `typecheck` | `make typecheck` (= `mypy gemini_hackathon/`) | GitHub Actions |
| `test` + `test:cov` + `test:fast` | `make test` + `make test-cov` | GitHub Actions |
| `baml:generate` + `baml:test` + `baml:coverage` + `baml:lint` | `make baml` (= generate + test) + `make baml:coverage` (TBD) | GitHub Actions |
| `smoke` + `smoke:quick` + `smoke:verbose` | `make verify` (= the 8-tick gate) | GitHub Actions |
| `setup` + `sync` + `install` | `make setup` + `make install` + `scripts/dev.sh` | `uv` |
| `run` + `backend` + `backend:test` + `shell` | `make run` + `make backend` + `scripts/backend_smoke.py` | `uv` |
| `notebook` + `docs` + `docs:serve` | `make notebook` + `make docs` | `marimo` |
| `docker:build` + `dev` + `down` | `make docker-build` + `make dev` + `make down` | `docker compose` |
| `gcp:*` (4 tasks) | `make cloudbuild` | `cloudbuild.yaml` |
| `journey:*` (8 tasks) | (none — use `journey/scripts/{setup,verify,deploy}.sh`) | `bash` |
| `sourcing:*` (8 tasks) | (none — internal pipeline steps) | `bash` |
| `data:ncce:*` (4 tasks) | `make ncce-extract` + `make ncce-visualise` | `uv` |
| `clean` + `clean:data` | `make clean` + `make clean-data` | (built-in) |
| `ci` | (none — already in `.github/workflows/ci.yml`) | GitHub Actions |

**Net**: 47 `mise.toml` tasks → 27 `Makefile` targets. `mise.toml` → 0 LOC. `Makefile` → ~190 LOC (with awk-parsed help).

## The canonical 5-step local dev recipe

```
1. make install     # uv sync --all-extras
2. cp .env.example .env
3. make dev         # docker compose up --build (the local stack)
4. make baml && uv run python -m cocoindex_flows.uk_ncce.learning_graphs_app
                    && uv run python -m dlt_pipelines.uk_ncce_learning_graphs
5. make backend
```

Or just `make setup` (which does steps 1-2-4-5 in one shot).

Or for the canonical CI gate: `make verify` (the 8-tick verify).

See `docs/LOCAL_DEV.md` for the full walkthrough.

## Where the GCP-native pieces live

```
gemini_hackathon/
├── pyproject.toml                       # PEP 621; deps + tool config
├── .env.example                          # env var template (committed)
├── .python-version                       # the uv-pinned Python version
├── Makefile                              # the canonical 27-target runner (~190 LOC)
├── scripts/
│   ├── dev.sh                            # one-shot bootstrap
│   └── verify.sh                         # 8-tick verify gate
├── cloudbuild.yaml                       # 4-step GCP deploy pipeline (baml → build → push → deploy)
├── cloud/
│   ├── terraform/
│   │   ├── modules/                      # 12 GCP Terraform modules
│   │   └── envs/{dev,prod}/              # per-env wiring (main.tf + backend.tf + terraform.tfvars)
│   ├── scripts/
│   │   └── deploy-cloud-run.sh           # the per-stack deploy script
│   └── workflows/                        # Cloud Workflows (the BIEP pipeline)
├── docker-compose.yml                    # the canonical local stack
├── docker-compose.local.yaml            # the observability override
├── .github/workflows/
│   ├── ci.yml                            # lint + mypy + pytest + baml test
│   ├── dev-deploy.yml                    # dev Cloud Run push on main
│   └── deploy-docs.yml                   # the gh-pages deploy
└── docs/
    ├── LOCAL_DEV.md                      # the 5-step local dev recipe
    ├── GOOGLE_PROJECT_MANAGEMENT.md     # this file
    ├── DEPLOYMENT.md                     # Cloud Run deployment guide
    ├── DEV_DEPLOY.md                     # local-dev + dev-deploy playbook
    └── IAC.md                            # the GCP-first IaC refactor
```

## Cross-references

- `docs/LOCAL_DEV.md` — the 5-step local dev guide (use this on your first clone)
- `docs/DEPLOYMENT.md` — Cloud Run deployment walkthrough
- `docs/DEV_DEPLOY.md` — local-dev + dev-deploy playbook
- `docs/IAC.md` — the GCP-first infrastructure refactor
- `openspec/changes/2026-08-31-replace-mise-with-make-v1/` — the openspec change that removed `mise.toml`
- `openspec/changes/2026-08-30-gcp-first-iac-refactor-v1/` — the openspec change that removed Komodo + Pangolin + Locket + Infisical
- `.agents/skills/openspec/SKILL.md` — the OpenSpec workflow