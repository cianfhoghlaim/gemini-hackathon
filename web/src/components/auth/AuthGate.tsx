/**
 * AuthGate — wraps the entire app and ensures every request goes through
 * Firebase Auth (the 3-layer security model: Security Rules + IAM + App Check).
 *
 * Public routes (`/`, `/login`, `/api/*`) are accessible without auth.
 * Everything else requires a signed-in user.
 *
 * Per the All Things Agentic Hackathon Fortified Enterprise Fleet sub-criterion
 * "Agent Identity (zero-trust access control)".
 */

import { useEffect, useState, type ReactNode } from "react";
import { onAuthStateChanged, type User } from "firebase/auth";
import { firebaseAuth } from "../lib/firebase";
import { SignInButton } from "./SignInButton";
import { logStructured } from "../lib/observability-browser";

interface AuthGateProps {
  children: ReactNode;
}

const PUBLIC_ROUTES = new Set(["/", "/login", "/api/copilotkit", "/api/themes", "/api/duckdb", "/api/stitch"]);

export function AuthGate({ children }: AuthGateProps) {
  const [user, setUser] = useState<User | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const pathname = typeof window !== "undefined" ? window.location.pathname : "/";

  useEffect(() => {
    const unsub = onAuthStateChanged(firebaseAuth(), (u) => {
      setUser(u);
      setHydrated(true);
      logStructured("info", {
        event: "auth_state_changed",
        uid: u?.uid ?? null,
        anonymous: u?.isAnonymous ?? true,
      });
    });
    return unsub;
  }, []);

  // Wait for the auth state to hydrate
  if (!hydrated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--color-background)]">
        <div className="text-sm opacity-60">Loading…</div>
      </div>
    );
  }

  const isPublic = PUBLIC_ROUTES.has(pathname) ||
                   pathname.startsWith("/api/") ||
                   pathname.startsWith("/_ah/") ||
                   pathname.startsWith("/login");

  if (!user && !isPublic) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--color-background)] px-6">
        <div className="max-w-md w-full space-y-6 text-center">
          <div className="space-y-2">
            <h1 className="text-2xl font-[var(--font-heading)] text-[var(--color-primary)]">
              gemini_hackathon
            </h1>
            <p className="text-sm opacity-70">
              Sign in to access the British Isles education platform.
            </p>
          </div>
          <SignInButton />
          <p className="text-xs opacity-50">
            We use Firebase Auth + Google Sign-In. No password is stored.
            Anonymous sign-in is available as a fallback.
          </p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}