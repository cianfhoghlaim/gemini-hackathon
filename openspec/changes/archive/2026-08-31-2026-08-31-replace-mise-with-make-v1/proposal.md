# 2026-08-31-replace-mise-with-make-v1

> **Phase D of the 2026-08-31 batch.** Drops the 357-LOC
> `mise.toml` (47 tasks) and replaces it with the canonical
> **Google-flavoured project management** pattern: a self-documenting
> `Makefile` (~80 LOC, `awk`-parsed `help` + 25 phony targets) +
> `scripts/dev.sh` (one-shot bootstrap, mirrors `journey/scripts/setup.sh`)
> + `scripts/verify.sh` (8-tick verify gate, mirrors
> `journey/scripts/verify.sh`) + `docs/LOCAL_DEV.md` (step-by-step local
> dev guide). Aligns the repo with every example in `docs/cocoindex_examples/`
> + every project in `docs/adk-examples/` (which use no `mise`).

## Why

The current `mise.toml` has **47 tasks + a `[tools]` version-pin block**
that duplicate what `uv`, `docker compose`, `cloudbuild.yaml`, and
`.github/workflows/ci.yml` already do. Removing it:

- **Aligns with the example projects.** Every example in `docs/cocoindex_examples/`
  (pdf_embedding, code_embedding, patient_intake_extraction_baml, bigquery_target,
  meeting_notes_graph_falkordb, …) + every project in `docs/adk-examples/`
  (adk2-tutorial, monstertix, loop-lab-table) uses **only** `pyproject.toml`
  + `.env.example` + `README.md` + a `main.py` — no `mise`, no
  multi-file task runner.
- **Eliminates a tool-version-pin drift surface.** `mise.toml` pinned
  Python 3.12 but `pyproject.toml` says `>=3.11` — they drifted.
  `uv` already pins the runtime Python via `.python-version` and
  `[project] requires-python`.
- **Cuts CI setup time.** Removing the `jdx/mise-action` install step
  in `.github/workflows/ci.yml` saves ~15s per CI run.
- **Cuts repo surface.** `mise.toml` (357 LOC) → `Makefile` (~80 LOC).
  Net repo delta: -277 LOC, -1 file (counting `mise.toml` removal).

The example project pattern is canonical:

```
example_dir/
├── README.md                  # 4-step "How to run" UX
├── main.py                    # the entire pipeline (~150-200 LOC)
├── pyproject.toml             # PEP 621; dependencies inline
├── .env.example               # env vars to copy to .env
└── (no mise.toml, no Makefile beyond a thin shim, no shell scripts)
```

The Google-flavoured twist (when the project touches BigQuery / Vertex AI
/ Cloud Storage / Secret Manager — which we do, per the
`2026-08-30-gcp-first-iac-refactor-v1` change) adds:

- **`cloudbuild.yaml`** at the repo root (3-4 steps: baml generate → build → push → deploy)
- **`cloud/terraform/{envs,modules}/`** tree (12 modules per `cloud/terraform/envs/dev/main.tf`)
- **`.github/workflows/ci.yml`** (lint + mypy + pytest + baml test)
- **`Makefile`** as a thin local-dev wrapper (~80 LOC, `awk`-parsed help)

## What changes

### Phase 0 — OpenSpec change folder (1 + 2 spec deltas)

- [x] T0.1: `openspec/changes/2026-08-31-replace-mise-with-make-v1/proposal.md` (this file)
- [x] T0.2: `openspec/changes/.../specs/task-runner/spec.md` (1 spec delta)
- [x] T0.3: `openspec/changes/.../tasks.md`
- [x] T0.4: `openspec validate 2026-08-31-replace-mise-with-make-v1 --strict` passes

### Phase 1 — Delete `mise.toml` (1 file)

- [ ] T1.1: `rm mise.toml` (357 LOC → 0)
- [ ] T1.2: No `git grep mise` matches outside this openspec change folder

### Phase 2 — New `Makefile` (~80 LOC, 25 phony targets)

- [ ] T2.1: `Makefile` rewritten with `awk`-parsed `help` target
- [ ] T2.2: 25 phony targets covering every workflow an operator calls locally (no more, no less)
- [ ] T2.3: `make help` exits 0 + prints the 25-target table

### Phase 3 — `scripts/dev.sh` + `scripts/verify.sh` (2 files)

- [ ] T3.1: `scripts/dev.sh` — one-shot bootstrap (mirrors `journey/scripts/setup.sh`)
- [ ] T3.2: `scripts/verify.sh` — 8-tick verify gate (mirrors `journey/scripts/verify.sh`)

### Phase 4 — `docs/LOCAL_DEV.md` (the new step-by-step guide)

- [ ] T4.1: `docs/LOCAL_DEV.md` — the step-by-step local dev guide (~250 LOC, 5 steps)
- [ ] T4.2: Cross-links from `README.md` + `docs/DEPLOYMENT.md` + `docs/DEV_DEPLOY.md`

### Phase 5 — Update `README.md` + `AGENTS.md` (replace `mise run` with `make`)

- [ ] T5.1: `README.md` §11 "Quick start" updated to use `make` + cross-link `docs/LOCAL_DEV.md`
- [ ] T5.2: `AGENTS.md` §"TL;DR" + §"Quality gates" updated to use `make`

### Phase 6 — Update `.github/workflows/ci.yml` (drop `mise` install)

- [ ] T6.1: `ci.yml` removes the `jdx/mise-action` install step
- [ ] T6.2: `ci.yml` replaces `mise run <task>` invocations with `make <target>`

### Phase 7 — Update `cloudbuild.yaml` (add `baml-cli generate` step)

- [ ] T7.1: `cloudbuild.yaml` adds a `baml-cli generate` step before the `docker build` step
- [ ] T7.2: The build step now uses `baml_client/` regenerated inside the image

### Phase 8 — Update `docs/DEPLOYMENT.md` + `docs/DEV_DEPLOY.md` (replace `mise run`)

- [ ] T8.1: `docs/DEPLOYMENT.md` §1 + §2 updated
- [ ] T8.2: `docs/DEV_DEPLOY.md` §0 + §1 + the "TL;DR — 4 commands" block updated

### Phase 9 — Update `scripts/setup.sh` (compose with new `Makefile install`)

- [ ] T9.1: `scripts/setup.sh` replaces any `mise run` references with `make install` + `make baml`

### Phase 10 — `docs/GOOGLE_PROJECT_MANAGEMENT.md` (the 1-page rationale)

- [ ] T10.1: `docs/GOOGLE_PROJECT_MANAGEMENT.md` — 1-page rationale (mirrors `docs/IAC.md`)

### Phase 11 — Final validation

- [ ] T11.1: `make help` exits 0
- [ ] T11.2: `openspec validate 2026-08-31-replace-mise-with-make-v1 --strict` passes
- [ ] T11.3: `git grep mise` outside this openspec change folder returns 0 matches
- [ ] T11.4: The `mise.toml`-era `dev` task was already deleted (commit `a92d8c8` Phase 2 GCP-first) — verify `make dev` works in its place
- [ ] T11.5: `make verify` exits 0 (the 8-tick verify gate)
- [ ] T11.6: `mise.toml` row in `openspec/changes/INDEX.md` updated

## Acceptance

- `mise.toml` no longer exists at the repo root
- `make help` prints 25 targets + exits 0
- `make verify` exits 0 (imports + baml + lint + typecheck + dlt-smoke + cocoindex-smoke + gradio-imports + dagster-imports)
- `make install && make baml` brings up the local dev environment without `mise`
- `git grep mise` outside `openspec/changes/2026-08-31-replace-mise-with-make-v1/` returns 0 matches
- `openspec validate 2026-08-31-replace-mise-with-make-v1 --strict` passes
- `mise run lint && mise run py:typecheck && mise run turbo typecheck` is now `make lint && make typecheck && (cd web && bun run typecheck)` (per `AGENTS.md`)
- The README §11 "Quick start" cross-links `docs/LOCAL_DEV.md`

## Dependencies

- **Blocked by:** nothing (the GCP-first IaC refactor is already merged to main; the docker-compose consolidation in commit `a92d8c8` removed the `dev` task already).
- **Unblocks:** nothing (this is a hygiene change).
- **Cross-repo:** the upstream cianfhoghlaim monorepo is unaffected — this is gemini_hackathon-only.

## Compatibility

- **No code changes** to the Python package, the BAML contracts, the DLT pipelines, or the CocoIndex Apps.
- **No data migration** — the existing `data/bi_ep/extracted_syllabi.sqlite` + DuckDB + Firestore collections are unchanged.
- **The only runtime change**: the `mise` tool disappears. Operators who previously ran `mise run <task>` will switch to `make <target>` (or direct `uv run python -m ...` invocations).
- **CI** (`.github/workflows/ci.yml`) drops the `jdx/mise-action` install step — saves ~15s per CI run.