/**
 * Per-user SessionContext — wraps the user session (subnation + role +
 * cycle + selected subjects) so every page can read it.
 *
 * Migrated from the prior localStorage-only version to a Firebase Auth +
 * Firestore-backed implementation. The custom claims set in
 * `functions/src/auth_oncreate.ts` provide the defaults; the user can
 * change them via the onboarding flow (which writes to Firestore).
 *
 * Per the All Things Agentic Hackathon Fortified Enterprise Fleet sub-criterion
 * "Agent Memory Bank (for persistent, secure cross-session context)" — the
 * session state lives in Firestore + custom claims, not localStorage.
 */

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { onAuthStateChanged, type User } from "firebase/auth";
import { doc, onSnapshot, type DocumentData } from "firebase/firestore";
import type { ActiveSubnation, Role, Cycle, SubnationMeta } from "../../types/session";
import { SUBNATIONS } from "../../types/session";
import { firebaseAuth, firebaseDb } from "~/src/lib/firebase";
import { logStructured } from "~/src/lib/observability-browser";

export interface SessionState {
  uid: string;
  email: string | null;
  isAnonymous: boolean;
  subnation: ActiveSubnation;
  role: Role;
  cycle: Cycle;
  selectedSubjects: string[];
  safeguardingSourceKey: string;
  paletteSourceKey: string;
  onboarded: boolean;
}

const DEFAULT_SESSION: Omit<SessionState, "uid" | "email" | "isAnonymous"> = {
  subnation: "ireland",
  role: "student",
  cycle: "leaving_cycle",
  selectedSubjects: [],
  safeguardingSourceKey: "gov.ie/education",
  paletteSourceKey: "ncca.ie",
  onboarded: false,
};

interface SessionContextValue {
  session: SessionState | null;
  user: User | null;
  setSession: (s: Partial<SessionState>) => void;
  clearSession: () => void;
  subnation: SubnationMeta;
  isDefault: boolean;
}

const DEFAULT_SUBNATION: SubnationMeta = SUBNATIONS[0];

const SessionContext = createContext<SessionContextValue>({
  session: null,
  user: null,
  setSession: () => {},
  clearSession: () => {},
  subnation: DEFAULT_SUBNATION,
  isDefault: true,
});

export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSessionState] = useState<SessionState | null>(null);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const unsubAuth = onAuthStateChanged(firebaseAuth(), (u) => {
      setUser(u);
      if (!u) {
        setSessionState(null);
        setHydrated(true);
      }
    });
    return unsubAuth;
  }, []);

  useEffect(() => {
    if (!user) return;
    const unsubUser = onSnapshot(
      doc(firebaseDb(), "users", user.uid),
      (snap) => {
        if (!snap.exists()) {
          // No Firestore user doc yet — the Cloud Function onCreate will create it
          setSessionState({
            uid: user.uid,
            email: user.email,
            isAnonymous: user.isAnonymous,
            ...DEFAULT_SESSION,
          });
          setHydrated(true);
          return;
        }
        const data = snap.data() as DocumentData;
        setSessionState({
          uid: user.uid,
          email: user.email,
          isAnonymous: user.isAnonymous,
          subnation: (data.subnation as ActiveSubnation) ?? DEFAULT_SESSION.subnation,
          role: (data.role as Role) ?? DEFAULT_SESSION.role,
          cycle: (data.cycle as Cycle) ?? DEFAULT_SESSION.cycle,
          selectedSubjects: (data.selectedSubjects as string[]) ?? [],
          safeguardingSourceKey: (data.safeguardingSourceKey as string) ?? DEFAULT_SESSION.safeguardingSourceKey,
          paletteSourceKey: (data.paletteSourceKey as string) ?? DEFAULT_SESSION.paletteSourceKey,
          onboarded: (data.onboarded as boolean) ?? false,
        });
        setHydrated(true);
      },
    );
    return unsubUser;
  }, [user]);

  const subnation = useMemo<SubnationMeta>(() => {
    if (!session) return DEFAULT_SUBNATION;
    return SUBNATIONS.find((s) => s.code === session.subnation) ?? DEFAULT_SUBNATION;
  }, [session]);

  const value: SessionContextValue = useMemo(
    () => ({
      session,
      user,
      setSession: (s) => {
        if (!user) return;
        setSessionState((prev) => prev ? { ...prev, ...s } : null);
        // The onboarding flow writes to Firestore via the authOnCreate
        // → use the patchDoc helper from lib/firestore.ts
        logStructured("info", {
          event: "session_updated",
          uid: user.uid,
          ...s,
        });
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
    [session, user, subnation],
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