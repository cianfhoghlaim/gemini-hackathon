# gemini_hackathon — One platform for the British Isles

> **Google All Things Agentic Hackathon submission.** Built with
> **Gemini 3.5** (Vertex AI) + **Gemma 4 26B-A4B** (Unsloth Studio) + the
> **Google ADK** agent framework. Deployed on **Google Cloud Run**.
> One codebase, **8 subnations** (5 live + 3 future expansion), **3
> audiences** (student / parent / teacher).

[![MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)
[![CI](https://img.shields.io/badge/CI-GitHub_Actions-blue)](.github/workflows/ci.yml)

---

## The British Isles, one platform

> A student in Ireland, a parent in Wales, a teacher in Northern
> Ireland — they all need a different view of the world, but they
> all benefit from the same platform. The theming is the user
> identity, not a colour picker. Same product, **3 audiences × 8
> subnations × 7 idea-agent capabilities**.

The 4 hackathon ideas:

| Idea | What it does | Surface |
|---|---|---|
| **Marking Grader Workflow** | Compares a student's answer to the per-jurisdiction marking scheme | `/agents` → `mark_answer` tool |
| **Adaptive Tutor** | Personalised tutoring grounded in the active subnation's palette + role + cycle + subjects | `/agents` chat |
| **Cross-Jurisdiction Equivalency Generator** | Given an Ireland LC Maths topic, finds the equivalent in England / Scotland / Wales / NI | `/find-resources` → `find_similar_resources` tool |
| **Curriculum Change Sensor** | Detects new syllabus PDFs / official source changes and re-runs the theming extraction | `/subjects` change-detection badge |

The 7 Fleet primitives (the Fortified Enterprise Fleet track's 4 pillars):

| Primitive | Maps to FEF pillar |
|---|---|
| `FleetGateway` | Agent Gateway (routing + policy) |
| `FleetIdentity` | Agent Identity (zero-trust access) |
| `FleetModelArmor` | Model Armor (prompt injection / PII guardrails) |
| `FleetObservability` | Agent Observability (audit logs + reasoning chain) |
| `FleetMemory` | Memory Bank (persistent cross-session context) |
| `FleetMcpCurriculum` | Agent Runtime (long-running async execution) |
| `FleetAguiBridge` | AG-UI streaming protocol bridge (agent → UI events) |

## Quick start (offline, no GCP keys required)

```bash
# 1. Verify the Python package offline
uv run python scripts/smoke_test.py
# → 11/11 steps green

# 2. Generate BAML clients + run BAML tests
uv run baml-cli generate
uv run baml-cli test

# 3. Boot the Python backend on a free port, hit /api/health, kill it
uv run python scripts/backend_smoke.py
# → /api/health + /api/themes + /api/models + /api/agents/find-resources all green

# 4. Run the Gemini-vs-Gemma4 comparison harness (writes to DuckDB)
uv run python scripts/compare_demo.py
# → 3 models compared, RAGAS score 1.0, DuckDB row written

# 5. Run the web UI (requires bun install first time)
cd web
bun install
bun run dev    # Vite on :3000
```

The 4 quick commands live in `mise.toml` — `mise run smoke` / `backend:test` / `compare:demo` / `web`.

## The per-user session

Every page in the app respects the active session's subnation. The
session binds:

- `subnation` — Ireland / England default; NI / Scotland / Wales available; Jersey / Guernsey / Isle of Man = future expansion pack
- `role` — student / parent / teacher (drives the home page quick actions)
- `cycle` — junior_cycle / leaving_cycle / gcse / a_level / national_5 / higher / advanced_higher
- `selectedSubjects` — drives the home page

Authentication is **BetterAuth + PocketID** in production, localStorage
in dev. The session is the user identity.

## What the demo video will show

A 4-min narrative:

> The British Isles is an archipelago of 8 distinct education systems.
> A student in Ireland, a parent in Wales, a teacher in Northern Ireland
> — they all need a different view of the world, but they all benefit
> from the same platform.
>
> We built one product that adapts to each. Ireland defaults. England
> defaults. Scotland, Wales, NI are live. Jersey, Guernsey, Isle of Man
> are the future expansion pack.
>
> The same chunking + indexing pipeline turns 148 official source PDFs
> into a single RAG corpus. An Irish Leaving Cert Maths student asks
> "find me English AQA mechanics papers that cover vectors" — and gets
> them, labelled with the NCCA outcome ID they relate to.
>
> The chat agent is a **Google ADK** agent with 5 tools. The backend is
> on **Google Cloud Run**. Every session is durable, multi-device,
> account-bound.
>
> Three audiences. Eight nations. Two default. One platform.

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the Mermaid diagram
and the full system architecture.

## The theming

13 palettes in `themes/` — 7 jurisdictions + 3 England boards + 5
safeguarding bodies. The theming is auto-resolved from the active
session's subnation. The agent's voice matches the awarding body's
typography + palette.

| Subnation | Awarding body | Primary | Default? |
|---|---|---|---|
| Ireland | NCCA | `#00733B` | ✓ |
| England | AQA + OCR + Pearson | `#00457C` | ✓ |
| Northern Ireland | CCEA | `#003478` | – |
| Scotland | SQA | `#003D7D` | – |
| Wales | WJEC | `#1F3A93` | – |
| Jersey | (future) | `#C8102E` | 🔒 |
| Guernsey | (future) | `#005EB8` | 🔒 |
| Isle of Man | (future) | `#003366` | 🔒 |

## The 2-tier model policy (hackathon profile)

```
Tier 1 (primary)  : gemini-3.5-flash       — Vertex AI (default) / AI Studio
Tier 2 (fallback) : gemma-4-26b-a4b        — Unsloth Studio :8888
```

**Bonus points**: Gemma 4 is a Google AI model — the +0.2 bonus for
"integrate Google AI models such as Gemma" applies.

Hard-rejected: `@cf/*` (Cloudflare Workers AI), `qwen3-coder-*`.

## What's verified live (this box)

| Service | URL | Status |
|---|---|---|
| Unsloth Studio | `127.0.0.1:8888` | OPEN |
| llama-swap (OCR/VLM) | `127.0.0.1:8080` | OPEN, 12 models |
| Langfuse | `127.0.0.1:3001` | OPEN |
| MLflow | `127.0.0.1:5050` | OPEN |
| marimo | `127.0.0.1:2718` | OPEN |
| Llama 3.1 8B | `127.0.0.1:11434` | OPEN |
| ComfyUI | `127.0.0.1:8188` | down (stub fallback) |
| InvokeAI | `127.0.0.1:9090` | down (stub fallback) |

## Tests

The `tests/` directory contains ~250 test functions across 24 modules.
The README's earlier `164 passed, 13 skipped` claim is stale; see
[`docs/KNOWN_ISSUES.md`](docs/KNOWN_ISSUES.md) for the 7 known failures
(5 pre-existing + 2 surfaced by the refactor). Per the August 2026
refactor agreement, test fixes are deferred to a post-hackathon pass;
the substantive work is the platform.

```bash
uv run pytest tests/ -q  # see docs/KNOWN_ISSUES.md for known failures
```

## License

MIT — see [LICENSE](LICENSE).
