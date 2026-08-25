import { createFileRoute } from "@tanstack/react-router";
import { usePalette } from "~/components/themes/SourcePaletteProvider";

const POLICY_NAMES: Record<string, string> = {
  "gov.ie/education": "DEIS Plan 2017 + Well-Being Policy Statement",
  "gov.uk/dfe": "Keeping Children Safe in Education (KCSiE) 2026",
  "education.gov.scot": "Included, Engaged and Involved",
  "gov.wales/education": "Keeping Learners Safe",
  "ccea.org.uk/safeguarding": "Safeguarding and Child Protection",
};

export const Route = createFileRoute("/safeguarding")({
  component: SafeguardingPage,
});

function SafeguardingPage() {
  const { current } = usePalette();
  if (!current) return null;
  const isSafeguarding = current.policyScope !== undefined;
  const policyName =
    POLICY_NAMES[current.sourceKey] ??
    "Adopt the active palette to view safeguarding context.";
  return (
    <div className="max-w-3xl">
      <h2 className="text-3xl font-[var(--font-heading)] mb-2">
        Safeguarding context
      </h2>
      <p className="text-sm text-[var(--color-secondary)]/70 mb-6">
        {current.sourceName}
        {current.policyScope ? ` - ${current.policyScope}` : ""}
      </p>
      {isSafeguarding ? (
        <article
          className="prose p-6 rounded-lg"
          style={{
            borderLeft: `4px solid var(--color-primary)`,
            background: "var(--color-background)",
          }}
        >
          <h3 className="text-xl font-[var(--font-heading)] mb-2">
            {policyName}
          </h3>
          <p className="text-sm">
            The active palette reflects this safeguarding body's brand colours,
            typography, and policy scope. Educational content presented in this
            jurisdiction should be filtered against this policy context.
          </p>
        </article>
      ) : (
        <p>
          Switch to a safeguarding palette (gov.ie/education, gov.uk/dfe,
          education.gov.scot, gov.wales/education, or ccea.org.uk/safeguarding)
          via the buttons on the home page to view applied safeguarding
          context.
        </p>
      )}
    </div>
  );
}
