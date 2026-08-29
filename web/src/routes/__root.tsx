/**
 * Root layout for the gemini_hackathon public demo.
 *
 * Migrated from TanStack Start + Convex + CopilotKit to a Firebase-native
 * stack: Firebase Auth + Firestore + Cloud Functions for Firebase (Gen2) +
 * Firebase App Check + Firebase Performance.
 *
 * Wraps every page with:
 *   - AuthGate: Firebase Auth + App Check attestation (the 3-layer security model)
 *   - SourcePaletteProvider: resolves the per-source palette (the visual layer)
 *   - SessionProvider: per-user identity (subnation + role + cycle) — the
 *     load-bearing piece for per-route content scoping, backed by Firestore
 *   - The Firestore realtime subscriptions that replace the Convex hooks
 *
 * Per the All Things Agentic Hackathon Fortified Enterprise Fleet track.
 */

import { Outlet, Link, createRootRoute } from "@tanstack/react-router";
import { SourcePaletteProvider } from "../components/themes/SourcePaletteProvider";
import { SessionProvider } from "../components/session/SessionContext";
import { AuthGate } from "../components/auth/AuthGate";
import { firebaseApp } from "../lib/firebase";
import "../globals.css";

// Eager-init Firebase so the singleton app instance is ready before any
// component (AuthGate, SessionProvider) calls getAuth/getFirestore.
firebaseApp();

const PROJECT_NAME = import.meta.env.VITE_FIREBASE_PROJECT_ID ?? "gemini-hackathon-prod";

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
        <AuthGate>
          <SourcePaletteProvider>
            <SessionProvider>
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
                  gemini_hackathon — Google ADK + Vertex AI (Gemini 3.5) + Gemma 4 via Unsloth Studio · Firebase Auth + Firestore + Cloud Functions · 8 subnations · one platform
                </footer>
              </div>
            </SessionProvider>
          </SourcePaletteProvider>
        </AuthGate>
      </body>
    </html>
  );
}