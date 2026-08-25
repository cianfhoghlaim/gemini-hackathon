/**
 * The home page — per-subnation landing for the active session.
 *
 * Behaviour:
 *   - For an unauthenticated user: shows the onboarding picker
 *     ("Where are you studying or working?" — Ireland / England / More)
 *   - For an onboarded user: shows their subnation's home (role-conditional
 *     quick actions + the archipelagic unity ribbon)
 *   - The map is now an "onboarding" affordance, not a swap.
 */

import { createFileRoute, Link } from "@tanstack/react-router";
import { useSession } from "../components/session/SessionContext";
import { OnboardingPicker } from "../components/onboarding/OnboardingPicker";
import { ArchipelagicRibbon } from "../components/session/ArchipelagicRibbon";
import { useEffect, useState } from "react";
import { getSession, saveSession, defaultSession, type SessionState } from "./_session";
import type { ActiveSubnation, Role, Cycle } from "../types/session";
import { SUBNATIONS, DEFAULT_SUBNATIONS, EXPANSION_SUBNATIONS, AVAILABLE_SUBNATIONS, SUBJECT_CATALOGUE } from "../types/session";

export const Route = createFileRoute("/")({
  component: HomePage,
});

function HomePage() {
  const { session, setSession } = useSession();
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    if (!session) {
      const existing = getSession();
      if (existing) setSession(existing);
    }
    setHydrated(true);
  }, [session, setSession]);

  if (!hydrated) {
    return (
      <div className="max-w-6xl mx-auto p-6">
        <div className="text-sm text-[var(--color-text)]/60">Loading session…</div>
      </div>
    );
  }

  // Unauthenticated: show the onboarding picker.
  if (!session || !session.onboarded) {
    return <OnboardingPicker onComplete={(s) => { saveSession(s); setSession(s); }} />;
  }

  return <SubnationHome session={session} />;
}

function SubnationHome({ session }: { session: SessionState }) {
  const sub = SUBNATIONS.find((s) => s.code === session.subnation) ?? SUBNATIONS[0];
  const cycleSubjects = (SUBJECT_CATALOGUE[session.subnation] ?? []).filter(
    (s) => !session.cycle || s.cycle === session.cycle,
  );

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      {/* The archipelagic unity ribbon — one row, one palette, all 8 nations */}
      <ArchipelagicRibbon activeSubnation={sub.code} />

      {/* The user's home subnation header */}
      <header className="flex items-baseline gap-4">
        <h1 className="text-4xl font-[var(--font-heading)] text-[var(--color-primary)]">
          {sub.flag} {sub.name}
        </h1>
        <span className="text-sm text-[var(--color-text)]/60">
          {sub.awardingBody} · {sub.awardingBodyShort}
        </span>
        <Link
          to="/archipelago"
          className="ml-auto text-sm text-[var(--color-secondary)] underline"
        >
          See all 8 nations →
        </Link>
      </header>

      {/* Role-conditional quick actions */}
      <section className="grid grid-cols-2 gap-3">
        {session.role === "student" && (
          <>
            <QuickAction to="/subjects" label="My subjects" sub={`${cycleSubjects.length} in ${sub.name}`} />
            <QuickAction to="/agents" label="Ask the agent" sub="Composes your subnation + role + cycle" />
            <QuickAction to="/safeguarding" label="Safeguarding in effect" sub={sub.awardingBody} />
            <QuickAction to="/find-resources" label="Find resources that help" sub="Cross-national discovery" />
          </>
        )}
        {session.role === "parent" && (
          <>
            <QuickAction to="/subjects" label="What your child is studying" sub={`${cycleSubjects.length} subjects`} />
            <QuickAction to="/safeguarding" label="Safeguarding in effect" sub={sub.safeguardingSourceKey} />
            <QuickAction to="/find-resources" label="Find resources across nations" sub="Cross-national discovery" />
            <QuickAction to="/agents" label="Ask the agent" sub="Curriculum explainer" />
          </>
        )}
        {session.role === "teacher" && (
          <>
            <QuickAction to="/agents" label="Mark a paper" sub="Per-question mark breakdown" />
            <QuickAction to="/find-resources" label="Find resources that help" sub="Cross-national" />
            <QuickAction to="/subjects" label="Curriculum changes" sub="Per-subnation change sensor" />
            <QuickAction to="/safeguarding" label="Safeguarding in effect" sub={sub.safeguardingSourceKey} />
          </>
        )}
      </section>

      {/* The active subjects for the home subnation */}
      <section>
        <h2 className="text-2xl font-[var(--font-heading)] mb-3">
          {sub.name} subjects
        </h2>
        {cycleSubjects.length === 0 ? (
          <p className="text-sm text-[var(--color-text)]/60">
            No subjects found for {sub.name} in this cycle yet.
          </p>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            {cycleSubjects.map((s) => (
              <Link
                key={`${s.sourceKey}-${s.cycle}-${s.name}`}
                to="/find-resources"
                search={{ subject: s.name }}
                className="block p-3 rounded border hover:shadow-md transition"
                style={{
                  borderColor: "var(--color-secondary)/20",
                  background: "var(--color-background)",
                }}
              >
                <h3 className="font-[var(--font-heading)] text-lg">{s.name}</h3>
                <p className="text-xs text-[var(--color-text)]/60">
                  {s.cycle.replace(/_/g, " ")}
                  {s.examBoard ? ` · ${s.examBoard}` : ""}
                </p>
              </Link>
            ))}
          </div>
        )}
      </section>

      {/* Change home link */}
      <p className="text-xs text-[var(--color-text)]/50 text-center pt-4">
        Studying or working somewhere else?{" "}
        <button
          onClick={() => {
            if (typeof window !== "undefined") {
              window.localStorage.removeItem("gh.session.v1");
              window.location.reload();
            }
          }}
          className="underline"
        >
          Change home
        </button>
      </p>
    </div>
  );
}

function QuickAction({ to, label, sub }: { to: string; label: string; sub: string }) {
  return (
    <Link
      to={to}
      className="block p-4 rounded border hover:shadow-md transition"
      style={{
        borderColor: "var(--color-secondary)/20",
        background: "var(--color-background)",
      }}
    >
      <h3 className="font-[var(--font-heading)] text-lg">{label}</h3>
      <p className="text-xs text-[var(--color-text)]/60 mt-1">{sub}</p>
    </Link>
  );
}
