import { createFileRoute, useLoaderData } from "@tanstack/react-router";
import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { SubjectCard } from "~/components/cards/SubjectCard";
import { usePalette } from "~/components/themes/SourcePaletteProvider";

interface SubjectRow {
  sourceKey: string;
  jurisdiction: string;
  subjectSlug: string;
  subjectName: string;
  level: string;
}

function loadSubjects(): SubjectRow[] {
  // The canonical sample lives at <repo>/data/syllabi/index.json.
  // At dev time, web/ is one level deep so we walk up.
  const candidates = [
    join(process.cwd(), "..", "data", "syllabi", "index.json"),
    join(process.cwd(), "data", "syllabi", "index.json"),
    join(process.cwd(), "..", "..", "data", "syllabi", "index.json"),
  ];
  for (const path of candidates) {
    if (existsSync(path)) {
      try {
        const data = JSON.parse(readFileSync(path, "utf-8"));
        return data.subjects ?? [];
      } catch {
        return [];
      }
    }
  }
  return [];
}

export const Route = createFileRoute("/subjects")({
  loader: loadSubjects,
  component: SubjectsPage,
});

function SubjectsPage() {
  const subjects = useLoaderData({ from: "/subjects" }) as SubjectRow[];
  const { current } = usePalette();

  // Group by jurisdiction for the layout.
  const grouped: Record<string, SubjectRow[]> = {};
  for (const s of subjects) {
    if (!grouped[s.jurisdiction]) grouped[s.jurisdiction] = [];
    grouped[s.jurisdiction].push(s);
  }
  const jurisdictionOrder = Object.keys(grouped).sort();

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      <header>
        <h2 className="text-3xl font-[var(--font-heading)] text-[var(--color-primary)]">
          Subjects
          <span className="ml-3 text-base font-[var(--font-body)] text-[var(--color-secondary)]/60">
            {subjects.length} across {jurisdictionOrder.length} jurisdictions
          </span>
        </h2>
        <p className="mt-2 text-sm text-[var(--color-text)]/70">
          Sampled from the canonical syllabus PDFs at{" "}
          <code>data/syllabi/index.json</code>.
          In production, this table is populated by{" "}
          <code>dlt_pipelines/official_doc_fetcher.py</code> from the 134 LC
          PDFs at <code>/Users/cianmacdeisigh/dev/cianchosaint/leaving_certificate/</code>.
        </p>
      </header>

      {subjects.length === 0 ? (
        <div
          className="rounded border p-6 text-center"
          style={{ borderColor: "var(--color-secondary)/20" }}
        >
          <p className="text-[var(--color-secondary)]/60">
            No subjects loaded. Run{" "}
            <code className="font-mono">scripts/compare_demo.py</code> to populate the
            sample dataset.
          </p>
        </div>
      ) : (
        jurisdictionOrder.map((j) => (
          <section key={j}>
            <h3 className="text-xl font-[var(--font-heading)] mb-3">{j}</h3>
            <div className="grid grid-cols-2 gap-3">
              {grouped[j].map((s) => (
                <SubjectCard
                  key={`${s.sourceKey}-${s.subjectSlug}`}
                  subject={{ slug: s.subjectSlug, name: s.subjectName, level: s.level }}
                  sourceKey={s.sourceKey}
                  palette={current ?? null}
                />
              ))}
            </div>
          </section>
        ))
      )}
    </div>
  );
}
