/**
 * Root layout for the gemini_hackathon public demo.
 *
 * Wraps every page with:
 *   - SourcePaletteProvider: resolves the per-source palette (the visual layer)
 *   - ConvexProvider: real-time database for runtime data
 *   - SessionProvider: per-tab user identity (subnation + role + cycle) — the
 *     load-bearing piece for per-route content scoping
 *   - CopilotKit: AG-UI streaming chat
 */

import { Outlet, Link, createRootRoute } from "@tanstack/react-router";
import { ConvexProvider, ConvexReactClient } from "convex/react";
import { CopilotKit } from "@copilotkit/react-core";
import { SourcePaletteProvider } from "../components/themes/SourcePaletteProvider";
import { SessionProvider } from "../components/session/SessionContext";
import "../globals.css";

const CONVEX_URL =
  (import.meta.env.VITE_CONVEX_URL as string) ?? "http://localhost:3210";
const COPILOTKIT_RUNTIME_URL =
  (import.meta.env.VITE_COPILOTKIT_RUNTIME_URL as string) ?? "/api/copilotkit";

const convex = new ConvexReactClient(CONVEX_URL, { unsavedChangesWarning: false });

export const Route = createRootRoute({
  component: RootComponent,
});

function RootComponent() {
  return (
    <html lang="en-IE" data-palette-source="ncca.ie">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>gemini_hackathon — One platform for the British Isles</title>
        <meta
          name="description"
          content="A theming + agentic platform for students, parents, and teachers in the British Isles."
        />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Merriweather:wght@400;700&display=swap"
        />
      </head>
      <body>
        <SourcePaletteProvider>
          <SessionProvider>
            <ConvexProvider client={convex}>
              <CopilotKit runtimeUrl={COPILOTKIT_RUNTIME_URL} agent="gemini_hackathon_agent">
                <div className="min-h-screen flex flex-col bg-[var(--color-background)] text-[var(--color-text)] font-[var(--font-body)]">
                  <header className="border-b border-[var(--color-secondary)]/20 px-6 py-4 flex items-center justify-between">
                    <Link to="/" className="text-2xl font-[var(--font-heading)] text-[var(--color-primary)]">
                      gemini_hackathon
                    </Link>
                    <nav className="flex gap-4 text-sm">
                      <Link to="/subjects" className="hover:text-[var(--color-accent)]">Subjects</Link>
                      <Link to="/safeguarding" className="hover:text-[var(--color-accent)]">Safeguarding</Link>
                      <Link to="/find-resources" className="hover:text-[var(--color-accent)]">Find resources</Link>
                      <Link to="/agents" className="hover:text-[var(--color-accent)]">Agent</Link>
                      <Link to="/archipelago" className="hover:text-[var(--color-accent)]">Archipelago</Link>
                    </nav>
                  </header>
                  <main className="flex-1">
                    <Outlet />
                  </main>
                  <footer className="border-t border-[var(--color-secondary)]/20 px-6 py-4 text-xs text-[var(--color-text)]/50 text-center">
                    gemini_hackathon — Google ADK + Vertex AI (Gemini 3.5) + Gemma 4 via Unsloth Studio · 8 subnations · one platform
                  </footer>
                </div>
              </CopilotKit>
            </ConvexProvider>
          </SessionProvider>
        </SourcePaletteProvider>
      </body>
    </html>
  );
}
