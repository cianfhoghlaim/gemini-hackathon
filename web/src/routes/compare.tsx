import { ComparisonLeaderboard } from "../components/comparison/Leaderboard";
import { DocumentExplorer } from "../components/comparison/DocumentExplorer";

function ComparePage() {
  return (
    <div className="max-w-6xl mx-auto space-y-8">
      <header>
        <h1 className="text-3xl font-[var(--font-heading)] text-[var(--color-primary)]">
          Gemini vs Gemma 4 — Live comparison
        </h1>
        <p className="mt-2 text-sm text-[var(--color-secondary)]/70">
          Every extraction is run under the same BAML function, scored by the same
          RAGAS-fidelity rubric, and persisted to DuckDB. This page reads the same
          DuckDB file in your browser via <code>@duckdb/duckdb-wasm</code> — same
          SQL dialect as the server-side DuckDB.
        </p>
      </header>

      <section>
        <h2 className="text-2xl font-[var(--font-heading)] mb-4">Model leaderboard</h2>
        <ComparisonLeaderboard />
      </section>

      <section>
        <h2 className="text-2xl font-[var(--font-heading)] mb-4">Document explorer</h2>
        <DocumentExplorer />
      </section>
    </div>
  );
}

export default ComparePage;
