/**
 * First-visit onboarding: pick your home subnation + role.
 *
 * Two-tier layout:
 *   - Top: Ireland / England (the two defaults; most populous)
 *   - "More options" expands to: Northern Ireland / Scotland / Wales
 *   - "Future expansion pack" shows Jersey / Guernsey / IoM as locked
 *     "coming soon" cards.
 *
 * Once both picks are made, calls `onComplete(session)` with the
 * onboarded session.
 */

import { useState } from "react";
import { DEFAULT_SUBNATIONS, AVAILABLE_SUBNATIONS, EXPANSION_SUBNATIONS, SUBNATIONS, type ActiveSubnation, type Role, type Cycle, type SubnationMeta } from "../../types/session";

export function OnboardingPicker({ onComplete }: { onComplete: (s: any) => void }) {
  const [step, setStep] = useState<"subnation" | "role" | "cycle" | "done">("subnation");
  const [subnation, setSubnation] = useState<ActiveSubnation | null>(null);
  const [showMore, setShowMore] = useState(false);
  const [role, setRole] = useState<Role | null>(null);
  const [cycle, setCycle] = useState<Cycle | null>(null);

  const sub = subnation ? SUBNATIONS.find((s) => s.code === subnation) : null;

  if (step === "subnation") {
    return (
      <div className="max-w-3xl mx-auto p-6 space-y-6">
        <header>
          <h1 className="text-3xl font-[var(--font-heading)] text-[var(--color-primary)]">
            Where are you studying or working?
          </h1>
          <p className="mt-2 text-sm text-[var(--color-text)]/70">
            One platform for the British Isles. Pick your home subnation —
            the content, the safeguarding policy, and the agent's voice all
            adapt to your answer. You can change it later.
          </p>
        </header>

        <div className="grid grid-cols-2 gap-4">
          {DEFAULT_SUBNATIONS.map((s) => (
            <SubnationCard
              key={s.code}
              sub={s}
              onClick={() => {
                setSubnation(s.code);
                setStep("role");
              }}
            />
          ))}
        </div>

        {!showMore ? (
          <button
            type="button"
            onClick={() => setShowMore(true)}
            className="w-full p-3 text-sm rounded border border-dashed text-[var(--color-text)]/60"
            style={{ borderColor: "var(--color-secondary)/30" }}
          >
            More options ▾
          </button>
        ) : (
          <div className="grid grid-cols-3 gap-3">
            {AVAILABLE_SUBNATIONS.map((s) => (
              <SubnationCard
                key={s.code}
                sub={s}
                onClick={() => {
                  setSubnation(s.code);
                  setStep("role");
                }}
                compact
              />
            ))}
          </div>
        )}

        <section>
          <h2 className="text-sm uppercase tracking-wide text-[var(--color-secondary)]/70 mt-6">
            Future expansion pack
          </h2>
          <p className="text-xs text-[var(--color-text)]/50 mb-2">
            Coming soon. We&apos;re building out the syllabi and safeguarding policy
            data for these subnations next.
          </p>
          <div className="grid grid-cols-3 gap-3 opacity-50">
            {EXPANSION_SUBNATIONS.map((s) => (
              <div
                key={s.code}
                className="p-3 rounded border text-center"
                style={{ borderColor: "var(--color-secondary)/20" }}
              >
                <div className="text-2xl">{s.flag}</div>
                <div className="font-[var(--font-heading)]">{s.name}</div>
                <div className="text-xs text-[var(--color-text)]/50 mt-1">Coming soon</div>
              </div>
            ))}
          </div>
        </section>
      </div>
    );
  }

  if (step === "role") {
    return (
      <div className="max-w-2xl mx-auto p-6 space-y-4">
        <header>
          <h1 className="text-2xl font-[var(--font-heading)] text-[var(--color-primary)]">
            Are you a…
          </h1>
          <p className="text-sm text-[var(--color-text)]/70">
            {sub?.flag} {sub?.name}. Different roles see different home pages.
          </p>
        </header>
        <div className="grid grid-cols-3 gap-3">
          {(["student", "parent", "teacher"] as Role[]).map((r) => (
            <button
              key={r}
              type="button"
              onClick={() => {
                setRole(r);
                setStep("cycle");
              }}
              className="p-6 rounded border text-center hover:shadow-md"
              style={{
                borderColor: "var(--color-primary)",
                background: "var(--color-background)",
              }}
            >
              <div className="font-[var(--font-heading)] text-xl capitalize">{r}</div>
              <div className="text-xs text-[var(--color-text)]/60 mt-2">
                {r === "student" && "Studying for JC / LC / GCSE / A-Level etc."}
                {r === "parent" && "Supporting your child at home"}
                {r === "teacher" && "Planning, marking, monitoring changes"}
              </div>
            </button>
          ))}
        </div>
      </div>
    );
  }

  if (step === "cycle" && sub) {
    return (
      <div className="max-w-2xl mx-auto p-6 space-y-4">
        <header>
          <h1 className="text-2xl font-[var(--font-heading)] text-[var(--color-primary)]">
            Which cycle?
          </h1>
          <p className="text-sm text-[var(--color-text)]/70">
            {sub.flag} {sub.name} runs these cycles:
          </p>
        </header>
        <div className="grid grid-cols-2 gap-3">
          {sub.cycles.map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => {
                setCycle(c);
                const finalCycle = c;
                const subMeta = sub;
                onComplete({
                  sessionId: `local-${Math.random().toString(36).slice(2, 10)}`,
                  userId: "anonymous",
                  subnation: subMeta.code,
                  role: role,
                  cycle: finalCycle,
                  selectedSubjects: [],
                  safeguardingSourceKey: subMeta.safeguardingSourceKey,
                  paletteSourceKey: subMeta.paletteSourceKey,
                  onboarded: true,
                  createdAt: new Date().toISOString(),
                  lastUsedAt: new Date().toISOString(),
                });
                setStep("done");
              }}
              className="p-4 rounded border hover:shadow-md capitalize"
              style={{
                borderColor: "var(--color-primary)",
                background: "var(--color-background)",
              }}
            >
              <div className="font-[var(--font-heading)] text-lg">
                {c.replace(/_/g, " ")}
              </div>
            </button>
          ))}
        </div>
      </div>
    );
  }

  return null;
}

function SubnationCard({ sub, onClick, compact = false }: { sub: SubnationMeta; onClick: () => void; compact?: boolean }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded border text-left hover:shadow-md transition ${compact ? "p-3" : "p-6"}`}
      style={{
        borderColor: "var(--color-primary)",
        background: "var(--color-background)",
      }}
    >
      <div className={`${compact ? "text-2xl" : "text-4xl"} mb-2`}>{sub.flag}</div>
      <div className={`font-[var(--font-heading)] ${compact ? "text-base" : "text-2xl"}`}>
        {sub.name}
      </div>
      <div className="text-xs text-[var(--color-text)]/60 mt-1">
        {sub.awardingBody} · {sub.awardingBodyShort}
      </div>
      {!compact && (
        <div className="text-xs text-[var(--color-text)]/50 mt-1">
          {sub.cycles.length} cycle{sub.cycles.length === 1 ? "" : "s"} available
        </div>
      )}
    </button>
  );
}
