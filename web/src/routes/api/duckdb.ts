/**
 * /api/duckdb — dev-mode proxy to the Firebase Cloud Function
 * `duckdbHandler`, which 302-redirects to a signed Firebase Storage URL
 * for the latest `.parquet` analytics export.
 *
 * Migrated from TanStack Start's `createFileRoute("/api/duckdb")` server
 * handler to a Vite middleware handler.
 */

const FUNCTIONS_BASE =
  import.meta.env.VITE_FIREBASE_FUNCTIONS_URL ??
  `https://europe-west1-${import.meta.env.VITE_FIREBASE_PROJECT_ID ?? "gemini-hackathon-prod"}.cloudfunctions.net`;

export async function GET(_request: Request): Promise<Response> {
  const url = `${FUNCTIONS_BASE}/duckdbAsset`;
  const resp = await fetch(url, { redirect: "manual" });
  // Pass through the 302 to the browser so it downloads directly.
  return new Response(null, {
    status: resp.status,
    headers: Object.fromEntries(resp.headers),
  });
}