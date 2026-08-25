import { createFileRoute } from "@tanstack/react-router";
import { usePalette } from "~/components/themes/SourcePaletteProvider";

interface EquivalentRow {
  sourceTopic: string;
  equivalents: Record<string, string>;
}

// Hard-coded Mathematics equivalencies across the 8 BI jurisdictions
const MATH_EQUIVALENCIES: EquivalentRow[] = [
  {
    sourceTopic: "Algebra & Functions",
    equivalents: {
      Ireland: "Algebra & Functions",
      England_AQA: "Algebra and functions",
      England_OCR: "Algebra",
      England_Pearson: "Pure Mathematics 1 - Algebra",
      Scotland: "Expressions and Functions",
      Wales: "Algebra and Functions",
      NI: "Algebra",
      IoM: "GCSE Mathematics (EdExcel International)",
    },
  },
  {
    sourceTopic: "Complex Numbers",
    equivalents: {
      Ireland: "Complex Numbers",
      England_AQA: "Complex numbers (A-Level Further)",
      England_OCR: "Complex numbers",
      England_Pearson: "Pure 2 - Complex numbers",
      Scotland: "Complex numbers (AH)",
      Wales: "Complex numbers",
      NI: "Complex numbers (A2)",
      IoM: "A-Level Further Maths",
    },
  },
  {
    sourceTopic: "Calculus (Differentiation & Integration)",
    equivalents: {
      Ireland: "Differentiation & Integration",
      England_AQA: "Calculus",
      England_OCR: "Calculus",
      England_Pearson: "Pure 2 - Calculus",
      Scotland: "Differentiation & Integration",
      Wales: "Calculus",
      NI: "Calculus",
      IoM: "Calculus",
    },
  },
];

export const Route = createFileRoute("/equivalency")({
  component: EquivalencyPage,
});

function EquivalencyPage() {
  const { current } = usePalette();
  const targetKey =
    current?.sourceKey ?? "ncca.ie";
  return (
    <div className="max-w-5xl">
      <h2 className="text-3xl font-[var(--font-heading)] mb-6">
        Cross-Jurisdiction Equivalencies
      </h2>
      <p className="mb-4 text-sm text-[var(--color-secondary)]/70">
        Mathematics topics aligned across {current?.jurisdiction ?? "the BI jurisdictions"}.
        Source jurisdiction: <strong>{targetKey}</strong>
      </p>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left border-b border-[var(--color-primary)]">
            <th className="py-2 pr-4">Source (Ireland LC)</th>
            <th className="py-2 pr-4">
              Equivalent in {current?.sourceName.split(" - ")[0] ?? "selected source"}
            </th>
          </tr>
        </thead>
        <tbody>
          {MATH_EQUIVALENCIES.map((row) => (
            <tr
              key={row.sourceTopic}
              className="border-b border-[var(--color-secondary)]/10"
            >
              <td className="py-2 pr-4 font-mono">{row.sourceTopic}</td>
              <td className="py-2 pr-4">
                {row.equivalents[
                  (
                    Object.keys(row.equivalents).find((k) =>
                      k
                        .toLowerCase()
                        .includes(targetKey.split(".")[0].toLowerCase()),
                    ) ?? "Ireland"
                  ) as keyof typeof row.equivalents
                ] ?? "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
