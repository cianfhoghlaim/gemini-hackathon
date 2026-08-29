/**
 * /api/duckdb — delegate to the Firebase Cloud Function `duckdbHandler`
 * which 302-redirects to a signed Firebase Storage URL for the latest
 * `.parquet` analytics export.
 *
 * Replaces the prior filesystem-read implementation
 * (`web/src/routes/api/duckdb.ts`) with a Cloud Function call that returns
 * a signed Cloud Storage URL.
 */

import { createFileRoute } from "@tanstack/react-router";

const FUNCTIONS_BASE =
  import.meta.env.VITE_FIREBASE_FUNCTIONS_URL ??
  `https://europe-west1-${import.meta.env.VITE_FIREBASE_PROJECT_ID ?? "gemini-hackathon-prod"}.cloudfunctions.net`;

export const Route = createFileRoute("/api/duckdb")({
  server: {
    handlers: {
      GET: async () => {
        const url = `${FUNCTIONS_BASE}/duckdbAsset`;
        const resp = await fetch(url, { redirect: "manual" });
        // The Cloud Function does a 302 redirect to the signed Cloud Storage URL;
        // we pass it through to the browser so the browser downloads directly.
        return new Response(null, {
          status: resp.status,
          headers: Object.fromEntries(resp.headers),
        });
      },
    },
  },
});