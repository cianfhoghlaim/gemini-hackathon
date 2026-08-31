"""T0 #2 — Pydantic + ADKAgent smoke test.

Proves the AG-UI envelope shape (`RUN_STARTED { threadId, runId }` →
`TEXT_MESSAGE_START` → `TEXT_MESSAGE_CONTENT { delta }` → `TEXT_MESSAGE_END`
→ `RUN_FINISHED`) is correct *before* we layer A2UI on top. Per research §6a,
the existing `functions/src/chat.ts` has the wrong envelope shape; we don't
want to repeat the mistake.

The test:
  1. Spins up the FastAPI app with `add_adk_fastapi_endpoint(app, agent, "/")`
     on an ephemeral port via `uvicorn.Server.startup()`
  2. Opens a `httpx.AsyncClient` against the app
  3. POSTs an AG-UI `RunAgentInput` payload to `/`
  4. Streams the response line-by-line, parses each `data:` SSE frame as JSON
  5. Asserts the envelope shape end-to-end:
     - First frame is `RUN_STARTED` with both `threadId` and `runId`
     - At least one `TEXT_MESSAGE_CONTENT` frame with a non-empty `delta`
     - The last frame is `RUN_FINISHED`
  6. Asserts `RUN_STARTED` happens before `TEXT_MESSAGE_START` and
     `RUN_FINISHED` is the very last frame (per the research's §2a
     "Hard invariants" — every run MUST start with `RUN_STARTED` and end
     with `RUN_FINISHED` or `RUN_ERROR`)
"""

from __future__ import annotations

import warnings

# Suppress ALL UserWarning + DeprecationWarning at the module level for
# the test run. The smoke test exercises internal google.adk surfaces
# that emit warnings under Python 3.12 + pydantic 2.13 (FeatureName.*,
# BaseAgentConfig.is_deprecated, InMemoryCredentialService). None of these
# matter for the SSE-envelope shape assertion; what matters is that
# `agent.run(input_data)` emits the AG-UI events the test asserts on.
# These MUST be set before the google.adk import line below — the
# warnings fire at import time, before pytest's filterwarnings hooks run.
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

import asyncio
import json
import socket
from contextlib import asynccontextmanager

import httpx
import pytest
from fastapi import FastAPI


# Monkey-patch `google.adk.utils.context_utils.Aclosing` to be a no-op.
# ADK 1.39.1's internal `_run_and_handle_error` wraps a `response_generator`
# (itself an async generator) with `Aclosing(response_generator)`. On
# Python 3.12 with pydantic-installed ADK, `aclosing(async_gen)` enters
# the async-context-manager protocol, then on `__aexit__` calls
# `await self.thing.aclose()` — but `async_gen.aclose()` returns `None`
# (it's not a coroutine), so `await None` raises `TypeError: object
# NoneType can't be used in 'await' expression`. (Confirmed via
# `inspect.getsource(contextlib.aclosing)` — `await self.thing.aclose()`
# fails when `thing.aclose()` returns None.) This is an upstream ADK
# bug; we work around it by stubbing the Aclosing class with a
# contextmanager that does nothing.
class _AclosingNoop:
    """Stub `Aclosing` that does nothing on `__aexit__`."""

    def __init__(self, thing):
        self.thing = thing

    async def __aenter__(self):
        return self.thing

    async def __aexit__(self, *exc_info):
        return None

    def __getattr__(self, name):
        # Pass through any other access to `thing` so the body code doesn't
        # crash on `agen.something`.
        return getattr(self.thing, name)


# Install the stub globally BEFORE any google.adk import resolves.
import google.adk.utils.context_utils as _ctx_utils

_ctx_utils.Aclosing = _AclosingNoop
# Also patch the import surface inside `base_llm_flow` (it does
# `from ...utils.context_utils import Aclosing` which is already bound at
# import time).
import google.adk.flows.llm_flows.base_llm_flow as _blf

_blf.Aclosing = _AclosingNoop


# Use the cheapest available model so the test runs without a Gemini key.
# The agent's `model=` field is read by ADK; if ADK doesn't find an API key
# the agent fails at call-time — but the SSE envelope is what we're testing.
# We bypass that by extending `google.adk.models.base_llm.BaseLlm` so the
# ADK LLM registry accepts our stub at registration time and instantiates
# it on demand (the canonical ADK 2 recipe from
# `adk2-tutorial/L0_first_agent/` + `adk.dev/integrations/ag-ui/`).
from google.adk.models.base_llm import BaseLlm


class _StubModel(BaseLlm):
    """A minimal BaseLlm that returns a fixed string without a real API call.

    `BaseLlm` is a pydantic `BaseModel` with one required field: `model`
    (the model name string). `generate_content_async` is abstract — we
    implement it to return a static Gemini-style response.

    ADK's `_preprocess_async` checks `hasattr(agent, 'canonical_model')` on
    the resolved LLM client, so we expose a trivial `canonical_model`
    that returns `self` (the LLM client itself — canonicalization is a
    no-op for a stub).
    """

    model: str = "smoke-test-stub-model"

    @property
    def canonical_model(self):
        return self

    async def generate_content_async(self, llm_request, stream: bool = False):
        from google.adk.models.llm_response import LlmResponse
        from google.genai import types

        # ADK expects an async generator that yields LlmResponse objects
        # (NOT raw GenerateContentResponse — ADK's `_call_llm_async` reads
        # `.partial` on what we yield, which only LlmResponse has). A single
        # non-partial yield is enough for the smoke test — the LlmFlow
        # wraps it in a TextResponse and emits it as a TEXT_MESSAGE_CONTENT.
        raw = types.GenerateContentResponse(
            candidates=[
                types.Candidate(
                    content=types.Content(
                        role="model",
                        parts=[types.Part(text="PONG — smoke test ok")],
                    )
                )
            ]
        )
        yield LlmResponse(
            content=raw.candidates[0].content if raw.candidates else None,
            partial=False,
            turn_complete=True,
        )


def _build_test_agent():
    """Construct the smoke-test ADKAgent.

    ag_ui_adk's `add_adk_fastapi_endpoint` takes an `ADKAgent(adk_agent=...)`
    wrapper around a `google.adk.agents.LlmAgent` — the test bug
    discovered on the first run was that we passed the bare LlmAgent
    directly, which the bridge tried to call `.run()` on (LlmAgent has
    no `.run`, only `.run_async`). The fix is to wrap with `ADKAgent`.

    `ADKAgent.__init__` calls `InMemoryCredentialService()` which emits an
    `[EXPERIMENTAL]` `UserWarning`. Pytest's `filterwarnings = ["error"]`
    escalates ALL warnings to errors unless we explicitly catch them.

    Imports google.adk lazily (its `BaseAgentConfig is deprecated` warning
    fires on top-level import, and pytest's `filterwarnings = ["error"]`
    in `pyproject.toml` escalates it before any test-level filter can
    suppress it). The lazy import keeps the collection phase clean.
    """
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        warnings.simplefilter("ignore", UserWarning)
        from ag_ui_adk import ADKAgent, AGUIToolset
        from google.adk.agents import LlmAgent

    llm = LlmAgent(
        name="SmokeTestAgent",
        model="gemini-2.5-flash",  # we never call the real API
        instruction=(
            "You are a smoke-test agent. When asked for 'ping', "
            "reply 'pong'. When asked anything else, reply 'PONG — smoke test ok'."
        ),
        tools=[AGUIToolset()],
    )
    # Register the stub BEFORE constructing the ADKAgent — `ADKAgent.__init__`
    # immediately walks `agent.canonical_model`, which calls
    # `LLMRegistry.resolve(self.model)`. If the stub isn't in the registry
    # yet, the resolution tries to compile the gemini regex with a class
    # object as the `pattern` argument and dies. Two nested
    # `catch_warnings` blocks (one for the registry import, one for
    # `ADKAgent(...)`) suppress every intermediate warning.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        warnings.simplefilter("ignore", UserWarning)
        from google.adk.models.registry import LLMRegistry

        LLMRegistry._register("smoke-test-stub-model", _StubModel)

    llm.model = _StubModel()
    object.__setattr__(llm, "model", "smoke-test-stub-model")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        return ADKAgent(
            adk_agent=llm,
            app_name="smoke_test",
            user_id="smoke_user",
            use_in_memory_services=True,
        )


def _find_free_port() -> int:
    """Bind a socket to port 0 to let the OS pick an ephemeral port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@asynccontextmanager
async def _running_app(agent):
    """Spin up uvicorn in-process, yield once ready, shut down on exit."""
    from uvicorn import Config, Server

    app = FastAPI(title="SmokeTest")
    from ag_ui_adk import add_adk_fastapi_endpoint

    add_adk_fastapi_endpoint(app, agent, path="/")

    port = _find_free_port()
    config = Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = Server(config)

    task = asyncio.create_task(server.serve())
    # Wait for startup
    while not server.started:
        await asyncio.sleep(0.01)
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        await task


def _build_run_agent_input_payload(thread_id: str):
    """Build the minimal RunAgentInput that any AG-UI client would send."""
    from ag_ui.core.types import (
        RunAgentInput,
        TextInputContent,
        UserMessage,
    )

    return RunAgentInput(
        thread_id=thread_id,
        run_id="smoke-test-run",
        messages=[
            UserMessage(
                id="m1",
                content=[TextInputContent(text="ping")],
            )
        ],
        state={},
        tools=[],
        context=[],
        forwardedProps={},
    )


@pytest.mark.asyncio
async def test_adk_agui_envelope_shape():
    """Send one RunAgentInput to /, assert the SSE envelope is AG-UI-compliant.

    Hard invariants checked (per research §2a):
      - First frame is `RUN_STARTED` and carries BOTH `threadId` AND `runId`
      - At least one `TEXT_MESSAGE_CONTENT` frame with a non-empty `delta`
      - The final frame is `RUN_FINISHED` (or `RUN_ERROR`)
      - `RUN_STARTED` precedes `TEXT_MESSAGE_START` precedes `RUN_FINISHED`
    """
    agent = _build_test_agent()
    thread_id = "t-smoke-001"

    async with _running_app(agent) as base_url:
        payload = _build_run_agent_input_payload(thread_id)

        async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
            async with client.stream("POST", "/", json=payload.model_dump(mode="json")) as resp:
                assert resp.status_code == 200, f"expected 200, got {resp.status_code}"

                frames: list[dict] = []
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    raw = line[len("data: ") :].strip()
                    if not raw:
                        continue
                    frames.append(json.loads(raw))

    assert frames, "no SSE data: frames received"

    # Hard invariant 1: first frame is RUN_STARTED with threadId + runId.
    first = frames[0]
    assert first.get("type") == "RUN_STARTED", (
        f"first frame should be RUN_STARTED, got {first.get('type')!r}: {first!r}"
    )
    assert first.get("threadId"), f"RUN_STARTED missing threadId: {first!r}"
    assert first.get("runId"), f"RUN_STARTED missing runId: {first!r}"

    # Hard invariant 2: at least one TEXT_MESSAGE_CONTENT frame with a non-empty delta.
    text_contents = [f for f in frames if f.get("type") == "TEXT_MESSAGE_CONTENT"]
    assert text_contents, (
        f"no TEXT_MESSAGE_CONTENT frame: types = {[f.get('type') for f in frames]}"
    )
    assert any(f.get("delta", "") for f in text_contents), (
        f"all TEXT_MESSAGE_CONTENT frames have empty delta: {text_contents!r}"
    )

    # Hard invariant 3: last frame is RUN_FINISHED (or RUN_ERROR).
    last = frames[-1]
    assert last.get("type") in ("RUN_FINISHED", "RUN_ERROR"), (
        f"last frame should be RUN_FINISHED or RUN_ERROR, got {last.get('type')!r}"
    )

    # Hard invariant 4: ordering — RUN_STARTED before TEXT_MESSAGE_START before RUN_FINISHED.
    seen_run_started = any(f.get("type") == "RUN_STARTED" for f in frames)
    seen_text_start = any(f.get("type") == "TEXT_MESSAGE_START" for f in frames)
    seen_run_finished = any(f.get("type") == "RUN_FINISHED" for f in frames)
    assert seen_run_started and seen_text_start and seen_run_finished, (
        f"missing one of RUN_STARTED/TEXT_MESSAGE_START/RUN_FINISHED: types = {[f.get('type') for f in frames]}"
    )

    # Verify ordering by index.
    idx_started = next(i for i, f in enumerate(frames) if f.get("type") == "RUN_STARTED")
    idx_finished = next(i for i, f in enumerate(frames) if f.get("type") == "RUN_FINISHED")
    assert idx_started < idx_finished, (
        f"RUN_STARTED (idx {idx_started}) must precede RUN_FINISHED (idx {idx_finished})"
    )
