# AGENTS.md — root agent routing file

> **For AI agents working in the `gemini_hackathon` repo.**
> This file is the **first file an agent reads** when entering the
> repo. It describes the canonical subagent routing, the priority
> skills, and the quality gates.

---

## TL;DR

```bash
# 1. Read this file (AGENTS.md)
# 2. Read the priority skills (below)
# 3. Run the quality gates (make verify)
# 4. Commit only when the user explicitly asks (see Commit policy below)
```

---

## Priority skills (read these FIRST)

These 5 skills are the **highest-priority** knowledge surface for
this repo. Load them before doing any work in this repo.

| # | Skill | Path | Why it matters |
|--:|-------|------|----------------|
| 1 | **CCC** (CocoIndex Code) | `.agents/skills/ccc/SKILL.md` | Semantic code search — finds code by meaning, not just text |
| 2 | **openspec** | `.agents/skills/openspec/SKILL.md` | OpenSpec workflow + the 14 priority specs + the spec-delta format |
| 2.5 | **submission-scope** | [`docs/SUBMISSION_SCOPE.md`](docs/SUBMISSION_SCOPE.md) | What the demo runs on — 97 in-scope PDFs; 8 jurisdictions deferred for this submission |
| 3 | **make** | (built-in) | The self-documenting `Makefile` — `make help` lists all 27 targets. Replaces the deprecated `mise.toml` |
| 4 | **secrets-management** | `.agents/skills/secrets-management/SKILL.md` | Google Secret Manager + Workload Identity Federation (the GCP-first IaC refactor) |
| 5 | **knowledge-sync-loop** | `.agents/skills/knowledge-sync-loop/SKILL.md` | The 6-layer pull-based sync architecture |

If the agent can read only one skill, it should be **openspec** —
every change to this repo flows through `openspec/changes/<id>/`.

---

## Stack count

This repo does **not** ship Docker Compose stacks (the4 IaC
stacks that previously lived under `infra/stacks/` were deleted
by the `2026-08-30-gcp-first-iac-refactor-v1` change — replaced by
the GCP-native Cloud Run + Terraform + Cloud Build + Google Secret
Manager + Workload Identity Federation substrate). The canonical
local-dev path is `make dev` (single `docker-compose.yml` + a single
`docker-compose.local.yaml`).

For prod, see `cloud/terraform/envs/{dev,prod}/` (12 Terraform modules per `cloud/terraform/envs/dev/main.tf`).

---

## Subagent dispatch map

When the user asks a question that requires more than one skill
load, dispatch to the appropriate subagent. The subagents are
defined in `.opencode/agents/` and have their own tools.

| Subagent | Dispatch keywords | Routes to |
|----------|-------------------|-----------|
| `data-platform` | DLT, Dagster, BAML, DuckLake, MotherDuck, marimo notebooks, CocoIndex | `dlt_pipelines/`, `orchestration/`, `baml_src/gemini_hackathon/`, `notebooks/` |
| `infrastructure` | Cloud Run, Cloud Build, Terraform, Cloud SQL, Memorystore, BigQuery, Workload Identity Federation | `cloud/terraform/`, `cloudbuild.yaml`, `cloud/workflows/` |
| `agent-platform` | The 12-agent fleet, OpenClaw, Vertex AI Memory Bank, Langfuse | `agents/`, `gemini_hackathon/fleet/` |
| `frontend-apps` | TanStack Start, Firebase, Hono, CopilotKit, AG-UI | `web/`, `web/src/routes/*/` |
| `research` | Firecrawl, arXiv papers, Hugging Face, sentence-transformers | `baml_extracts/`, `notebooks/` |

The subagent is selected by matching the user's request to the
"Dispatch keywords" column. When the request spans multiple
subagents, dispatch to all of them in parallel and synthesise
the results.

---

## Quality gates

Before committing any change, run all four quality gates. The gates
are defined in the `Makefile` (run `make help` for the full list).

```bash
# 1. Lint (Python + Markdown + YAML — ruff check + ruff format --check)
make lint

# 2. Python typecheck (mypy on the gemini_hackathon/ package)
make typecheck

# 3. Tests (pytest)
make test

# 4. The 8-tick verify gate (calls scripts/verify.sh)
make verify

# 5. OpenSpec validation
openspec validate <change-id> --strict
```

If any gate fails, fix the failure before committing. Do **not**
commit with failing gates. The CI workflow (`.github/workflows/ci.yml`)
runs `make lint` + `make typecheck` + `make test` + `baml-cli test`
on every push across the Python 3.11 + 3.12 matrix.

> **Note**: there is no `mise.toml` and no `mise run` in this repo.
> Per the `2026-08-31-replace-mise-with-make-v1` openspec change,
> the canonical task runner is the `Makefile` (matches the example
> projects in `docs/cocoindex_examples/*` + `docs/adk-examples/*`).
> See `docs/GOOGLE_PROJECT_MANAGEMENT.md` for the rationale.

---

## Commit policy

**The user explicitly asks for commit/push.** Do not commit or
push without an explicit "commit this" or "push to origin"
instruction. The convention is per the upstream
`concurrent-agent-write-safety-v1` skill — the user might be
running multiple agents in parallel and an unexpected commit
from this agent could clobber work from another agent.

When the user does explicitly ask for a commit:

1. Inspect `git status` + `git diff` + `git log --oneline -10`
2. Stage only the intended files (`git add <file>` not `git add -A`)
3. Write a concise commit message that matches the repo style
4. Push with `git push origin main`
5. Report the commit SHA + the push result

---

## OpenSpec workflow (quick reference)

Every change to this repo flows through OpenSpec 1.4 (the
spec-driven schema). The workflow is:

1. Create the change folder:
   `mkdir -p openspec/changes/<id>/specs/<capability>/`
2. Write `proposal.md` (with `## Why` + `## What Changes` +
   `## Impact` + `## Dependencies`)
3. Write `tasks.md` (the ordered checklist with quality gates
   between phases)
4. Write the spec delta in
   `openspec/changes/<id>/specs/<capability>/spec.md`
5. Validate: `openspec validate <id> --strict`
6. Hand off to build mode for implementation
7. After deploy: `openspec archive <id> --yes`

The current active change is
[`2026-08-24-gemini-hackathon-public-v1`](openspec/changes/2026-08-24-gemini-hackathon-public-v1/proposal.md).

---

## File conventions

- **Python**: dignified Python 3.11+ (modern type syntax, pathlib,
  ABC-based interfaces). See `.agents/skills/dignified-python/SKILL.md`.
- **TypeScript**: strict mode, ESM only, no CommonJS. The
  frontend is at `web/`, the backend is at `backend/`.
- **BAML**: BAML 0.223.0 syntax, the 8 canonical patterns, the
  cross-file import conventions. See `.agents/skills/baml/SKILL.md`.
- **DLT**: the `@dlt.source` + `@dlt.resource` decorators, the
  `dlt_sources/common/` helpers. See `.agents/skills/dlt-sync/SKILL.md`.
- **marimo**: dual-mode pattern (CLI + reactive), ibis-first SQL,
  PEP 723 inline dependency blocks. See `.agents/skills/marimo/SKILL.md`.

---

## References

- [`README.md`](README.md) — the main project README
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — the architecture deep-dive
- [`docs/LOCAL_DEV.md`](docs/LOCAL_DEV.md) — the 5-step local dev recipe
- [`docs/GOOGLE_PROJECT_MANAGEMENT.md`](docs/GOOGLE_PROJECT_MANAGEMENT.md) — why we use Make + uv + Docker Compose + Cloud Build + GitHub Actions
- [`docs/MODEL_POLICY.md`](docs/MODEL_POLICY.md) — the model policy
- [`docs/THEMING.md`](docs/THEMING.md) — the theming guide
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — the Cloud Run deployment guide
- [`docs/DEV_DEPLOY.md`](docs/DEV_DEPLOY.md) — the local-dev + dev-deploy playbook
- [`.agents/skills/openspec/SKILL.md`](.agents/skills/openspec/SKILL.md) —
  the OpenSpec skill (the canonical reference)
- [`openspec/AGENTS.md`](openspec/AGENTS.md) — the OpenSpec workflow
  + the 27 openspec changes