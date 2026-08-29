import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "~": path.resolve(__dirname, "."),
    },
  },
  server: {
    port: 3000,
    host: "0.0.0.0",
    // No more proxy — the API routes delegate to Firebase Cloud Functions
    // in production (see web/src/routes/api/{themes,copilotkit,duckdb}.ts).
    // Locally we run them against the Functions emulator (`firebase emulators:start`).
  },
  build: {
    target: "es2022",
    sourcemap: true,
    outDir: "dist",
    emptyOutDir: true,
  },
});