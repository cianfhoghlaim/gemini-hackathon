// Per-subnation session context.
// The active session is stored in localStorage (dev) or fetched from
// Convex `userSessions` (production). For now: a typed wrapper around
// localStorage that all routes import.

import type { ActiveSubnation, Role, Cycle } from "~/types/session";

export interface SessionState {
  sessionId: string;
  userId: string;
  subnation: ActiveSubnation;
  role: Role;
  cycle: Cycle | null;
  selectedSubjects: string[];
  safeguardingSourceKey: string;
  paletteSourceKey: string;
  onboarded: boolean;
}

const STORAGE_KEY = "gh.session.v1";

export function getSession(): SessionState | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as SessionState;
  } catch {
    return null;
  }
}

export function saveSession(s: SessionState): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
}

export function clearSession(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(STORAGE_KEY);
}

export function defaultSession(): SessionState {
  return {
    sessionId: `local-${Math.random().toString(36).slice(2, 10)}`,
    userId: "anonymous",
    subnation: "ireland",
    role: "student",
    cycle: "leaving_cycle",
    selectedSubjects: [],
    safeguardingSourceKey: "gov.ie/education",
    paletteSourceKey: "ncca.ie",
    onboarded: false,
  };
}
