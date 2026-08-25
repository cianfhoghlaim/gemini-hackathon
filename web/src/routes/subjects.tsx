import { createFileRoute } from "@tanstack/react-router";
import { SubjectCard } from "~/components/cards/SubjectCard";
import { usePalette } from "~/components/themes/SourcePaletteProvider";

const SAMPLE_SUBJECTS: Record<string, Array<{ slug: string; name: string; level: string }>> = {
  "ncca.ie": [
    { slug: "lc-maths-hl", name: "Mathematics", level: "LC Higher" },
    { slug: "lc-chemistry", name: "Chemistry", level: "LC Higher" },
    { slug: "lc-english", name: "English", level: "LC Higher" },
    { slug: "lc-geography", name: "Geography", level: "LC Higher" },
    { slug: "lc-cs", name: "Computer Science", level: "LC Higher" },
    { slug: "lc-gaeilge", name: "Gaeilge", level: "LC Higher" },
  ],
  "aqa.org.uk": [
    { slug: "aqa-a-level-maths", name: "A-Level Mathematics", level: "A-Level" },
    { slug: "aqa-gcse-chemistry", name: "GCSE Chemistry", level: "GCSE" },
    { slug: "aqa-a-level-english", name: "A-Level English Literature", level: "A-Level" },
  ],
};

export const Route = createFileRoute("/subjects")({
  component: SubjectsPage,
});

function SubjectsPage() {
  const { current } = usePalette();
  const subjects = current
    ? SAMPLE_SUBJECTS[current.sourceKey] ?? []
    : [];
  return (
    <div>
      <h2 className="text-3xl font-[var(--font-heading)] mb-6">
        Subjects{current ? ` - ${current.sourceName}` : ""}
      </h2>
      {subjects.length === 0 ? (
        <p className="text-[var(--color-secondary)]/60">
          No subjects yet for this source. Try one of the 8 main jurisdictions.
        </p>
      ) : (
        <div className="grid grid-cols-2 gap-3">
          {subjects.map((s) => (
            <SubjectCard
              key={s.slug}
              subject={s}
              sourceKey={current?.sourceKey ?? "ncca.ie"}
              palette={current ?? undefined}
            />
          ))}
        </div>
      )}
    </div>
  );
}
