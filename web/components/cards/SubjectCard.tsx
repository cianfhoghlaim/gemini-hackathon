import type { PaletteData } from "~/components/themes/SourcePaletteProvider";

export interface SubjectCardProps {
  subject: {
    slug: string;
    name: string;
    level: string;
    syllabus_url?: string;
  };
  sourceKey: string;
  palette?: PaletteData | null;
}

export function SubjectCard({ subject, sourceKey, palette }: SubjectCardProps) {
  return (
    <article
      className="subject-card"
      style={{
        borderLeft: "4px solid var(--color-primary)",
        background: "var(--color-background)",
        color: "var(--color-text)",
        padding: "1rem",
        margin: "0.5rem 0",
        borderRadius: "0.25rem",
        boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
      }}
    >
      <header style={{ display: "flex", alignItems: "baseline", gap: "0.5rem" }}>
        <h3 style={{ margin: 0, fontFamily: "var(--font-heading)" }}>
          {subject.name}
        </h3>
        <span style={{ fontSize: "0.875rem", color: "var(--color-secondary)" }}>
          {subject.level}
        </span>
        {palette?.flag && (
          <span aria-hidden="true" style={{ marginLeft: "auto" }}>
            {palette.flag}
          </span>
        )}
      </header>
      <footer style={{ marginTop: "0.5rem", fontSize: "0.875rem" }}>
        <a
          href={`/subjects/${sourceKey}/${subject.slug}`}
          style={{ color: "var(--color-primary)" }}
        >
          View syllabus →
        </a>
      </footer>
    </article>
  );
}
