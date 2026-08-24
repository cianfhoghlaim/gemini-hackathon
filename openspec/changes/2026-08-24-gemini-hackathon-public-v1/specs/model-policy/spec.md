# Spec Delta: model-policy

This delta is applied by the openspec change
[`2026-08-24-gemini-hackathon-public-v1`](../proposal.md). It
describes the ADDED Requirements to the canonical
[`openspec/specs/model-policy/spec.md`](../../../../specs/model-policy/spec.md)
that this change adds.

## ADDED Requirements

### Requirement: Tier 1 minimax-m3 as primary

The system SHALL use **`minimax-m3`** (the canonical Cianfhoghlaim
primary model) as the **default, primary model** for every
`call_llm()` invocation in the `gemini_hackathon` codebase.

The LiteLLM router configuration SHALL declare `minimax-m3` as the
first entry in the `model_list`, with no `weight` override (i.e.
100% of normal traffic is routed to it).

Every BAML function in `baml_src/gemini_hackathon/` SHALL declare
`client "Primary"` which resolves to `minimax-m3` via the
LiteLLM router.

#### Scenario: Every call_llm() invocation defaults to minimax-m3

- **WHEN** the operator inspects the LiteLLM router config
- **THEN** `minimax-m3` SHALL be the first model in `model_list`
- **AND** it SHALL have the highest `weight` (default `1.0`)
- **AND** no `rpm` / `tpm` override SHALL route requests away from it

#### Scenario: BAML functions declare the Primary client

- **WHEN** the operator inspects any BAML file in `baml_src/gemini_hackathon/`
- **THEN** every `@function` declaration SHALL include
  `client "Primary"`
- **AND** the `Primary` client SHALL resolve to `minimax-m3`
  in the LiteLLM router

### Requirement: Tier 2 unsloth gemma-4-26B as fallback

The system SHALL use **`unsloth/gemma-4-26B-A4B-it-GGUF`** (the
local Llama.cpp-served Gemma 4 26B model, fine-tuned with Unsloth)
as the **fallback model** when `minimax-m3` is unavailable.

The fallback SHALL fire after ONE retry on `minimax-m3` (the
`num_retries=1` policy). When `minimax-m3` returns a 5xx error or
exceeds the 10-second per-request timeout, the LiteLLM router
SHALL fall through to `unsloth/gemma-4-26B-A4B-it-GGUF`.

The fallback model SHALL be served locally via `llama.cpp` with the
GGUF weights hosted at `huggingface.co/unsloth/gemma-4-26B-A4B-it-GGUF`.

#### Scenario: Tier 2 fires after Tier 1 fails

- **WHEN** the `minimax-m3` invocation returns a 503 error
- **THEN** the LiteLLM router SHALL automatically retry the
  invocation against `unsloth/gemma-4-26B-A4B-it-GGUF`
- **AND** SHALL emit a structlog event with `llm.tier=2` +
  `llm.fallback_reason="primary_5xx"`

#### Scenario: Tier 2 fires after Tier 1 times out

- **WHEN** the `minimax-m3` invocation exceeds 10 seconds
- **THEN** the LiteLLM router SHALL cancel the primary request
- **AND** SHALL retry against `unsloth/gemma-4-26B-A4B-it-GGUF`
- **AND** SHALL emit a structlog event with `llm.tier=2` +
  `llm.fallback_reason="primary_timeout"`

### Requirement: Tier 3 vertex_ai/gemini-3.5-flash as final fallback

The system SHALL use **`vertex_ai/gemini-3.5-flash`** (Google Cloud
Vertex AI's Gemini 3.5 Flash model) as the **final fallback** when
both `minimax-m3` and `unsloth/gemma-4-26B-A4B-it-GGUF` are
unavailable.

The Vertex AI fallback SHALL fire after ONE retry on Tier 2 (the
same `num_retries=1` policy applied per tier). The Vertex AI
credentials SHALL be sourced from the `GOOGLE_APPLICATION_CREDENTIALS`
environment variable per the Google Cloud auth contract.

The Vertex AI model SHALL only be invoked when both Tier 1 and Tier 2
have failed (the LiteLLM router's `fallbacks` chain handles this
automatically).

#### Scenario: Tier 3 fires after Tier 2 fails

- **WHEN** the `minimax-m3` invocation returns a 5xx error AND
  the `unsloth/gemma-4-26B-A4B-it-GGUF` invocation returns a
  connection error
- **THEN** the LiteLLM router SHALL retry the invocation against
  `vertex_ai/gemini-3.5-flash`
- **AND** SHALL emit a structlog event with `llm.tier=3` +
  `llm.fallback_reason="primary_5xx+secondary_unreachable"`

#### Scenario: Vertex AI credentials are sourced from GOOGLE_APPLICATION_CREDENTIALS

- **WHEN** the LiteLLM router initialises the `vertex_ai/gemini-3.5-flash` client
- **THEN** it SHALL read the service-account JSON path from the
  `GOOGLE_APPLICATION_CREDENTIALS` environment variable
- **AND** SHALL raise a `MissingCredentialsError` if the variable
  is not set

### Requirement: Cloudflare Workers AI explicitly excluded

The system SHALL **NOT** use any Cloudflare Workers AI model
(`@cf/meta/llama-3.1-8b-instruct`, `@cf/google/gemma-7b-it`,
`@cf/mistral/mistral-7b-instruct-v0.1`, etc.) for any
`call_llm()` invocation.

The exclusion is enforced by **absence**: the Cloudflare Workers AI
provider SHALL NOT appear in the LiteLLM router's `model_list` or
the `litellm.router` configuration.

The exclusion rationale (cost, vendor lock-in, inconsistent quality)
SHALL be documented at `docs/MODEL_POLICY.md`.

#### Scenario: No Cloudflare Workers AI model is configured

- **WHEN** the operator inspects the LiteLLM router config
- **THEN** no model name SHALL match the `@cf/...` prefix
- **AND** `litellm.Router(model_list=...)` SHALL NOT include
  any `@cf/meta/*`, `@cf/google/*`, or `@cf/mistral/*` entry

#### Scenario: A request for a @cf/ model raises a clear error

- **WHEN** the developer accidentally configures
  `litellm.completion(model="@cf/meta/llama-3.1-8b-instruct", ...)`
- **THEN** the LiteLLM library SHALL raise a `BadRequestError`
  with the message `"Model @cf/meta/llama-3.1-8b-instruct is
  explicitly excluded by the gemini_hackathon model policy"`
- **AND** SHALL NOT silently fall back to a different `@cf/*` model

### Requirement: Qwen3-coder models explicitly excluded

The system SHALL **NOT** use any Qwen3-coder model
(`qwen3-coder-32b-instruct`, `qwen3-coder-14b-instruct`, etc.)
for any `call_llm()` invocation in the `gemini_hackathon` codebase.

The exclusion rationale (coding-tuned models do not suit the
pedagogical use case: they over-format prose, hallucinate code
comments inside natural-language answers, and prioritise
completion accuracy over factual recall) SHALL be documented at
`docs/MODEL_POLICY.md`.

#### Scenario: No Qwen3-coder model is configured

- **WHEN** the operator inspects the LiteLLM router config
- **THEN** no model name SHALL match the `qwen3-coder-*` prefix
- **AND** no BAML function SHALL declare a `client` that resolves
  to a Qwen3-coder model

#### Scenario: A request for a Qwen3-coder model raises a clear error

- **WHEN** the developer accidentally configures
  `litellm.completion(model="qwen3-coder-32b-instruct", ...)`
- **THEN** the LiteLLM library SHALL raise a `BadRequestError`
  with the message `"Model qwen3-coder-32b-instruct is explicitly
  excluded by the gemini_hackathon model policy"`
- **AND** SHALL NOT silently fall back to a different Qwen3-coder
  variant

### Requirement: structlog captures which tier was used

The system SHALL emit a **structured log event** for every
`call_llm()` invocation that captures which tier served the
request.

The log event SHALL include the following fields:

- `llm.tier` (string, `"1"` / `"2"` / `"3"`)
- `llm.model` (string, the resolved model name)
- `llm.latency_ms` (integer, the request latency in milliseconds)
- `llm.fallback_reason` (string, optional, present when `tier > "1"`)
- `llm.tokens_in` / `llm.tokens_out` (integer)
- `llm.cost_usd` (float, optional, populated when the model has
  known pricing)

The log event SHALL be emitted via `structlog.get_logger().info()`
with the event name `"llm.invocation"`.

The `llm.tier` field SHALL be queryable in Langfuse (via the
Langfuse structlog integration) so that operators can see the
distribution of tier-1 / tier-2 / tier-3 invocations over time.

#### Scenario: A successful Tier 1 invocation emits the correct event

- **WHEN** `call_llm(messages=[...])` succeeds on `minimax-m3`
- **THEN** the structlog event SHALL have:
  - `event="llm.invocation"`
  - `llm.tier="1"`
  - `llm.model="minimax-m3"`
  - `llm.latency_ms=<actual latency>`
- **AND** SHALL NOT include `llm.fallback_reason`

#### Scenario: A Tier 2 fallback invocation emits the correct event

- **WHEN** `call_llm(messages=[...])` falls through to
  `unsloth/gemma-4-26B-A4B-it-GGUF` after a Tier 1 timeout
- **THEN** the structlog event SHALL have:
  - `event="llm.invocation"`
  - `llm.tier="2"`
  - `llm.model="unsloth/gemma-4-26B-A4B-it-GGUF"`
  - `llm.fallback_reason="primary_timeout"`
  - `llm.latency_ms=<actual latency>`

#### Scenario: Langfuse captures the tier distribution

- **WHEN** the operator opens the Langfuse dashboard for the
  `gemini_hackathon` project
- **THEN** they SHALL see the `llm.tier` dimension with the
  distribution of tier-1 / tier-2 / tier-3 invocations
- **AND** SHALL be able to filter traces by `llm.tier` value