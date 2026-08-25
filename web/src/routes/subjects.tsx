/**
 * Per-subnation subjects page.
 *
 * Filters SUBJECT_CATALOGUE to the active subnation + cycle. Cross-
 * national subjects are NOT shown by default — use the "Find resources
 * that help" feature to surface those.
 */

import { createFileRoute, Link } from "@tanstack/react-router";
import { useSession } from "../components/session/SessionContext";
import { SUBJECT_CATALOGUE } from "../types/session";

export const Route = createFileRoute("/subjects")({
  component: SubjectsPage,
});

function SubjectsPage() {
  const { subnation, session } = useSession();
  const subjects = (SUBJECT_CATALOGUE[subnation.code] ?? []).filter(
    (s) => !session?.cycle || s.cycle === session.cycle,
  );

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      <header>
        <h1 className="text-3xl font-[var(--font-heading)] text-[var(--color-primary)]">
          {subnation.flag} {subnation.name} subjects
        </h1>
        <p className="mt-2 text-sm text-[var(--color-text)]/70">
          {subjects.length} subjects in your selected cycle
          {session?.cycle && (
            <> ({session.cycle.replace(/_/g, " ")})</>
          )}.
          Awarding body: <strong>{subnation.awardingBody}</strong>.
        </p>
      </header>

      {subjects.length === 0 ? (
        <p className="text-sm text-[var(--color-text)]/60 text-center py-8">
          No subjects found for {subnation.name} in this cycle. Try a
          different cycle in the home settings.
        </p>
      ) : (
        <section className="grid grid-cols-2 gap-3">
          {subjects.map((s) => (
            <Link
              key={`${s.sourceKey}-${s.cycle}-${s.name}`}
              to="/find-resources"
              search={{ subject: s.name }}
              className="block p-4 rounded border hover:shadow-md transition"
              style={{
                borderLeft: "4px solid var(--color-primary)",
                background: "var(--color-background)",
              }}
            >
              <h2 className="font-[var(--font-heading)] text-lg">{s.name}</h2>
              <p className="text-xs text-[var(--color-text)]/60 mt-1">
                {s.cycle.replace(/_/g, " ")}
                {s.examBoard && ` · ${s.examBoard}`}
              </p>
              <p className="text-xs text-[var(--color-secondary)] mt-2">
                Find resources that help →
              </p>
            </Link>
          ))}
        </section>
      )}

      <p className="text-xs text-[var(--color-text)]/50 text-center pt-4">
        Looking for resources from other nations?{" "}
        <Link to="/find-resources" className="underline">
          Use Find resources that help
        </Link>
        .
      </p>
    </div>
  );
}
