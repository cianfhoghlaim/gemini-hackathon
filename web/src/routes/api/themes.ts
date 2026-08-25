import { createFileRoute } from "@tanstack/react-router";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

function loadFromDir(dir: string): unknown[] {
  const out: unknown[] = [];
  let entries: string[] = [];
  try {
    entries = readdirSync(dir).filter((f) => f.endsWith(".json"));
  } catch {
    return out;
  }
  for (const file of entries) {
    try {
      const raw = readFileSync(join(dir, file), "utf-8");
      out.push(JSON.parse(raw));
    } catch {
      continue;
    }
  }
  return out;
}

export const Route = createFileRoute("/api/themes")({
  server: {
    handlers: {
      GET: async () => {
        const themesRoot = join(process.cwd(), "..", "themes");
        const safeguardingRoot = join(themesRoot, "safeguarding");
        const palettes = [
          ...loadFromDir(themesRoot),
          ...loadFromDir(safeguardingRoot),
        ];
        return new Response(
          JSON.stringify({ palettes, count: palettes.length }),
          { headers: { "Content-Type": "application/json" } },
        );
      },
    },
  },
});
