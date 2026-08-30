import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

/**
 * Registers the dev-mode /api/* proxies (themes + duckdb) at the Vite
 * dev server. In production the same logic is served by the Firebase
 * Cloud Functions at `europe-west1-<PROJECT>.cloudfunctions.net/...`.
 *
 * Replaces the prior TanStack Start `createFileRoute("/api/...")` server
 * handlers; this plugin exposes the `GET` exports of
 * `web/src/routes/api/{themes,duckdb}.ts` as Vite middleware.
 */
function apiProxyPlugin(): Plugin {
  return {
    name: "gemini-hackathon-api-proxy",
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        if (!req.url) return next();
        if (req.url.startsWith("/api/themes")) {
          const mod = await server.ssrLoadModule("/src/routes/api/themes.ts");
          const response = await mod.GET(toFetchRequest(req));
          await sendResponse(res, response);
          return;
        }
        if (req.url.startsWith("/api/duckdb")) {
          const mod = await server.ssrLoadModule("/src/routes/api/duckdb.ts");
          const response = await mod.GET(toFetchRequest(req));
          await sendResponse(res, response);
          return;
        }
        next();
      });
    },
  };
}

/** Adapter: Node IncomingMessage → Web Fetch Request. */
function toFetchRequest(req: { url?: string; method?: string; headers: NodeJS.Dict<string | string[]> }): Request {
  const url = req.url ?? "/";
  const method = req.method ?? "GET";
  const headers = new Headers();
  for (const [k, v] of Object.entries(req.headers)) {
    if (v == null) continue;
    headers.set(k, Array.isArray(v) ? v.join(", ") : String(v));
  }
  return new Request(`http://localhost${url}`, { method, headers });
}

/** Adapter: Web Fetch Response → Node ServerResponse. */
async function sendResponse(res: { statusCode: number; setHeader: (k: string, v: string) => void; end: (chunk?: Buffer | string) => void }, response: Response): Promise<void> {
  res.statusCode = response.status;
  response.headers.forEach((v, k) => res.setHeader(k, v));
  const body = await response.arrayBuffer();
  res.end(Buffer.from(body));
}

export default defineConfig({
  plugins: [react(), apiProxyPlugin()],
  resolve: {
    alias: {
      "~": path.resolve(__dirname, "."),
    },
    // Allow extensionless and `.ts`/`.tsx` imports — the pre-existing
    // repo (per the TanStack Start -> react-router-dom migration) never
    // used extensionful paths and Vite v7's defaults don't include `.ts`
    // in `resolve.extensions` for Rollup.
    extensions: [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".json"],
  },
  ssr: {
    noExternal: true,
  },
  optimizeDeps: {
    include: ["../lib/firebase", "../lib/observability-browser"],
    esbuildOptions: {
      loader: { ".ts": "ts", ".tsx": "tsx" },
    },
  },
  server: {
    port: 3000,
    host: "0.0.0.0",
  },
  build: {
    target: "es2022",
    sourcemap: true,
    outDir: "dist",
    emptyOutDir: true,
  },
});
