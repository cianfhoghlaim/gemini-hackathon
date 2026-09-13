# Tasks: gemini_hackathon mirror

## Stage 0
- [x] T0.1 — Confirm parent change is archived (`openspec/changes/archive/2026-09-06-adk-gemini-deep-research-control-plane-v1/` exists in cianfhoghlaim)

## Stage 1 — Spec delta
- [x] T1.1 — Write `openspec/specs/adk-deep-research-control-plane/spec.md`
- [x] T1.2 — Write the change's spec delta

## Stage 2 — Backend module
- [x] T2.1 — Create `gemini_hackathon_backend/agents/gemini_deep_research.py`
- [x] T2.2 — Update `gemini_hackathon_backend/agents/__init__.py` (fixed import to `build_ncca_panel_agent`)

## Stage 3 — Terraform module
- [x] T3.1 — Create `cloud/terraform/modules/cloud_run_deep_research/` (12th module; wraps `cloudrun_service` with deep-research-specific defaults: scale-to-zero, 4Gi memory, 900s timeout, GOOGLE_API_KEY via Secret Manager)

## Stage 4 — Validation
- [x] T4.1 — Run `make verify` (8/8 ticks green)
- [x] T4.2 — Run `openspec validate --strict` (valid)

## Post-2026-09-13 additions
- [x] PA.1 — Promote 9 M3 chokepoint aliases (minimax-m3, kimi-k2.6, glm-5.1, minimax-m2.5, mimo-v2.5, deepseek-v4-flash, deepseek-v4-pro, kimi-k2.7-code, kimi-k3) to hackathon profile in `gemini_hackathon/model_registry.py` per the centralized-model-registry spec
- [x] PA.2 — Trigger Cloud Build deploy (`fe0e395e-6690-4e77-bd06-8f38a7f172a9`) with image `europe-west1-docker.pkg.dev/agentic-hackathon-august-26/gemini-hackathon/backend:6ff16e0`
- [x] PA.3 — Set £300/month budget alert (`5adcef7a-53a9-496e-9b1b-b34335335153`) on `agentic-hackathon-august-26`
