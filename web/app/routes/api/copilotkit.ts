import { createAPIFileRoute } from "@tanstack/react-start/api";

const PYTHON_BACKEND =
  process.env.PYTHON_BACKEND_URL ?? "http://localhost:8000";

export const Route = createAPIFileRoute("/api/copilotkit")({
  ALL: async ({ request }) => {
    const url = new URL(request.url);
    const target = `${PYTHON_BACKEND}/api/copilotkit${url.pathname.replace("/api/copilotkit", "")}${url.search}`;
    const upstream = await fetch(target, {
      method: request.method,
      headers: request.headers,
      body: request.body,
      // @ts-expect-error duplex is required for streaming bodies
      duplex: "half",
    });
    return new Response(upstream.body, {
      status: upstream.status,
      headers: upstream.headers,
    });
  },
});
