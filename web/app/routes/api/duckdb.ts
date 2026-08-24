/**
 * API route that serves the gemini_hackathon.duckdb file to the browser.
 * DuckDB-WASM reads the whole file via fetch() then opens it in-process.
 *
 * For large files (>200MB) switch to Range-based streaming; for the
 * hackathon demo the .duckdb file is well under that.
 */

import { createAPIFileRoute } from "@tanstack/react-start/api";
import { stat, readFile } from "node:fs/promises";
import { join } from "node:path";

export const Route = createAPIFileRoute("/api/duckdb")({
  GET: async () => {
    // Locate the .duckdb file. The web app expects it at the repo root.
    const dbPath = process.env.DUCKDB_PATH
      || join(process.cwd(), "..", "data", "gemini_hackathon.duckdb");

    try {
      await stat(dbPath);
    } catch {
      return new Response(
        JSON.stringify({
          status: "not_ready",
          message: `DuckDB file not yet materialised at ${dbPath}. Run 'gemini-hackathon pipeline run all' first.`,
        }),
        { status: 404, headers: { "Content-Type": "application/json" } },
      );
    }

    const buf = await readFile(dbPath);
    return new Response(buf, {
      status: 200,
      headers: {
        "Content-Type": "application/octet-stream",
        "Cache-Control": "no-cache",
      },
    });
  },
});
