# Tasks: gemini_hackathon mirror

## Stage 0
- [ ] T0.1 — Confirm parent change is archived

## Stage 1 — Spec delta
- [ ] T1.1 — Write `openspec/specs/adk-deep-research-control-plane/spec.md`
- [ ] T1.2 — Write the change's spec delta

## Stage 2 — Backend module
- [ ] T2.1 — Create `gemini_hackathon_backend/agents/gemini_deep_research.py`
- [ ] T2.2 — Update `gemini_hackathon_backend/agents/__init__.py`

## Stage 3 — Terraform module
- [ ] T3.1 — Create `cloud/terraform/modules/cloud_run_deep_research/`

## Stage 4 — Validation
- [ ] T4.1 — Run `make verify`
- [ ] T4.2 — Run `openspec validate --strict`
