/**
 * CopilotKit / AG-UI proxy endpoint.
 *
 * Streams chat-completion events from the local Python backend (which
 * routes through the 3-tier LiteLLM router). The Python backend serves
 * the OpenAI-compatible /api/chat/completions shape that CopilotKit's
 * useAgentContext hook expects.
 *
 * The proxy passes through:
 *   - request method, headers, body
 *   - response status, headers, body (streamed)
 *
 * Why proxy instead of direct-to-LLM:
 *   - The Python backend enforces MODEL_PROFILE gating (hackathon vs dev).
 *   - The Python backend emits structlog `llm.invocation` events with
 *     tier/backend/latency — feeds the Langfuse/MLflow observability stack.
 *   - The Python backend handles the Cloudflare / Qwen3-coder exclusion guard.
 *
 * If PYTHON_BACKEND_URL is unset, this route returns a 503 with a
 * helpful message rather than silently failing.
 */

import { createAPIFileRoute } from "@tanstack/react-start/api";

export const Route = createAPIFileRoute("/api/copilotkit")({
  ALL: async ({ request }) => {
    const pythonBackend =
      process.env.PYTHON_BACKEND_URL ?? "http://localhost:8000";

    const url = new URL(request.url);
    // /api/copilotkit/chat -> /api/chat on the Python backend
    const stripped = url.pathname.replace(/^\/api\/copilotkit/, "") || "/";
    const finalUrl = `${pythonBackend.replace(/\/+$/, "")}/api${stripped}${url.search}`;

    let upstream: Response;
    try {
      upstream = await fetch(finalUrl, {
        method: request.method,
        headers: request.headers,
        body: request.body,
        // @ts-expect-error duplex is required for streaming bodies
        duplex: "half",
      });
    } catch (err) {
      return new Response(
        JSON.stringify({
          error: "python_backend_unreachable",
          python_backend: pythonBackend,
          detail: String(err),
          hint: "Start the Python backend with `mise run serve` (or `python -m gemini_hackathon.cli serve --port 8000`).",
        }),
        { status: 503, headers: { "Content-Type": "application/json" } },
      );
    }

    return new Response(upstream.body, {
      status: upstream.status,
      headers: upstream.headers,
    });
  },
});
