/**
 * Root layout for the gemini_hackathon public demo.
 *
 * Migrated from TanStack Start + Convex + hand-rolled SSE to:
 *   - Vite + react-router-dom (Phase T3 of the ADK + CopilotKit refactor)
 *   - CopilotKit v2 + AG-UI bridge to the `gemini-hackathon-adk` Cloud Run
 *     service (the AG-UI SSE endpoint at /)
 *   - @copilotkit/a2ui-renderer for streaming JSONL → React panels
 *
 * Wraps every page with (outer → inner):
 *   - AuthGate               Firebase Auth + App Check attestation
 *   - CopilotKitProvider     the AG-UI runtime + A2UI renderer (new in T3)
 *   - SourcePaletteProvider  resolves the per-source palette
 *   - SessionProvider        per-user identity (subnation + role + cycle)
 */

import { Outlet, Link } from "react-router-dom";
import { SourcePaletteProvider } from "../components/themes/SourcePaletteProvider";
import { SessionProvider } from "../components/session/SessionContext";
import { AuthGate } from "../components/auth/AuthGate";
import { firebaseApp } from "../lib/firebase.ts";
import catalog from "../a2ui/catalog";
import { citePdfRenderer } from "../a2ui/tool-renderers";
import { setThemeColorTool } from "../a2ui/frontend-tools";
import "../globals.css";
import { CopilotKit, CopilotKitProvider } from "@copilotkit/react-core/v2";

// Eager-init Firebase so the singleton app instance is ready before any
// component (AuthGate, SessionProvider) calls getAuth/getFirestore.
firebaseApp();

const PROJECT_NAME = import.meta.env.VITE_FIREBASE_PROJECT_ID ?? "gemini-hackathon-prod";
const ADK_RUNTIME_URL =
  import.meta.env.VITE_ADK_RUNTIME_URL ?? "https://gemini-hackathon-adk-eeeeeeeeeeeeeeee.a.run.app";

export default function App(): React.ReactNode {
  // The CopilotKit provider is wrapped INSIDE AuthGate so unauthenticated
  // users don't open an SSE stream to the ADK backend. The `useSingleEndpoint`
  // flag is set to `false` because we use BOTH the v2 CopilotKit runtime
  // (for AG-UI chat) AND the Firebase Functions layer (for design tokens
  // + Stitch + DuckDB export) — they're separate runtimes, not one merged.
  //
  // The `a2ui={...}` prop wires our 6 NCCA components + the basic catalog
  // (Text, Button, Row, Column, List, Card) — see a2ui/catalog.tsx.
  return (
    <AuthGate>
      <CopilotKit
        runtimeUrl={ADK_RUNTIME_URL}
        agent="ncca_panel"
        publicLicenseKey={import.meta.env.VITE_COPILOTKIT_PUBLIC_LICENSE_KEY ?? ""}
        useSingleEndpoint={false}
        a2ui={{ catalog }}
        frontendTools={[setThemeColorTool]}
        renderToolCalls={[citePdfRenderer]}
      >
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
      </CopilotKit>
    </AuthGate>
  );
}
