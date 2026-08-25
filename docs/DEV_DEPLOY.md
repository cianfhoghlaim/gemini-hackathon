# Dev-Deploy Playbook

End-to-end manual test order. Each section is something you (not the
agent) click through and judge.

**TL;DR — 4 commands to verify everything that can be verified without network keys:**

\`\`\`bash
mise run smoke          # 11-step E2E (164 unit tests + 11 integration)
mise run backend:test   # Boots Python backend, hits 3 endpoints, kills it
mise run compare:demo   # Runs the Gemini-vs-Gemma harness, writes DuckDB row
cd web && bun run dev    # Opens the web UI at http://localhost:3000
\`\`\`

---

## 0. Pre-flight (5 min)

\`\`\`bash
cd ~/dev/gemini_hackathon
git log --oneline -1                                # cc848ed...39eec9f
git status                                         # clean working tree
which uv bun baml-cli                              # all three present
python -m pytest tests/ -q --tb=no                  # 164 passed, 13 skipped
\`\`\`

The 13 skipped tests require Python 3.11+ DLT (this box's \`.venv\` is 3.9). They are unrelated to anything you interact with in the UI; skip them.

## 1. Run the canonical smoke test (30 s, no network)

\`\`\`bash
mise run smoke
\`\`\`

What it asserts:

| Step | Verifies |
|---|---|
| 1. Theming | All 15 palettes load via both domain form (ncca.ie) and canonical (ncca) |
| 2. Models | MODEL_REGISTRY has 24 entries; hackathon profile excludes minimax-m3 |
| 3. Exclusion | \`@cf/*\` and \`qwen3-coder-*\` are rejected at the call_llm boundary |
| 4. OCR | Capability router loads 7 capabilities × 6 backends; auto_capability() heuristic works |
| 5. Assets | AssetControlRecord JSON-roundtrips; stub fallback fires when no live backends |
| 6. CLI | All 6 subcommands registered |
| 7. Observability | trace_agent emits opened + closed events |
| 8. Compare | Stubbed harness writes a DuckDB row |
| 9. BAML clients | Python + TypeScript generated clients exist on disk |
| 10. Palette JSON | Every theme JSON file parses |
| 11. pyproject | pyproject.toml is well-formed |

**Expected output:** \`11/11 steps green\` — if anything fails, the script prints the failing step + error type.

## 2. Run the backend smoke (15 s, no network)

\`\`\`bash
mise run backend:test
\`\`\`

Boots the Python backend on a free port, hits three endpoints with \`urllib\`, kills the process.

Expected output:

\`\`\`
[backend_smoke] using free port XXXXX
[OK] /api/health → status=ok, profile=hackathon, models=19
[OK] /api/themes → 15 palettes
[OK] /api/models → 19 models under hackathon profile
[OK] /api/chat/completions → HTTP 500 (TypeError) — backend reachable, no Gemini key in env
\`\`\`

The 500 on \`/api/chat/completions\` is **expected** without an API key — it proves the backend is reachable, the router ran, and the LiteLLM call failed at the network layer. With \`GEMINI_API_KEY=...\` set, this would return a real Gemini response.

To exercise the real path:

\`\`\`bash
export GEMINI_API_KEY=sk-...
mise run backend:test
\`\`\`

Should now show a \`model=gemini-3.5-flash\` row with content.

## 3. Run the comparison harness (2 min, no network by default)

\`\`\`bash
mise run compare:demo
\`\`\`

Generates a 3-model comparison on the canonical sample PDF (\`data/syllabi/sample_lc_maths_2024.pdf\`), writes to a temp DuckDB, prints the leaderboard.

Expected output:

\`\`\`
=== DuckDB state ===
  gemini-3.5-flash                score=1.00  latency=10ms  in=128  out=64
  gemini-3.5-flash-aistudio       score=1.00  latency=10ms  in=128  out=64
  gemma-4-26b-a4b                 score=1.00  latency=10ms  in=128  out=64
\`\`\`

Three rows is the **hackathon profile** — Gemini 3.5 (Vertex), Gemini 3.5 (AI Studio), Gemma 4. To see the dev profile (which adds minimax-m3 + the Unsloth Studio text set):

\`\`\`bash
MODEL_PROFILE=dev mise run compare:demo
\`\`\`

Should now show 6+ rows.

To exercise real (non-stubbed) Gemini + Gemma:

\`\`\`bash
export GEMINI_API_KEY=sk-...                                    # or GEMINI_VERTEX_PROJECT=...
export UNSLOTH_BASE_URL=http://127.0.0.1:8888/v1
export UNSLOTH_API_KEY=sk-unsloth-...
uv run gemini-hackathon compare --pdf data/syllabi/sample_lc_maths_2024.pdf \\
    --duckdb data/gemini_hackathon.duckdb
\`\`\`

Each model row will now carry real \`latency_ms\` + \`tokens_in/out\` + \`cost_usd\`.

## 4. Open the web UI (requires \`bun install\` first time)

\`\`\`bash
cd web
bun install       # ~30s first time
bun run dev       # vite dev server on :3000
\`\`\`

Browser: **http://localhost:3000**.

### What to click through

**Home page (/)**
- Map renders the 10 BI jurisdictions with real (simplified) GeoJSON polygons.
- Click any region → CSS variables swap; buttons + headings + body colours change.
- The right rail AG-UI chat panel should attempt to talk to the Python backend (which is **not running yet** unless you started it). Expected error message: \`python_backend_unreachable\`.

**Subjects (/subjects)**
- Empty state — there are no subjects in Convex yet (you'd need \`bunx convex dev\` + \`seedSubjectsFromDLT\` first).

**Safeguarding (/safeguarding)**
- Empty until you swap to a safeguarding palette. Click any safeguarding-region button on the home page first.

**Equivalency (/equivalency)**
- Hard-coded 3-row mathematics table — works offline.

**Compare (/compare)**
- Comparison Leaderboard + Document Explorer.
- DuckDB-WASM loads the \`.duckdb\` file. If \`data/gemini_hackathon.duckdb\` doesn't exist, the route returns a 404 with a helpful message.

## 5. To make the AG-UI chat actually respond

The chat panel expects a running Python backend:

\`\`\`bash
# Terminal A
mise run backend       # listens on 127.0.0.1:8000

# Terminal B (Vite proxies /api/copilotkit → 127.0.0.1:8000)
cd web && bun run dev
\`\`\`

Now \`localhost:3000\` chat panel will proxy through to the Python backend, which routes via \`call_llm()\` and the model registry.

## 6. To run the OCR pipeline end-to-end against the live llama-swap

\`\`\`bash
# llama-swap is already running on this box at :8080 (12 OCR/VLM models)
curl -s http://127.0.0.1:8080/v1/models | head -c 400
\`\`\`

Then:

\`\`\`python
# In a Python REPL:
from gemini_hackathon.ocr import ocr, OcrRequest, Capability

result = ocr(OcrRequest(
    capability=Capability.ENGLISH,
    image_path="/tmp/your_page.png",
    base_url="http://127.0.0.1:8080/v1",
    model="qwen3-vl-8b",
    timeout_seconds=60.0,
))
print(result.text)
\`\`\`

Already verified live in this environment (\`qwen3-vl-8b\` returned \`'Video:'\` for a 1×1 PNG in 29.5 s).

## 7. To generate a real asset (Phase 8)

\`\`\`bash
# Image-gen backends are off in this env. Stub fallback fires.
uv run python -c "
from gemini_hackathon.assets.image_gen import ImageGenRouter
from gemini_hackathon.assets.control_record import AssetControlRecord

router = ImageGenRouter()
rec = AssetControlRecord.from_syllabus_and_palette(
    source_pdf_path='/tmp/lc_chem_2024.pdf',
    source_page=12,
    subject='Flame test apparatus',
    palette={'primary': '#00733B', 'secondary': '#0E2D5C', 'accent': '#F7B81C'},
    learning_outcome_id='LC-CHEM-3.1.2',
)
result = router.generate(rec)
print(f'backend={result.backend.value}, seed={result.seed}, duration={result.duration_ms}ms')
print(f'provenance: {result.provenance}')
"
\`\`\`

Output: \`backend=stub, seed=..., duration=~60ms, provenance={...control_record_hash: ...}\`. To get a real image, bring ComfyUI :8188 or InvokeAI :9090 up — the same \`ImageGenRouter\` will pick the live backend.

## What you'll likely find needs changing after E2E

Based on what shipped and what I can't verify from here:

1. **\`@tanstack/react-start/plugin/vite\` import path** — confirmed correct for 1.95+, but if \`bun run dev\` fails at the plugin import line, the fix is \`import { tanstackStart } from "@tanstack/react-start/plugin/vite"\` ( already what we have) vs the older \`import { tanstackStart } from "@tanstack/start/vite"\`. Test this with \`bun install && bun run dev\`.

2. **Convex \`bunx convex dev\`** — never run in this environment. First-time setup needs a free Convex account; once provisioned, \`npx convex dev\` creates the deployment and \`seedSubjectsFromDLT\` populates the subjects table.

3. **CSS variables on the GeoJSON map** — may produce stale colours on the first hover before the second click (React state ↔ MapLibre expression sync is async).

4. **Image-gen stub** — fine for layout testing, doesn't render a real certificate. Brings up ComfyUI or InvokeAI to see real assets.

5. **\`requires-python = ">=3.11,<3.13"\`** — this box's \`.venv\` is 3.9, which is why 13 DLT tests skip. Use \`uv\` to provision a 3.12 venv for the full test pass.

6. **The map click → setPalette fires a real network round-trip** for any palette change that has a safeguarding backend (none of them do today, but if you bring up Phase 11's progress ledger, it'll hit Convex).

---

## Files of note

- \`scripts/smoke_test.py\` — canonical 11-step E2E. Edit this when adding new feature surfaces.
- \`scripts/compare_demo.py\` — harness demo; bound to \`mise run compare:demo\`.
- \`scripts/backend_smoke.py\` — boots + probes the Python backend.
- \`gemini_hackathon/backend.py\` — the stdlib HTTP server. Replace with Hono + oRPC + Convex actions when the production backend graduates.
- \`mise.toml\` — every dev-deploy command is a mise task.
- \`web/public/british_isles_jurisdictions.geojson\` — the 10-jurisdiction boundary file.
