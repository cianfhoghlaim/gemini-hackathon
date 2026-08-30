/**
 * /api/themes — dev-mode proxy to the Firebase Cloud Function `themesHandler`.
 *
 * Migrated from TanStack Start's `createFileRoute("/api/themes")` server
 * handler to a Vite middleware handler. In production, the Cloud Run
 * service serves this directly via the deployed Cloud Function at
 * `https://europe-west1-<PROJECT_ID>.cloudfunctions.net/themesApi`.
 *
 * The Vite plugin in `vite.config.ts` registers this module's `GET`
 * export at the `/api/themes` path during dev.
 */

import { getIdToken } from "../../lib/auth.ts";

const FUNCTIONS_BASE =
  import.meta.env.VITE_FIREBASE_FUNCTIONS_URL ??
  import.meta.env.VITE_FIREBASE_FUNCTIONS_ORIGIN ??
  `https://europe-west1-${import.meta.env.VITE_FIREBASE_PROJECT_ID ?? "gemini-hackathon-prod"}.cloudfunctions.net`;

export async function GET(request: Request): Promise<Response> {
  const url = `${FUNCTIONS_BASE}/themesApi${new URL(request.url).search}`;
  const token = await getIdToken();
  const resp = await fetch(url, {
    method: "GET",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  // Pass-through + CORS
  return new Response(resp.body, {
    status: resp.status,
    headers: {
      ...Object.fromEntries(resp.headers),
      "Access-Control-Allow-Origin": "*",
    },
  });
}