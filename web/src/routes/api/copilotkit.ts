/**
 * /api/copilotkit/** — delegate to the Firebase Cloud Function `chatHandler`
 * which streams Gemini 3.5 Flash responses via Server-Sent Events.
 *
 * Replaces the prior TanStack Start reverse-proxy to the Python `backend.py`
 * (`web/src/routes/api/copilotkit.ts`). The CopilotKit runtime was mounted-but-
 * unused; the new path is direct Firebase AI streaming.
 */

import { createFileRoute } from "@tanstack/react-router";
import { getIdToken } from "../../lib/auth";

const FUNCTIONS_BASE =
  import.meta.env.VITE_FIREBASE_FUNCTIONS_URL ??
  `https://europe-west1-${import.meta.env.VITE_FIREBASE_PROJECT_ID ?? "gemini-hackathon-prod"}.cloudfunctions.net`;

async function proxyToChatStream(request: Request): Promise<Response> {
  const token = await getIdToken();
  const url = new URL(request.url);
  const finalUrl = `${FUNCTIONS_BASE}/chatStream${url.pathname.replace(/^\/api\/copilotkit/, "")}${url.search}`;
  const upstream = await fetch(finalUrl, {
    method: request.method,
    headers: {
      ...Object.fromEntries(request.headers),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: request.body,
    // @ts-expect-error duplex is required for streaming bodies
    duplex: "half",
  });
  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      ...Object.fromEntries(upstream.headers),
      "Access-Control-Allow-Origin": "*",
    },
  });
}

export const Route = createFileRoute("/api/copilotkit")({
  server: {
    handlers: {
      GET: async ({ request }) => proxyToChatStream(request),
      POST: async ({ request }) => proxyToChatStream(request),
      PUT: async ({ request }) => proxyToChatStream(request),
      DELETE: async ({ request }) => proxyToChatStream(request),
    },
  },
});