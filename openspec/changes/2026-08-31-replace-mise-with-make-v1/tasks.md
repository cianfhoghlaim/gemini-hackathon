# Tasks for 2026-08-31-replace-mise-with-make-v1

## Phase 0 — OpenSpec change folder (this commit)
- [x] T0.1: `openspec/changes/2026-08-31-replace-mise-with-make-v1/proposal.md` written
- [x] T0.2: `openspec/changes/.../specs/task-runner/spec.md` (1 spec delta)
- [x] T0.3: `openspec/changes/.../tasks.md` (this file)
- [x] T0.4: `openspec validate 2026-08-31-replace-mise-with-make-v1 --strict` passes

## Phase 1 — Delete `mise.toml`
- [ ] T1.1: `rm mise.toml` (357 LOC → 0)
- [ ] T1.2: `git grep mise` outside this change folder returns 0 matches

## Phase 2 — New `Makefile`
- [ ] T2.1: `Makefile` rewritten with `awk`-parsed `help` target
- [ ] T2.2: 25 phony targets covering every workflow an operator calls locally
- [ ] T2.3: `make help` exits 0 + prints the 25-target table

## Phase 3 — `scripts/dev.sh` + `scripts/verify.sh`
- [ ] T3.1: `scripts/dev.sh` — one-shot bootstrap (mirrors `journey/scripts/setup.sh`)
- [ ] T3.2: `scripts/verify.sh` — 8-tick verify gate (mirrors `journey/scripts/verify.sh`)

## Phase 4 — `docs/LOCAL_DEV.md`
- [ ] T4.1: `docs/LOCAL_DEV.md` — the step-by-step local dev guide (~250 LOC, 5 steps)
- [ ] T4.2: Cross-links from `README.md` + `docs/DEPLOYMENT.md` + `docs/DEV_DEPLOY.md`

## Phase 5 — Update `README.md` + `AGENTS.md`
- [ ] T5.1: `README.md` §11 "Quick start" updated to use `make`
- [ ] T5.2: `AGENTS.md` §"TL;DR" + §"Quality gates" updated to use `make`

## Phase 6 — Update `.github/workflows/ci.yml`
- [ ] T6.1: `ci.yml` removes the `jdx/mise-action` install step
- [ ] T6.2: `ci.yml` replaces `mise run <task>` invocations with `make <target>`

## Phase 7 — Update `cloudbuild.yaml`
- [ ] T7.1: `cloudbuild.yaml` adds a `baml-cli generate` step before the `docker build` step
- [ ] T7.2: The build step now uses `baml_client/` regenerated inside the image

## Phase 8 — Update `docs/DEPLOYMENT.md` + `docs/DEV_DEPLOY.md`
- [ ] T8.1: `docs/DEPLOYMENT.md` §1 + §2 updated
- [ ] T8.2: `docs/DEV_DEPLOY.md` §0 + §1 + the "TL;DR — 4 commands" block updated

## Phase 9 — Update `scripts/setup.sh`
- [ ] T9.1: `scripts/setup.sh` replaces any `mise run` references with `make install` + `make baml`

## Phase 10 — `docs/GOOGLE_PROJECT_MANAGEMENT.md`
- [ ] T10.1: `docs/GOOGLE_PROJECT_MANAGEMENT.md` — 1-page rationale

## Phase 11 — Final validation
- [ ] T11.1: `make help` exits 0
- [ ] T11.2: `openspec validate 2026-08-31-replace-mise-with-make-v1 --strict` passes
- [ ] T11.3: `git grep mise` outside this change folder returns 0 matches
- [ ] T11.4: `make dev` (docker compose up --build) starts the local stack
- [ ] T11.5: `make verify` exits 0
- [ ] T11.6: `openspec/changes/INDEX.md` updated to bump 27 → 28 changes
- [ ] T11.7: commit + push
- [ ] T11.8: archive the OpenSpec change after deploy