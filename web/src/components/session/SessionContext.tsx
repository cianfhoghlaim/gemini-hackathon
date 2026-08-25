/**
 * Per-tab SessionContext — wraps the user session (subnation + role +
 * cycle + selected subjects) so every page can read it.
 *
 * In dev, the session lives in localStorage. In production, the
 * `saveSession` and `getSession` helpers talk to the Convex `userSessions`
 * table (schema already in `web/convex/schema.ts`).
 *
 * The active subnation drives:
 *   - The palette (auto-resolved from DEFAULT_PALETTE_PER_SUBNATION)
 *   - The safeguarding policy (auto-resolved)
 *   - All per-route content scoping
 *   - The ADK agent's system prompt (via the Python backend)
 */

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { ActiveSubnation, Role, Cycle, SubnationMeta } from "../../types/session";
import { SUBNATIONS } from "../../types/session";
import { getSession, saveSession, defaultSession, type SessionState } from "../../lib/session-helpers";

interface SessionContextValue {
  session: SessionState | null;
  setSession: (s: SessionState) => void;
  clearSession: () => void;
  subnation: SubnationMeta;
  isDefault: boolean;
}

const DEFAULT_SUBNATION: SubnationMeta = SUBNATIONS[0];

const SessionContext = createContext<SessionContextValue>({
  session: null,
  setSession: () => {},
  clearSession: () => {},
  subnation: DEFAULT_SUBNATION,
  isDefault: true,
});

export function SessionProvider({ children }: { children: ReactNode }) {
  const [session, setSessionState] = useState<SessionState | null>(null);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setSessionState(getSession());
    setHydrated(true);
  }, []);

  const subnation = useMemo<SubnationMeta>(() => {
    if (!session) return DEFAULT_SUBNATION;
    return (
      SUBNATIONS.find((s) => s.code === session.subnation) ?? DEFAULT_SUBNATION
    );
  }, [session]);

  const value: SessionContextValue = useMemo(
    () => ({
      session,
      setSession: (s) => {
        saveSession(s);
        setSessionState(s);
      },
      clearSession: () => {
        if (typeof window !== "undefined") {
          window.localStorage.removeItem("gh.session.v1");
        }
        setSessionState(null);
      },
      subnation,
      isDefault: !session || session.subnation === "ireland",
    }),
    [session, subnation],
  );

  return (
    <SessionContext.Provider value={value}>
      {children}
    </SessionContext.Provider>
  );
}

export function useSession(): SessionContextValue {
  return useContext(SessionContext);
}
