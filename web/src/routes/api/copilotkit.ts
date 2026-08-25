import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/api/copilotkit")({
  server: {
    handlers: {
      GET: async ({ request }: { request: Request }) =>
        proxyToPythonBackend(request),
      POST: async ({ request }: { request: Request }) =>
        proxyToPythonBackend(request),
      PUT: async ({ request }: { request: Request }) =>
        proxyToPythonBackend(request),
      DELETE: async ({ request }: { request: Request }) =>
        proxyToPythonBackend(request),
    },
  },
});

async function proxyToPythonBackend(request: Request): Promise<Response> {
  const pythonBackend =
    process.env.PYTHON_BACKEND_URL ?? "http://localhost:8000";

  const url = new URL(request.url);
  // The route is exactly /api/copilotkit; the Python backend mirrors at /api/copilotkit
  const finalUrl = `${pythonBackend.replace(/\/+$/, "")}${url.pathname}${url.search}`;

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
        hint: "Start the Python backend with `mise run backend`.",
      }),
      {
        status: 503,
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*",
        },
      },
    );
  }

  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      ...Object.fromEntries(upstream.headers),
      "Access-Control-Allow-Origin": "*",
    },
  });
}
