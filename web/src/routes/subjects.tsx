import { useSession } from "../components/session/SessionContext";
import { MarimoEmbed } from "../components/marimo/MarimoEmbed";
import { Link } from "react-router-dom";

function SubjectsPage() {
  const { subnation, session } = useSession();
  // The subjects catalogue is loaded from the Phase-3 sources module.
  // In dev we render a small fallback so the page works without the
  // full backend. When the DLT pipeline is wired, replace this with
  // a fetch from `/api/subjects?subnation=<code>`.
  const subjects = [
    { slug: "mathematics", name: "Mathematics" },
    { slug: "english",    name: "English" },
    { slug: "gaeilge",    name: "Gaeilge" },
    { slug: "chemistry",  name: "Chemistry" },
    { slug: "physics",    name: "Physics" },
    { slug: "biology",    name: "Biology" },
    { slug: "geography",  name: "Geography" },
    { slug: "history",    name: "History" },
  ];

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <header>
        <h1 className="text-3xl font-[var(--font-heading)] text-[var(--color-primary)]">
          {subnation.flag} {subnation.name} subjects
        </h1>
        <p className="mt-2 text-sm text-[var(--color-text)]/70">
          Click a subject to open the interactive teaching notebook
          (powered by marimo, runs in your browser via WebAssembly).
        </p>
      </header>

      <section className="grid grid-cols-2 gap-3">
        {subjects.map((s) => (
          <Link
            key={s.slug}
            to={`/subjects/${s.slug}`}
            className="block p-4 rounded border hover:shadow-md transition"
            style={{
              borderColor: "var(--color-secondary)/20",
              background: "var(--color-background)",
            }}
          >
            <h2 className="font-[var(--font-heading)] text-lg">{s.name}</h2>
            <p className="text-xs text-[var(--color-text)]/60 mt-1">
              Interactive notebook → syllabus + past papers + AI suggestions
            </p>
          </Link>
        ))}
      </section>
    </div>
  );
}

export default SubjectsPage;
