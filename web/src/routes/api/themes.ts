/**
 * /api/themes — delegate to the Firebase Cloud Function `themesHandler`
 * which reads the 12 official-guidelines palette JSONs + the Stitch-managed
 * design_tokens from Firestore.
 *
 * Replaces the prior filesystem-read implementation (`web/src/routes/api/themes.ts`)
 * with a Cloud Function call. The Cloud Function URL is configured at
 * build time via `VITE_FIREBASE_FUNCTIONS_URL` (defaults to the project's
 * functions origin on `europe-west1`).
 */

import { createFileRoute } from "@tanstack/react-router";
import { getIdToken } from "~/src/lib/auth.ts";

const FUNCTIONS_BASE =
  import.meta.env.VITE_FIREBASE_FUNCTIONS_URL ??
  import.meta.env.VITE_FIREBASE_FUNCTIONS_ORIGIN ??
  `https://europe-west1-${import.meta.env.VITE_FIREBASE_PROJECT_ID ?? "gemini-hackathon-prod"}.cloudfunctions.net`;

export const Route = createFileRoute("/api/themes")({
  server: {
    handlers: {
      GET: async ({ request }) => {
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
      },
    },
  },
});