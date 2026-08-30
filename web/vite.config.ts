import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
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
