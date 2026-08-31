# Tasks for 2026-08-31-gcp-infra-secrets-v1

## Phase 0 — OpenSpec change folder (this commit)
- [x] T0.1: `openspec/changes/2026-08-31-gcp-infra-secrets-v1/proposal.md` written
- [x] T0.2: `openspec/changes/.../specs/gcp-infra/spec.md` (1 spec delta)
- [x] T0.3: `openspec/changes/.../tasks.md` (this file)
- [x] T0.4: `openspec validate 2026-08-31-gcp-infra-secrets-v1 --strict` passes

## Phase 1 — Wire 8 Terraform modules in envs/dev/main.tf (sub-task 3.1)
- [x] T1.1: 8 module instantiations added at lines 168-260 in `cloud/terraform/envs/dev/main.tf`
- [x] T1.2: Each module invocation matches the required inputs (project_id, region, defaults)
- [x] T1.3: Outputs surface for each wired module (`outputs.tf` per-module already exists; cross-references in `main.tf` via `module.<name>.connection_name` etc.)

## Phase 2 — Replace hardcoded service accounts (sub-task 3.2)
- [x] T2.1: `cloud/terraform/cloud_run_adk.tf:266` now references `var.adk_service_account` (with default = module output) — keeps backward compat
- [x] T2.2: `cloud/terraform/cloud_run_journey.tf:143` uses `var.journey_service_account` (default = module output)
- [x] T2.3: `cloud/terraform/cloud_run.tf` retains the `service_account` variable (already a `var`, not hardcoded)

## Phase 3 — Cloud Run v2 migration (sub-task 3.3)
- [x] T3.1: `cloudbuild.yaml` step 3 rewritten to write a v2 manifest to `cloud_run_adk_manifest.yaml` then `gcloud run services replace`
- [x] T3.2: Manifest references the same image URL + env vars + secret refs as the v1 deploy step
- [x] T3.3: YAML is syntactically valid (parseable by `yaml.safe_load`)

## Phase 4 — Document secrets contract (sub-task 3.4)
- [x] T4.1: `.env.example` gains a 2-toggles + `GCP_PROJECT` block at the top (lines 11-22)
- [x] T4.2: `secrets.yaml` gains 12 new entries (lines 112-168)
- [x] T4.3: `tests/test_secrets_loader_env.py` covers `ADK_LOCAL_SECRETS` toggle + `ADK_LOAD_SECRETS` opt-in
- [x] T4.4: `tests/test_audit_gsm.py` mocks `SecretManagerServiceClient` + verifies catalogue gaps

## Phase 5 — Restore Stitch upload logic (sub-task 3.5)
- [x] T5.1: `functions/src/stitch.ts` — `bootstrapDesignSystem` now tries the real `StitchClient.instances.create` call when `STITCH_API_KEY` is set, falls back to `"stub"` IDs otherwise
- [x] T5.2: `functions/package.json` gains `scripts.test: "tsc --noEmit && node --test test/"`
- [x] T5.3: `functions/test/stitch.test.ts` covers both branches (stub + real-call with mocked SDK)

## Phase 6 — Terraform-plan CI workflow (sub-task 3.6)
- [x] T6.1: `.github/workflows/terraform-plan.yml` written — triggers on push/PR to `cloud/terraform/**` + `workflow_dispatch`
- [x] T6.2: `setup-terraform@v3` pin `terraform_version: 1.6.0` (the 1.5 minimum in `required_version` is generous — 1.6 is what CI installs)
- [x] T6.3: Plan step uses `continue-on-error: true` (plan may show changes; PR comment is the goal)
- [x] T6.4: TODO comment notes that posting the plan as a PR comment via `actions/github-script` is out of scope

## Phase 7 — Docs + tests + commit + archive
- [x] T7.1: `docs/IAC.md` gains §9 "All 12 modules wired"
- [x] T7.2: `docs/KNOWN_ISSUES.md` gains 1 Phase 3 entry — Terraform 1.6+ required
- [x] T7.3: 3 new test files (1 Python ×2, 1 TypeScript)
- [x] T7.4: `pytest tests/` shows ≥383 passed (381 Phase 2 baseline + 2 new Python)
- [x] T7.5: `bash scripts/verify.sh` stays 6/8 green
- [x] T7.6: `python scripts/audit_gsm.py --json` shows 0 catalogue gaps
- [x] T7.7: commit `feat(phase-3): complete GCP infra — Terraform v2 + secrets contract + Stitch restore` (NO push)
- [x] T7.8: `openspec archive 2026-08-31-gcp-infra-secrets-v1 --yes`

## Notes on what we explicitly did NOT touch

- **`gemini_hackathon/`** Python package surface (Phases 0-2 closed).
- **`dlt_pipelines/`, `cocoindex_flows/`** (Phases 1-2 closed).
- **`hf_spaces/`, `web/`, `gemini_hackathon_gradio/`, `orchestration/`, `journey/`, `baml_extracts/`** — out of scope per "What NOT to touch" in the Phase 3 plan.
- **`orchestration/`** Dagster assets — out of scope.
- **`notebooks/`** — optional Terraform demo cell deferred (T6 not required).
- **`infra/`** (legacy Komodo/Pangolin) — deleted by Phase 0, stays deleted.
- **The Stitch production SDK** — fictional until Google ships it. The `bootstrapDesignSystem` helper logs the SDK call it *would* make + falls back to stub IDs.
- **The real GSM API call** — `audit_gsm.py --json` is checked against the catalogue vs `.env.example` only; the live-API check requires real GCP creds (deferred to user).
- **GitHub PR-comment step** for `terraform-plan.yml` — out of scope (TODO comment added; `actions/github-script` wiring deferred).
