import { defineConfig } from "vite";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [
    tanstackStart(),
    react(),
  ],
  resolve: {
    alias: {
      "~": path.resolve(__dirname, "."),
    },
  },
  server: {
    port: 3000,
    host: "0.0.0.0",
    proxy: {
      "/api/agents": "http://localhost:8000",
      "/api/copilotkit": "http://localhost:8000",
    },
  },
  build: {
    target: "es2022",
    sourcemap: true,
  },
});
