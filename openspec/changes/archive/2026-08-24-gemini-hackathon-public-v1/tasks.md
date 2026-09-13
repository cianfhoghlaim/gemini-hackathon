# Tasks: gemini-hackathon-public-v1

## 1. Project structure

- [ ] 1.1 Set up project structure: `backend/` (Hono + oRPC),
      `web/` (TanStack Start + Convex + CopilotKit + AG-UI),
      `baml_src/gemini_hackathon/` (BAML functions),
      `dlt_pipelines/` (DLT source definitions),
      `notebooks/` (marimo dashboards), `infra/` (Pulumi),
      `tests/` (pytest), `themes/` + `themes/safeguarding/`
      (palette JSON), `openspec/` (this directory),
      `docs/` (this directory's siblings).

## 2. BAML extraction functions (3 NEW files at `baml_src/gemini_hackathon/`)

- [ ] 2.1 `baml_src/gemini_hackathon/extract_source_palette.baml` —
      `ExtractSourcePalette(pdf_path: string, source_name: string)
      -> SourcePalette` (per-source theming)
- [ ] 2.2 `baml_src/gemini_hackathon/extract_equivalencies.baml` —
      `ExtractEquivalencies(source_topic: Topic, source_pdf: string,
      target_jurisdiction: Jurisdiction) -> Equivalencies`
      (cross-jurisdiction equivalency)
- [ ] 2.3 `baml_src/gemini_hackathon/detect_curriculum_changes.baml` —
      `DetectCurriculumChanges(current_pdf: string, previous_pdf: string)
      -> CurriculumChanges` (redline diff)
- [ ] 2.4 Every BAML file uses the `minimax-m3` client (Tier 1)
      per the model-policy spec
- [ ] 2.5 Every BAML class includes the lineage envelope
      (`extractedBy`, `extractedFromPdf`, `confidence`,
      `extractedAt`)

## 3. LLM router (3-tier fallback)

- [ ] 3.1 Implement `gemini_hackathon/llm.py:call_llm()` that
      routes through the 3 tiers
      (`minimax-m3` → `unsloth/gemma-4-26B-A4B-it-GGUF` →
      `vertex_ai/gemini-3.5-flash`) using LiteLLM Router
- [ ] 3.2 Every invocation emits a structlog event with the
      `llm.tier` field (1 / 2 / 3) + `llm.model` + `llm.latency_ms`
- [ ] 3.3 The Cloudflare Workers AI and Qwen3-coder models are
      NOT configured in the router
- [ ] 3.4 The router enforces a 30-second total timeout with one
      retry per tier before falling through

## 4. Fleet primitives (7 wholesale-copied modules at `gemini_hackathon/fleet/`)

- [ ] 4.1 `gemini_hackathon/fleet/gateway.py` — OpenClaw
      channel-fanout gateway (WebChat + Telegram + Slack + Discord +
      WhatsApp + Teams) — wholesale-copied from Cianfhoghlaim
- [ ] 4.2 `gemini_hackathon/fleet/identity.py` — BetterAuth + SIWE
      identity layer — wholesale-copied
- [ ] 4.3 `gemini_hackathon/fleet/armor.py` — Turnstile + PocketID
      admin auth + TinyAuth proxy — wholesale-copied
- [ ] 4.4 `gemini_hackathon/fleet/observability.py` — Langfuse +
      MLflow + structlog observability stack — wholesale-copied
- [ ] 4.5 `gemini_hackathon/fleet/memory.py` — Cognee knowledge
      graph + Graphiti temporal KG + LanceDB vector RAG —
      wholesale-copied
- [ ] 4.6 `gemini_hackathon/fleet/ag_ui.py` — AG-UI protocol
      bindings for TanStack Start + CopilotKit — wholesale-copied
- [ ] 4.7 `gemini_hackathon/fleet/mcp.py` — Firecrawl MCP server +
      the canonical 12-tool surface — wholesale-copied

## 5. Idea agents (4 NEW agents at `gemini_hackathon/agents/`)

- [ ] 5.1 `gemini_hackathon/agents/theming_agent.py` — exposes
      `ExtractSourcePalette` to the AG-UI surface
- [ ] 5.2 `gemini_hackathon/agents/equivalency_generator.py` —
      exposes `ExtractEquivalencies` + the
      `EquivalencyGenerator` chat surface
- [ ] 5.3 `gemini_hackathon/agents/safeguarding_mapper.py` —
      exposes the 5-body safeguarding policy search
- [ ] 5.4 `gemini_hackathon/agents/curriculum_drift_detector.py` —
      exposes `DetectCurriculumChanges` + the redline diff view

## 6. DLT pipelines (2 NEW pipelines at `dlt_pipelines/`)

- [ ] 6.1 `dlt_pipelines/official_doc_fetcher.py` — fetches the
      official PDFs from the 8 jurisdictions + the 5 safeguarding
      bodies and loads them into DuckLake + MotherDuck
- [ ] 6.2 `dlt_pipelines/safeguarding_fetcher.py` — fetches the
      safeguarding-policy PDFs separately so that the safeguarding
      theming roster is independent of the syllabus roster

## 7. Marimo notebook (1 NEW notebook at `notebooks/`)

- [ ] 7.1 `notebooks/theming_extraction.py` — operator-facing
      palette-authoring dashboard. Loads a PDF, runs
      `ExtractSourcePalette`, shows the JSON, lets the operator
      approve / edit / discard, then writes the JSON to
      `themes/<source_key>_palette.json`

## 8. Frontend (1 NEW app at `web/`)

- [ ] 8.1 TanStack Start app at `web/` with Convex schema +
      CopilotKit runtime + AG-UI bindings + the 4 chat surfaces
      (one per idea)
- [ ] 8.2 The theming custom-properties injection at the root
      `<html>` element so every page renders with the chosen
      source's palette
- [ ] 8.3 The equivalency view shows the source topic on the left
      and the destination body's rendered view on the right
- [ ] 8.4 The safeguarding map shows the 5 bodies' policies
      side-by-side
- [ ] 8.5 The curriculum drift detector shows a redline diff
      between the previous + current PDF

## 9. Docker + CI

- [ ] 9.1 `Dockerfile` at the repo root (multi-stage, `uv`-based)
- [ ] 9.2 `docker-compose.yaml` with the backend + frontend +
      Langfuse + MLflow + Convex services
- [ ] 9.3 `.github/workflows/ci.yml` — runs `mise run lint`,
      `mise run py:typecheck`, `mise run turbo typecheck`,
      `pytest`, `openspec validate <change> --strict`

## 10. Documentation

- [ ] 10.1 `README.md` — the main project README
- [ ] 10.2 `ARCHITECTURE.md` — the architecture deep-dive
- [ ] 10.3 `AGENTS.md` — the root agent routing file
- [ ] 10.4 `docs/MODEL_POLICY.md` — the 3-tier model policy
- [ ] 10.5 `docs/THEMING.md` — the per-source theming guide
- [ ] 10.6 `docs/DEPLOYMENT.md` — local + Cloud Run deployment
- [ ] 10.7 `LICENSE` — MIT with copyright Cian Mac Aindréisigh 2026
- [ ] 10.8 `.github/ISSUE_TEMPLATE/bug_report.md` +
      `feature_request.md` + `PULL_REQUEST_TEMPLATE.md`

## 11. Validation

- [ ] 11.1 `openspec validate gemini-hackathon-public-v1 --strict`
      passes
- [ ] 11.2 `openspec validate openspec/specs/theming/ --strict`
      passes
- [ ] 11.3 `openspec validate openspec/specs/model-policy/ --strict`
      passes
- [ ] 11.4 `openspec validate openspec/specs/equivalency/ --strict`
      passes

## 12. Commit + archive

- [ ] 12.1 `git add openspec/changes/2026-08-24-gemini-hackathon-public-v1/`
      only (no `git add -A` — concurrent-agent write safety)
- [ ] 12.2 `git commit -m "feat(hackathon): openspec proposal + 3 spec deltas + 9 docs (Change 1)"`
- [ ] 12.3 `git push origin main`
- [ ] 12.4 After deploy: `openspec archive gemini-hackathon-public-v1 --yes`