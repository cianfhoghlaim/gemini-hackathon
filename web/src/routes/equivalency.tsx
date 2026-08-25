import { createFileRoute, useLoaderData } from "@tanstack/react-router";
import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { usePalette } from "~/components/themes/SourcePaletteProvider";

interface EquivalencyRow {
  sourceTopic: string;
  equivalents: Record<string, string>;
}

interface EquivalencyFile {
  subjects: string[];
  rows: EquivalencyRow[];
}

function loadEquivalencies(): EquivalencyFile {
  const candidates = [
    join(process.cwd(), "..", "data", "equivalencies", "mathematics.json"),
    join(process.cwd(), "data", "equivalencies", "mathematics.json"),
  ];
  for (const path of candidates) {
    if (existsSync(path)) {
      try {
        return JSON.parse(readFileSync(path, "utf-8"));
      } catch {
        break;
      }
    }
  }
  // Fallback: hard-coded Mathematics equivalencies.
  return {
    subjects: [
      "Ireland", "England (AQA)", "England (OCR)", "England (Pearson)",
      "Scotland", "Wales", "Northern Ireland", "Jersey", "Guernsey", "Isle of Man",
    ],
    rows: [
      {
        sourceTopic: "Algebra & Functions",
        equivalents: {
          "Ireland": "Algebra & Functions",
          "England (AQA)": "Algebra and functions",
          "England (OCR)": "Algebra",
          "England (Pearson)": "Pure Mathematics 1 — Algebra",
          "Scotland": "Expressions and Functions",
          "Wales": "Algebra and Functions",
          "Northern Ireland": "Algebra",
          "Jersey": "GCSE Mathematics (Edexcel International)",
          "Guernsey": "GCSE Mathematics",
          "Isle of Man": "GCSE Mathematics (Edexcel International)",
        },
      },
      {
        sourceTopic: "Complex Numbers",
        equivalents: {
          "Ireland": "Complex Numbers",
          "England (AQA)": "Complex numbers (A-Level Further)",
          "England (OCR)": "Complex numbers",
          "England (Pearson)": "Pure 2 — Complex numbers",
          "Scotland": "Complex numbers (AH)",
          "Wales": "Complex numbers",
          "Northern Ireland": "Complex numbers (A2)",
          "Jersey": "A-Level Further Maths",
          "Guernsey": "A-Level Further Maths",
          "Isle of Man": "A-Level Further Maths",
        },
      },
      {
        sourceTopic: "Calculus (Differentiation & Integration)",
        equivalents: {
          "Ireland": "Differentiation & Integration",
          "England (AQA)": "Calculus",
          "England (OCR)": "Calculus",
          "England (Pearson)": "Pure 2 — Calculus",
          "Scotland": "Differentiation & Integration",
          "Wales": "Calculus",
          "Northern Ireland": "Calculus",
          "Jersey": "Calculus",
          "Guernsey": "Calculus",
          "Isle of Man": "Calculus",
        },
      },
      {
        sourceTopic: "Mechanics (Forces, Motion, Momentum)",
        equivalents: {
          "Ireland": "Forces & Motion",
          "England (AQA)": "Mechanics",
          "England (OCR)": "Mechanics",
          "England (Pearson)": "Applied 1 — Mechanics",
          "Scotland": "Mechanics",
          "Wales": "Mechanics",
          "Northern Ireland": "Mechanics",
          "Jersey": "Mechanics",
          "Guernsey": "Mechanics",
          "Isle of Man": "Mechanics",
        },
      },
      {
        sourceTopic: "Statistics & Probability",
        equivalents: {
          "Ireland": "Probability & Statistics",
          "England (AQA)": "Statistics",
          "England (OCR)": "Statistics",
          "England (Pearson)": "Applied 1 — Statistics",
          "Scotland": "Statistics",
          "Wales": "Statistics",
          "Northern Ireland": "Statistics",
          "Jersey": "Statistics",
          "Guernsey": "Statistics",
          "Isle of Man": "Statistics",
        },
      },
    ],
  };
}

export const Route = createFileRoute("/equivalency")({
  loader: loadEquivalencies,
  component: EquivalencyPage,
});

function EquivalencyPage() {
  const data = useLoaderData({ from: "/equivalency" }) as EquivalencyFile;
  const { current } = usePalette();
  const targetKey =
    current?.jurisdiction?.replace(/\s*\(.+\)/, "").toLowerCase().trim()
    ?? "ireland";

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      <header>
        <h2 className="text-3xl font-[var(--font-heading)] text-[var(--color-primary)]">
          Mathematics equivalencies across the British Isles
        </h2>
        <p className="mt-2 text-sm text-[var(--color-text)]/70">
          Source jurisdiction: <strong>{current?.jurisdiction ?? "Ireland"}</strong>.
          Equivalencies cross-mapped from Ireland's NCCA LC Mathematics to
          England (3 boards), Scotland, Wales, NI, Jersey, Guernsey, and the
          Isle of Man.
        </p>
      </header>

      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="text-left border-b-2 border-[var(--color-primary)]">
            <th className="py-2 pr-4">Topic (Ireland LC)</th>
            {data.subjects.map((j) => (
              <th key={j} className="py-2 pr-4 text-xs">
                {j}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.rows.map((row) => (
            <tr
              key={row.sourceTopic}
              className="border-b border-[var(--color-secondary)]/10"
            >
              <td className="py-2 pr-4 font-mono">{row.sourceTopic}</td>
              {data.subjects.map((j) => (
                <td key={j} className="py-2 pr-4">
                  {row.equivalents[j] ?? "—"}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
