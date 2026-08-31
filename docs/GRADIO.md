# docs/GRADIO.md — the 6 Gradio studios + Phase 4 polish

> The British Isles Education Platform runs 6 Gradio studios (one per
> educational surface). Phase 4 (the `2026-08-31-journey-gradio-polish-v1`
> openspec change, committed in the `feat(phase-4)` commit) wired the
> 4 studios that still had Markdown stubs + added the sourcing-copilot
> tests.

## The 6 studios

| # | Studio | Module | Status | Notes |
|---|--------|--------|--------|-------|
| 1 | **An Scrudu** | `gemini_hackathon_gradio.an_scrudu` | ✅ Production | LC past-paper heatmap (the canonical showcase) |
| 2 | **Editorial Studio** | `gemini_hackathon_gradio.editorial_studio` | ✅ Phase 4 wired | Big British Isles Education surface with 5 stage tabs |
| 3 | **Anam Oideachais** | `gemini_hackathon_gradio.anam_education` | ✅ Phase 4 wired | Education Integration Studio (7 feature tabs) |
| 4 | **Oideachais Mission Control** | `gemini_hackathon_gradio.oideachais_mission_control` | ✅ Phase 4 expanded | 5 stage + 5 NEW operator tabs |
| 5 | **Oideachais PDF Review** | `gemini_hackathon_gradio.oideachais_pdf_review` | ✅ Phase 4 restructured | 3-tab layout (Upload / Review / Export) |
| 6 | **An Learning Graph** | `gemini_hackathon_gradio.an_learning_graph` | ✅ Phase 3 wired | NCCE learning-graph showcase (4 tabs) |

## Phase 4 polish summary

### `editorial_studio` — 4 Markdown stubs replaced

The 4 tabs that previously said "Wired in W12." (Aistear / Bunscoil /
MeanScoil / Ollscoil) now wire to the canonical
`CertificatePipeline.run()` from `gemini_hackathon/certificate/pipeline.py:87`.

Each tab has:
- A `learner_id` textbox
- A `subject` dropdown sourced from `SUBJECT_WIRING_REGISTRY` (`gemini_hackathon/agents/registry.py:94`)
- An "Extract certificate" button
- 2 outputs — a Markdown summary + a `gr.JSON()` with the full `CertificateRecord`

### `anam_education` — 7 tabs each get a BAML extraction button

Each of the 7 tabs (Curriculum Map / Chemistry Visual / Exit Card /
Gaelscribhneoir / Bilingual EN/GA / Certificate / Skill Progression) now
has a `_build_baml_operator()` that calls
`BAMLSyllabusExtractor.extract()` honouring `BAML_TEST_MODE=true`. The
result renders as `gr.JSON()`.

### `oideachais_mission_control` — 5 NEW operator tabs

5 NEW operator tabs were added alongside the 5 stage tabs:

1. **Subjects** — the 14-subject `SUBJECT_WIRING_REGISTRY` as a Dataframe
2. **Models** — `MODEL_REGISTRY._entries` as a Dataframe
3. **Outputs** — generated certificates from `data/certificates/*.json`
4. **Observability** — 5 mocked structlog events (real Logfire / Langfuse lands in Phase 5)
5. **Settings** — `.env.example` keys as a Markdown code block

### `oideachais_pdf_review` — 3-tab layout + `@spaces.GPU` handler

Restructured from a single-column operator into 3 tabs (Upload / Review /
Export). The `@spaces.GPU` handler is now registered as
`_gpu_suggestion_handler` — the decorator is conditional on `SPACE_ID`
so the dev / CI path doesn't require the `spaces` package.

## Tests

`tests/gradio/{test_editorial_studio,test_anam_education,test_oideachais_mission_control,test_oideachais_pdf_review}.py`
+ `tests/gradio/conftest.py` cover all 4 newly-wired studios (28 tests
total). `journey/sourcing_copilot_tests/{test_tools,test_agent}.py`
covers the SourcingCopilot's 7 tools + agent factory (15 tests).

## Sourcing dedupe

`journey/sourcing/sourcing/` (the Phase 3 subagent's scope-creep
duplicate) was deleted. The canonical `gemini_hackathon/journey/sourcing/`
(with the `_shared_fs()` singleton pattern) remains as the single source
of truth.

## Quick verify

```bash
cd /Users/cianmacandeisigh/dev/gemini_hackathon
for studio in editorial_studio anam_education oideachais_mission_control oideachais_pdf_review; do
  uv run python -c "
from gemini_hackathon_gradio import ${studio}
app = ${studio}.build_app()
assert app is not None, 'build_app() returned None'
print(f'  ${studio}: build_app() OK')
" 2>&1
done
```
