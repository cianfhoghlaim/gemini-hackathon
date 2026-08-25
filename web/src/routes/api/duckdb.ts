import { createFileRoute } from "@tanstack/react-router";
import { stat, readFile } from "node:fs/promises";
import { join } from "node:path";

export const Route = createFileRoute("/api/duckdb")({
  server: {
    handlers: {
      GET: async () => {
        const dbPath = process.env.DUCKDB_PATH
          || join(process.cwd(), "..", "data", "gemini_hackathon.duckdb");

        try {
          await stat(dbPath);
        } catch {
          return new Response(
            JSON.stringify({
              status: "not_ready",
              message: `DuckDB file not yet materialised at ${dbPath}. Run 'gemini-hackathon compare --pdf ...' first.`,
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
    },
  },
});
