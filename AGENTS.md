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
# 3. Run the quality gates (mise run lint && mise run py:typecheck && mise run turbo typecheck)
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
| 3 | **mise** | `.agents/skills/mise/SKILL.md` | mise.toml task authoring + the canonical 9-namespace task catalogue |
| 4 | **secrets-management** | `.agents/skills/secrets-management/SKILL.md` | Infisical + Locket + mise three-way contract |
| 5 | **knowledge-sync-loop** | `.agents/skills/knowledge-sync-loop/SKILL.md` | The 6-layer pull-based sync architecture |

If the agent can read only one skill, it should be **openspec** —
every change to this repo flows through `openspec/changes/<id>/`.

---

## Stack count

This repo ships with **93 Docker Compose stacks** under
`infra/stacks/` (89 wholesale-copied from Cianfhoghlaim + 4 NEW
gemini_hackathon-specific stacks). The canonical 6-file
GOLD_STANDARD pattern (per the upstream `stacks-sync` skill) is:

```
<stack>/
├── compose.yaml      # the Docker Compose definition
├── sidecar.yaml       # the Locket sidecar (per the 3-way contract)
├── secrets.env       # the secret bindings (NOT committed)
├── pangolin.yaml     # the Pangolin resource definition
├── blueprint.yaml    # the Komodo blueprint
└── .env.example      # the environment variable template
```

The 4 NEW gemini_hackathon stacks are:

1. `infra/stacks/gemini_hackathon_backend/` — the Hono + oRPC
   backend
2. `infra/stacks/gemini_hackathon_frontend/` — the TanStack
   Start frontend
3. `infra/stacks/gemini_hackathon_observability/` — the
   Langfuse + MLflow + Convex services
4. `infra/stacks/gemini_hackathon_lakehouse/` — the DuckLake +
   MotherDuck + LanceDB services

---

## Subagent dispatch map

When the user asks a question that requires more than one skill
load, dispatch to the appropriate subagent. The subagents are
defined in `.opencode/agents/` and have their own tools.

| Subagent | Dispatch keywords | Routes to |
|----------|-------------------|-----------|
| `data-platform` | DLT, Dagster, BAML, DuckLake, MotherDuck, marimo notebooks, CocoIndex | `dlt_pipelines/`, `orchestration/`, `baml_src/gemini_hackathon/`, `notebooks/` |
| `infrastructure` | Komodo, Pangolin, Locket, Infisical, Pulumi, Dagger | `infra/stacks/`, `bonneagar/` |
| `agent-platform` | The 12-agent fleet, OpenClaw, Letta, RisingWave, Langfuse | `agents/`, `gemini_hackathon/fleet/` |
| `frontend-apps` | TanStack Start, Convex, Hono, CopilotKit, AG-UI, Babylon.js | `web/`, `web/apps/*/` |
| `research` | Firecrawl, arXiv papers, Hugging Face, sentence-transformers | `baml_extracts/`, `notebooks/` |

The subagent is selected by matching the user's request to the
"Dispatch keywords" column. When the request spans multiple
subagents, dispatch to all of them in parallel and synthesise
the results.

---

## Quality gates

Before committing any change, run all three quality gates. The
gates are defined in `mise.toml`.

```bash
# 1. Lint (Python + TypeScript + BAML + Markdown + YAML)
mise run lint

# 2. Python typecheck (mypy + pyright on the gemini_hackathon/ package)
mise run py:typecheck

# 3. Turbo typecheck (TypeScript on web/ and backend/)
mise run turbo typecheck

# 4. OpenSpec validation
openspec validate <change-id> --strict

# 5. Tests
mise run test
```

If any gate fails, fix the failure before committing. Do **not**
commit with failing gates.

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
- [`docs/MODEL_POLICY.md`](docs/MODEL_POLICY.md) — the model policy
- [`docs/THEMING.md`](docs/THEMING.md) — the theming guide
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — the deployment guide
- [`.agents/skills/openspec/SKILL.md`](.agents/skills/openspec/SKILL.md) —
  the OpenSpec skill (the canonical reference)
- [`openspec/AGENTS.md`](openspec/AGENTS.md) — the OpenSpec workflow
  + the 14 priority specs