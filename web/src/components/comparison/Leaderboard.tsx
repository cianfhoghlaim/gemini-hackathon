import { useEffect, useState } from "react";
import { useComparisonLeaderboard, type ComparisonRow } from "../../lib/duckdb";

export function ComparisonLeaderboard() {
  const { fetchLeaderboard } = useComparisonLeaderboard();
  const [rows, setRows] = useState<ComparisonRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchLeaderboard()
      .then(setRows)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [fetchLeaderboard]);

  if (loading) return <div className="text-sm text-[var(--color-text)]/60">Loading leaderboard…</div>;
  if (error) return <div className="text-sm text-[var(--color-secondary)]">{error}</div>;
  if (rows.length === 0)
    return (
      <div className="text-sm text-[var(--color-text)]/60">
        No model comparisons yet. Run <code className="font-mono">gemini-hackathon compare</code> to populate.
      </div>
    );

  return (
    <table style={{ width: "100%", fontSize: "0.875rem", borderCollapse: "collapse" }}>
      <thead>
        <tr style={{ textAlign: "left", borderBottom: "2px solid var(--color-primary)" }}>
          <th style={{ padding: "0.5rem" }}>Model</th>
          <th style={{ padding: "0.5rem" }}>Backend</th>
          <th style={{ padding: "0.5rem" }}>RAGAS</th>
          <th style={{ padding: "0.5rem" }}>Latency (ms)</th>
          <th style={{ padding: "0.5rem" }}>Cost (USD)</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row, i) => (
          <tr key={`${row.pdf_sha256}-${row.model_key}`} style={{ borderBottom: "1px solid var(--color-secondary)/20" }}>
            <td style={{ padding: "0.5rem", fontFamily: "var(--font-body)" }}>{row.model_key}</td>
            <td style={{ padding: "0.5rem" }}>{row.backend}</td>
            <td style={{ padding: "0.5rem", fontWeight: row.ragas_score >= 0.9 ? "bold" : "normal" }}>
              {(row.ragas_score * 100).toFixed(1)}%
            </td>
            <td style={{ padding: "0.5rem" }}>{row.latency_ms}</td>
            <td style={{ padding: "0.5rem" }}>${row.cost_usd.toFixed(4)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
