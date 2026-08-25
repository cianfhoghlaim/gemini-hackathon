/**
 * Per-subnation safeguarding policy page.
 *
 * Prominently shows the active subnation's policy. Other subnations'
 * policies are behind an "all 8 subnations" expander.
 */

import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useSession } from "../components/session/SessionContext";
import { SUBNATIONS } from "../types/session";

const POLICY_NAMES: Record<string, string> = {
  ireland: "DEIS Plan 2017 + Well-Being Policy Statement",
  england: "Keeping Children Safe in Education (KCSiE) 2026",
  northern_ireland: "Safeguarding and Child Protection (CCEA / DE)",
  scotland: "Included, Engaged and Involved (Part 1)",
  wales: "Keeping Learners Safe (Welsh Government guidance)",
};

const POLICY_SUMMARIES: Record<string, string> = {
  ireland:
    "Ireland's DEIS (Delivering Equality of Opportunity in Schools) plan supports schools in communities with high concentrations of disadvantage. The Well-Being Policy Statement (2018-2023) sets out the Department of Education's framework for promoting well-being in schools.",
  england:
    "KCSiE 2026 is the statutory safeguarding guidance that all schools and colleges in England must follow. It covers online safety, peer-on-peer abuse, mental health, and the role of the designated safeguarding lead.",
  northern_ireland:
    "Northern Ireland's safeguarding policy (under CCEA / DENI) requires schools to follow the Department of Education's 'Safeguarding and Child Protection - A Guide for Schools' (2024).",
  scotland:
    "Scotland's 'Included, Engaged and Involved' guidance (2015) is the national approach to behaviour and attendance. The National Guidance for Child Protection in Scotland (2021) underpins the safeguarding regime.",
  wales:
    "Wales' 'Keeping Learners Safe' guidance (updated 2025) sets out the safeguarding responsibilities of schools, further education colleges, and local authorities under the Social Services and Well-being (Wales) Act 2014.",
};

export const Route = createFileRoute("/safeguarding")({
  component: SafeguardingPage,
});

function SafeguardingPage() {
  const { subnation } = useSession();
  const [showAll, setShowAll] = useState(false);

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <header>
        <h1 className="text-3xl font-[var(--font-heading)] text-[var(--color-primary)]">
          {subnation.flag} {subnation.name} safeguarding
        </h1>
        <p className="mt-2 text-sm text-[var(--color-text)]/70">
          The policy in effect for your home subnation. This is the policy
          the agent composes into every system prompt.
        </p>
      </header>

      <article
        className="rounded border p-6 space-y-3"
        style={{
          borderLeft: "6px solid var(--color-primary)",
          background: "var(--color-background)",
        }}
      >
        <h2 className="text-2xl font-[var(--font-heading)]">
          {POLICY_NAMES[subnation.code] ?? `${subnation.name} safeguarding policy`}
        </h2>
        <p className="text-sm">
          <strong>Awarding body:</strong> {subnation.awardingBody}
        </p>
        <p className="text-sm">
          <strong>Source:</strong> <code>{subnation.safeguardingSourceKey}</code>
        </p>
        <p className="text-sm text-[var(--color-text)]/80">
          {POLICY_SUMMARIES[subnation.code] ?? "(Stub: the canonical safeguarding policy text for this subnation will be loaded from the BAML pipeline in production.)"}
        </p>
      </article>

      <p className="text-sm text-center">
        <button
          onClick={() => setShowAll((s) => !s)}
          className="text-[var(--color-secondary)] underline"
        >
          {showAll ? "Hide" : "Show"} the other 7 subnations' policies
        </button>
      </p>

      {showAll && (
        <section className="grid grid-cols-1 gap-3">
          {SUBNATIONS.filter((s) => s.code !== subnation.code).map((s) => (
            <article
              key={s.code}
              className="rounded border p-4 opacity-80"
              style={{ borderColor: "var(--color-secondary)/20" }}
            >
              <h3 className="font-[var(--font-heading)] text-lg">
                {s.flag} {s.name}
              </h3>
              <p className="text-sm text-[var(--color-text)]/70">
                {POLICY_NAMES[s.code] ?? `${s.name} safeguarding policy`}
              </p>
              <p className="text-xs text-[var(--color-text)]/50 mt-1">
                {POLICY_SUMMARIES[s.code] ?? "(Stub.)"}
              </p>
            </article>
          ))}
        </section>
      )}
    </div>
  );
}
