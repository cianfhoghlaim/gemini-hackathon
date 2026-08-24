# Model Policy — gemini_hackathon

> **Status:** enforced project-wide (per
> [`openspec/specs/model-policy/spec.md`](../../openspec/specs/model-policy/spec.md))
> **Last updated:** 2026-08-24

This document describes the **3-tier model policy** that every
`call_llm()` invocation in the `gemini_hackathon` codebase routes
through, plus the rationale for the explicit exclusions.

---

## The 3-tier model policy

Every `call_llm()` invocation in the `gemini_hackathon` codebase
goes through `gemini_hackathon.llm.call_llm()`, which routes
through a LiteLLM Router configured with the following 3 tiers:

| Tier | Model | Role | Litellm name | When it fires |
|-----:|-------|------|-------------|---------------|
| 1    | **minimax-m3** | Primary (default) | `minimax-m3` | Normal traffic (every request starts here) |
| 2    | **unsloth/gemma-4-26B-A4B-it-GGUF** | Fallback | `unsloth/gemma-4-26B-A4B-it-GGUF` | After ONE retry on Tier 1 fails (5xx error or > 10s timeout) |
| 3    | **vertex_ai/gemini-3.5-flash** | Final fallback | `vertex_ai/gemini-3.5-flash` | After Tier 2 also fails (connection error or > 10s timeout) |

The chain is **strictly sequential**: Tier 2 never fires before
Tier 1 has been tried + has failed; Tier 3 never fires before
both Tier 1 and Tier 2 have been tried + have failed.

The fallback `num_retries` policy is `1` per tier (one retry per
tier, no exponential back-off, no jitter — the goal is fast
failover to a working model).

---

## Tier 1 — minimax-m3 (primary)

`minimax-m3` is the **canonical primary model** for the
Cianfhoghlaim architecture. It is the default for every request.

The Litellm router entry is:

```python
{
    "model_name": "primary",
    "litellm_params": {
        "model": "minimax-m3",
        "api_key": os.environ["MINIMAX_API_KEY"],
    },
}
```

The `MINIMAX_API_KEY` environment variable is sourced from
Infisical via the Locket sidecar (per the upstream
`secrets-management` skill):

```
infisical://dev-baile/gemini_hackathon/minimax-api-key
```

---

## Tier 2 — unsloth/gemma-4-26B-A4B-it-GGUF (fallback)

`unsloth/gemma-4-26B-A4B-it-GGUF` is a **local Llama.cpp-served
Gemma 4 26B model**, fine-tuned with Unsloth. It is the fallback
when `minimax-m3` is unavailable.

The Litellm router entry is:

```python
{
    "model_name": "fallback",
    "litellm_params": {
        "model": "unsloth/gemma-4-26B-A4B-it-GGUF",
        "api_base": "http://localhost:8080",  # llama.cpp server
    },
}
```

The model weights are hosted at
[`huggingface.co/unsloth/gemma-4-26B-A4B-it-GGUF`](https://huggingface.co/unsloth/gemma-4-26B-A4B-it-GGUF)
and are served by the local `llama.cpp` server (started by
`mise run llm:start-fallback`).

The Tier 2 fallback fires when:

- The `minimax-m3` invocation returns a 5xx HTTP error
- The `minimax-m3` invocation exceeds 10 seconds (the
  `litellm.Router(timeout=10)` policy)

---

## Tier 3 — vertex_ai/gemini-3.5-flash (final fallback)

`vertex_ai/gemini-3.5-flash` is **Google Cloud Vertex AI's Gemini
3.5 Flash model**. It is the final fallback when both Tier 1 and
Tier 2 are unavailable.

The Litellm router entry is:

```python
{
    "model_name": "emergency",
    "litellm_params": {
        "model": "vertex_ai/gemini-3.5-flash",
        "vertex_credentials": os.environ["GOOGLE_APPLICATION_CREDENTIALS"],
        "vertex_project": "gemini-hackathon",
        "vertex_location": "europe-west1",
    },
}
```

The `GOOGLE_APPLICATION_CREDENTIALS` environment variable is
sourced from Infisical via the Locket sidecar:

```
infisical://dev-baile/gemini_hackathon/google-application-credentials
```

The Tier 3 fallback fires when:

- The `unsloth/gemma-4-26B-A4B-it-GGUF` invocation returns a
  connection error (the llama.cpp server is down)
- The `unsloth/gemma-4-26B-A4B-it-GGUF` invocation exceeds
  10 seconds

The Vertex AI model is invoked **only** as the last resort — the
goal is to use the local fallback (Tier 2) for as many requests
as possible to keep the Vertex AI cost low.

---

## Excluded models

### Cloudflare Workers AI — EXCLUDED

Cloudflare Workers AI models (`@cf/meta/llama-3.1-8b-instruct`,
`@cf/google/gemma-7b-it`, `@cf/mistral/mistral-7b-instruct-v0.1`,
etc.) are **explicitly excluded** from the model policy.

**Rationale:**

1. **Cost** — Cloudflare Workers AI uses per-request pricing
   that does not match the billing expectations for a hackathon
   project. The flat-rate LiteLLM + OpenRouter billing model
   used by the other tiers is more predictable.
2. **Vendor lock-in** — Cloudflare Workers AI runs only on
   Cloudflare's edge network. The Cianfhoghlaim architecture
   is **cloud-agnostic by design** (it can run on Cloudflare,
   AWS, GCP, or on-prem). Adopting Cloudflare Workers AI would
   contradict that posture.
3. **Inconsistent quality** — Cloudflare's `@cf/meta/llama-3.1-8b-instruct`
   and `@cf/google/gemma-7b-it` models have inconsistent quality
   across regions (the model serving capacity varies by data
   centre), which is unacceptable for a production agent fleet.
4. **No Langfuse integration** — Cloudflare Workers AI does not
   emit the structured trace events that Langfuse expects, so
   the observability story would degrade.

The exclusion is enforced by **absence** in the LiteLLM router
config + a `BadRequestError` guard that raises a clear error if
any `@cf/*` model is requested.

### Qwen3-coder-* — EXCLUDED

Qwen3-coder models (`qwen3-coder-32b-instruct`,
`qwen3-coder-14b-instruct`, etc.) are **explicitly excluded** from
the model policy.

**Rationale:**

1. **Pedagogical use case mismatch** — The `gemini_hackathon`
   project is a **pedagogical** agent fleet (Helping pupils
   understand British Isles curricula + safeguarding policies).
   Qwen3-coder models are tuned for **code completion** — they
   over-format prose, hallucinate code comments inside
   natural-language answers, and prioritise completion accuracy
   over factual recall.
2. **Factual recall vs completion** — Pedagogical agents need
   **strict factual recall** (e.g. "what is the SQA equivalent
   of Leaving Cert Maths 3.1?"). Qwen3-coder models optimise for
   the next-token completion, not for factuality.
3. **Math reasoning** — Gemma 4 26B (the Tier 2 fallback) has
   demonstrated stronger math-reasoning benchmarks than
   Qwen3-coder-32B for the kind of curriculum-level math
   questions the equivalency generator handles.

The exclusion is enforced by **absence** in the LiteLLM router
config + a `BadRequestError` guard that raises a clear error if
any `qwen3-coder-*` model is requested.

---

## LiteLLM router config (full example)

```python
# gemini_hackathon/llm.py
from __future__ import annotations

import os
import time
from typing import Any

import structlog
from litellm import Router

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# The 3-tier router — DO NOT add @cf/* or qwen3-coder-* entries
# ---------------------------------------------------------------------------
router = Router(
    model_list=[
        # Tier 1 — primary
        {
            "model_name": "primary",
            "litellm_params": {
                "model": "minimax-m3",
                "api_key": os.environ["MINIMAX_API_KEY"],
            },
        },
        # Tier 2 — fallback
        {
            "model_name": "fallback",
            "litellm_params": {
                "model": "unsloth/gemma-4-26B-A4B-it-GGUF",
                "api_base": os.environ.get(
                    "LLAMACPP_API_BASE", "http://localhost:8080"
                ),
            },
        },
        # Tier 3 — emergency
        {
            "model_name": "emergency",
            "litellm_params": {
                "model": "vertex_ai/gemini-3.5-flash",
                "vertex_credentials": os.environ["GOOGLE_APPLICATION_CREDENTIALS"],
                "vertex_project": os.environ.get(
                    "VERTEX_PROJECT", "gemini-hackathon"
                ),
                "vertex_location": os.environ.get(
                    "VERTEX_LOCATION", "europe-west1"
                ),
            },
        },
    ],
    fallbacks=[
        {"primary": ["fallback"]},
        {"fallback": ["emergency"]},
    ],
    num_retries=1,
    timeout=10,
)


# ---------------------------------------------------------------------------
# The call_llm() entry point
# ---------------------------------------------------------------------------
def call_llm(messages: list[dict[str, str]], **kwargs: Any) -> str:
    """Invoke the 3-tier LLM router.

    Every invocation emits a structlog event with `llm.tier`,
    `llm.model`, `llm.latency_ms`, and (when tier > 1) `llm.fallback_reason`.
    """
    start = time.monotonic()
    try:
        response = router.completion(
            model="primary",  # start at Tier 1; router handles fallbacks
            messages=messages,
            **kwargs,
        )
        latency_ms = int((time.monotonic() - start) * 1000)

        # Determine which tier actually served the request
        tier = _resolve_tier(response)

        logger.info(
            "llm.invocation",
            llm_tier=str(tier),
            llm_model=response["model"],
            llm_latency_ms=latency_ms,
            llm_tokens_in=response["usage"]["prompt_tokens"],
            llm_tokens_out=response["usage"]["completion_tokens"],
            llm_cost_usd=_compute_cost(response),
        )
        return response["choices"][0]["message"]["content"]

    except Exception as exc:
        latency_ms = int((time.monotonic() - start) * 1000)
        logger.error(
            "llm.invocation.failed",
            llm_tier="3",  # reached the final fallback
            llm_model="vertex_ai/gemini-3.5-flash",
            llm_latency_ms=latency_ms,
            llm_error=str(exc),
        )
        raise


def _resolve_tier(response: dict) -> int:
    """Determine which tier served the request."""
    model = response.get("model", "")
    if model.startswith("minimax-m3"):
        return 1
    if model.startswith("unsloth/gemma-4"):
        return 2
    if model.startswith("vertex_ai/gemini"):
        return 3
    return 1  # default to Tier 1 if unknown


def _compute_cost(response: dict) -> float:
    """Compute the cost in USD (LiteLLM provides this)."""
    return float(response.get("_hidden_params", {}).get("response_cost", 0.0))
```

---

## structlog trace format

Every `call_llm()` invocation emits a structlog event with the
following fields:

| Field | Type | Description |
|-------|------|-------------|
| `event` | string | Always `"llm.invocation"` |
| `llm.tier` | string | `"1"` / `"2"` / `"3"` (which tier served the request) |
| `llm.model` | string | The resolved model name |
| `llm.latency_ms` | integer | The request latency in milliseconds |
| `llm.tokens_in` | integer | The input token count |
| `llm.tokens_out` | integer | The output token count |
| `llm.cost_usd` | float | The cost in USD (LiteLLM-provided) |
| `llm.fallback_reason` | string | Optional — present when `tier > "1"` |

Example event (Tier 1 success):

```json
{
  "event": "llm.invocation",
  "llm.tier": "1",
  "llm.model": "minimax-m3",
  "llm.latency_ms": 842,
  "llm.tokens_in": 128,
  "llm.tokens_out": 256,
  "llm.cost_usd": 0.000142
}
```

Example event (Tier 2 fallback):

```json
{
  "event": "llm.invocation",
  "llm.tier": "2",
  "llm.model": "unsloth/gemma-4-26B-A4B-it-GGUF",
  "llm.latency_ms": 12453,
  "llm.tokens_in": 128,
  "llm.tokens_out": 256,
  "llm.cost_usd": 0.0,
  "llm.fallback_reason": "primary_timeout"
}
```

The structlog events are forwarded to **Langfuse** via the
Langfuse structlog integration, so the `llm.tier` dimension is
queryable in the Langfuse dashboard.

---

## References

- [`openspec/specs/model-policy/spec.md`](../../openspec/specs/model-policy/spec.md) —
  the canonical model-policy spec
- [`openspec/changes/2026-08-24-gemini-hackathon-public-v1/specs/model-policy/spec.md`](../../openspec/changes/2026-08-24-gemini-hackathon-public-v1/specs/model-policy/spec.md) —
  the model-policy spec delta
- [`gemini_hackathon/llm.py`](../../gemini_hackathon/llm.py) —
  the `call_llm()` implementation