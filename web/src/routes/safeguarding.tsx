import { createFileRoute, useLoaderData } from "@tanstack/react-router";
import { usePalette } from "~/components/themes/SourcePaletteProvider";

interface SafeguardingEntry {
  sourceKey: string;
  sourceName: string;
  policyScope: string;
}

const ENTRIES: SafeguardingEntry[] = [
  { sourceKey: "gov.ie/education",         sourceName: "Ireland Dept of Education",   policyScope: "DEIS Plan 2017 + Well-Being Policy Statement" },
  { sourceKey: "gov.uk/dfe",               sourceName: "UK Dept for Education",        policyScope: "Keeping Children Safe in Education (KCSiE) 2026" },
  { sourceKey: "education.gov.scot",       sourceName: "Scotland Education",          policyScope: "Included, Engaged and Involved" },
  { sourceKey: "gov.wales/education",      sourceName: "Wales Education",             policyScope: "Keeping Learners Safe" },
  { sourceKey: "ccea.org.uk/safeguarding", sourceName: "CCEA Safeguarding (NI)",       policyScope: "Safeguarding and Child Protection" },
];

export const Route = createFileRoute("/safeguarding")({
  loader: () => ENTRIES,
  component: SafeguardingPage,
});

function SafeguardingPage() {
  const entries = useLoaderData({ from: "/safeguarding" }) as SafeguardingEntry[];
  const { current } = usePalette();
  const isSafeguarding = current?.sourceKey?.includes("/") ?? false;

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <header>
        <h2 className="text-3xl font-[var(--font-heading)] text-[var(--color-primary)]">
          Safeguarding policy context
        </h2>
        <p className="mt-2 text-sm text-[var(--color-text)]/70">
          Per-source child-protection policy scope. Click a safeguarding
          palette (any palette button with a "/" in its name) to see the
          active policy rendered against the active source.
        </p>
      </header>

      {!isSafeguarding && (
        <div
          className="rounded border p-4 text-sm"
          style={{
            borderColor: "var(--color-accent)",
            background: "var(--color-background)",
          }}
        >
          Switch to a safeguarding palette (gov.ie/education, gov.uk/dfe,
          education.gov.scot, gov.wales/education, ccea.org.uk/safeguarding)
          to see applied policy.
        </div>
      )}

      <section className="grid grid-cols-1 gap-3">
        {entries.map((e) => (
          <article
            key={e.sourceKey}
            className="rounded border p-4"
            style={{
              borderLeft: `4px solid ${current?.sourceKey === e.sourceKey ? "var(--color-primary)" : "var(--color-secondary)/30"}`,
              background: "var(--color-background)",
            }}
          >
            <header className="flex items-baseline justify-between">
              <h3 className="font-[var(--font-heading)] text-lg">{e.sourceName}</h3>
              <code className="text-xs text-[var(--color-secondary)]/60">{e.sourceKey}</code>
            </header>
            <p className="mt-2 text-sm">{e.policyScope}</p>
            {current?.sourceKey === e.sourceKey && (
              <p className="mt-2 text-xs italic text-[var(--color-primary)]">
                ↑ Active palette
              </p>
            )}
          </article>
        ))}
      </section>
    </div>
  );
}
