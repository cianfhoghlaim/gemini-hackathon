import { createAPIFileRoute } from "@tanstack/react-start/api";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

interface RawPalette {
  sourceKey: string;
  sourceName: string;
  jurisdiction: string;
  level: string;
  policyScope?: string;
  palette: {
    primary: string;
    secondary: string;
    accent: string;
    background: string;
    text: string;
  };
  typography: {
    heading: string;
    body: string;
  };
  iconography?: {
    logoUrl?: string;
  };
  flag?: string;
}

function loadFromDir(dir: string): RawPalette[] {
  const out: RawPalette[] = [];
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

export const Route = createAPIFileRoute("/api/themes")({
  GET: async () => {
    // themes/ is at the repo root, web/ is one level deep.
    const themesRoot = join(process.cwd(), "..", "themes");
    const safeguardingRoot = join(themesRoot, "safeguarding");
    const palettes = [
      ...loadFromDir(themesRoot),
      ...loadFromDir(safeguardingRoot),
    ];
    return Response.json({ palettes, count: palettes.length });
  },
});
