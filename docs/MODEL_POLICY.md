# Model Policy — gemini_hackathon

> **Status:** enforced project-wide (per
> [`openspec/changes/2026-08-24-gemini-hackathon-public-v1/specs/model-policy/spec.md`](../../openspec/changes/2026-08-24-gemini-hackathon-public-v1/specs/model-policy/spec.md))
> **Last updated:** 2026-08-25 (Phase 0 — dual-profile registry)

## TL;DR

Two profiles, one surface. The **hackathon** profile is the only one docs,
the UI, the CLI, and the submission materials ever reference. The **dev**
profile exists for the comparison harness and stays out of public view by
construction (see `public_model_roster()`).

| Tier | hackathon profile | dev profile (extra only) |
|---|---|---|
| 1 (primary) | `gemini-3.5-flash` — Vertex AI (default) or AI Studio | + the same model served via AI Studio |
| 2 (fallback) | `unsloth/gemma-4-26B-A4B-it-GGUF` via Unsloth Studio :8888 | + a dev-only gemma copy |
| 3 (extra) | — | `minimax-m3`, `qwen3.8-27b`, `deepseek-v4-flash`, `kimi-k2.6` |

Hard-rejected: `@cf/*` (Cloudflare Workers AI) and any `qwen3-coder-*` prefix.
These cannot be reached at the call boundary — `_assert_model_allowed` in
`call_llm.py` raises `ModelExcludedError` before the request is dispatched.

---

## How `MODEL_PROFILE` works

`gemini_hackathon/call_llm.py` reads `MODEL_PROFILE` (default `hackathon`) and
selects a tier tuple. Each tier is `(family, role)` and resolves via
`MODEL_REGISTRY.resolve(family, role, profile=...)`. Adding a new model
is a **registry change** (`gemini_hackathon/model_registry.py`), not a router
change — this is the hard rule for keeping model strings out of three
places.

`MODEL_REGISTRY.resolve()` is first-match-wins over insertion order. The
canonical entry for each `(family, role)` pair MUST be declared first
within its family. Adding a sibling entry below the canonical one would
not "win" — only profile-gated entries that the filter considers will be
discovered.

`public_model_roster()` ignores `MODEL_PROFILE` and reads the **hackathon**
profile unconditionally. If a dev-only entry somehow ends up in this list,
it raises `ModelPolicyError`. Docs generators, the UI's model selector,
and the CLI's `--roster` output must read from here and nowhere else.

```python
from gemini_hackathon.model_registry import (
    MODEL_REGISTRY, model_for, public_model_roster,
)
entries = public_model_roster()              # always hackathon profile
gemini   = model_for("text_llm", "default")    # respects MODEL_PROFILE
```

---

## Where each backend lives

| Backend | URL pattern | Status | Notes |
|---|---|---|---|
| **Vertex AI** (Tier 1 default) | regional, ADC, no key | production-shape | Requires `GOOGLE_CLOUD_PROJECT` + ADC; counted as the GCP infrastructure service for the hackathon mandatory-tech rule |
| **AI Studio** (Tier 1 fallback) | `https://generativelanguage.googleapis.com/v1beta/...` | any | Requires `GEMINI_API_KEY`; auto-selected when Vertex creds are missing and AI Studio creds are present |
| **Unsloth Studio** (Tier 2) | host process `:8888/v1` | live | A HOST process, NOT a Docker service. OpenAI-compatible + Anthropic-compatible. From Docker, reach via `http://host.docker.internal:8888/v1` (see `extra_hosts` in compose) |
| **llama-swap** (ocr_vision) | `:8080/v1` | live | 12 OCR/VLM models. Per-capability dispatch lives in `gemini_hackathon/ocr/router.py` |
| **InvokeAI** (image_gen quality) | `:9090/v1` | down in this env | Adapter has a deterministic-seed stub fallback |
| **ComfyUI** (image_gen provenance / FIBO) | `:8188` | down in this env | Adapter has a deterministic-seed stub fallback |
| **minimax** (dev Tier 3) | `https://api.minimax.io/v1` | dev-only | `minimax-m3` |

The `ollama` service that earlier this repo`s docker-compose.yml` carried
was deleted in Phase 1. Unsloth Studio is the only Gemma-family route —
it serves the same weights as ollama would have, with a model registry
that does not lie about which key is on the wire.

---

## Deployment matrix

Three values of `UNSLOTH_BASE_URL` cover every deployment. The compose file
sets the docker default; the host value overrides for `bun run dev`
locally; the hackathon value comes from the GCE VM env at submit time.

| Where | `UNSLOTH_BASE_URL` |
|---|---|
| Host dev (terminal) | `http://127.0.0.1:8888/v1` |
| Docker dev (`bun run dev` inside compose) | `http://host.docker.internal:8888/v1` (set in compose, `extra_hosts: ["host.docker.internal:host-gateway"]`) |
| GCE hackathon VM | `http://<GCE_VM_INTERNAL_IP>:8888/v1` (placeholder, set in deploy env) |

Never invent a hostname or project id. The compose`s `${UNSLOTH_BASE_URL:-http://host.docker.internal:8888/v1}`
substitution preserves the dev default and lets every other deployment override.

---

## Cost ceiling per session

Each `Session` carries `cost_cap_usd: float = 0.10`. Before each LLM call,
`call_llm.py` sums the session accumulated cost; if `> cost_cap_usd`,
it downgrades from Tier 1 (Gemini 3.5) to Tier 2 (Gemma 4) automatically.
The chat panel header shows the running total — judges see cost discipline
in the live demo, not just in the docs.

---

## Observability

Every `call_llm()` invocation emits a structlog event `llm.invocation`
carrying `llm.tier`, `llm.role`, `llm.model_key`, `llm.model_alias`,
`llm.backend`, `llm.latency_ms`, `llm.tokens_in`, `llm.tokens_out`,
`llm.fallback_reason`, and the active `model_profile`. When Langfuse is
configured (`LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY`), each event is
also forwarded to a Langfuse trace. The `/observability` route in the web
app surfaces the Langfuse dashboard via iframe.

---

## Adding a model (the hard rule)

1. Open `gemini_hackathon/model_registry.py`.
2. Find the family (`text_llm`, `ocr_vision`, `image_gen`).
3. Add a new `ModelRegistryEntry` in the correct position. **Canonical
   entries come first** in the family; profile-gated alternates come after.
4. Set `profile="hackathon"` for anything docs/UI/submission will read,
   or `profile="dev"` for harness-only entries, or `profile="both"` if it
   should appear under both.
5. Run `uv run pytest tests/test_model_policy_exclusion.py -q` and
   `uv run pytest tests/test_call_llm.py -q`.
6. The smoke test `scripts/smoke_test.py` step 3 ("Exclusion guard") and
   step 11 ("pyproject metadata sanity") both still pass.

Never hardcode model strings in `call_llm.py`, in a BAML file, or in the
web app. They must always come from the registry via
`model_for(family, role, profile=...)`.

---

## Why this design

The hackathon rules ask every project to use:
- **Gemini 3.5** via Vertex AI or the Gemini API (mandatory)
- **at least one Google Agent Framework** (ADK — the `LlmAgent` is in `agents/adk_gemini_agent.py`)
- **at least one Google Cloud infrastructure service** (Vertex AI counts)

This policy satisfies all three with `gemini-3.5-flash` on Tier 1 + Vertex AI
on Tier 1 default. Gemma 4 26B-A4B on Tier 2 qualifies for the +0.2 bonus
for "integrating Google AI models such as Gemma" (the rule is permissive —
Gemma is a Google AI model). Both Tier 1 and Tier 2 are surfaced in the
UI model selector; the dev-profile Tier 3 (`minimax-m3`) is NOT surfaced
because `public_model_roster()` ignores the dev profile.

---

## Secrets hygiene

The Unsloth key format is `sk-unsloth-...`, stored at Infisical
`dev-baile/unsloth/api_key`. `call_llm.py` uses an **allow-list** of safe
env keys in any logging/dump path — never a deny-list. A previous agent in
this project shipped a deny-list that matched `KEY` but not `TOKEN`, and a
live token leaked into a log file. Allow-list only.
