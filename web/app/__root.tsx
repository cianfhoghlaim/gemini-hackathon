import { type ReactNode } from "react";
import { Outlet, Link, createRootRoute } from "@tanstack/react-router";
import { ConvexProvider, ConvexReactClient } from "convex/react";
import { CopilotKit } from "@copilotkit/react-core";
import { BritainIslesMap } from "~/components/map/BritainIslesMap";
import { AGUIChat } from "~/components/chat/AGUIChat";
import { SourcePaletteProvider } from "~/components/themes/SourcePaletteProvider";
import "~/app/globals.css";

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
        <title>gemini_hackathon - Per-Source Theming Across the British Isles</title>
        <meta
          name="description"
          content="A theming + agentic system that adapts to the official source of every British-Isles jurisdiction and safeguarding body."
        />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Merriweather:wght@400;700&display=swap"
        />
      </head>
      <body>
        <SourcePaletteProvider>
          <ConvexProvider client={convex}>
            <CopilotKit runtimeUrl={COPILOTKIT_RUNTIME_URL} agent="gemini_hackathon_root">
              <div className="min-h-screen flex flex-col bg-[var(--color-background)] text-[var(--color-text)] font-[var(--font-body)]">
                <header className="border-b border-[var(--color-secondary)]/20 px-6 py-4 flex items-center justify-between">
                  <h1 className="text-2xl font-[var(--font-heading)] text-[var(--color-primary)]">
                    gemini_hackathon
                  </h1>
                  <nav className="flex gap-4 text-sm">
                    <Link to="/" className="hover:text-[var(--color-accent)]">Home</Link>
                    <Link to="/subjects" className="hover:text-[var(--color-accent)]">Subjects</Link>
                    <Link to="/safeguarding" className="hover:text-[var(--color-accent)]">Safeguarding</Link>
                    <Link to="/equivalency" className="hover:text-[var(--color-accent)]">Equivalencies</Link>
                  </nav>
                </header>
                <main className="flex-1 flex">
                  <aside className="w-80 border-r border-[var(--color-secondary)]/20 p-4">
                    <BritainIslesMap />
                  </aside>
                  <section className="flex-1 p-6">
                    <Outlet />
                  </section>
                  <aside className="w-96 border-l border-[var(--color-secondary)]/20 p-4">
                    <AGUIChat />
                  </aside>
                </main>
              </div>
            </CopilotKit>
          </ConvexProvider>
        </SourcePaletteProvider>
      </body>
    </html>
  );
}
