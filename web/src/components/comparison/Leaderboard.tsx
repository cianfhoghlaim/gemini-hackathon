/**
 * Firestore-backed leaderboard — replaces the DuckDB-WASM comparison leaderboard.
 *
 * The `certificateComparisons` collection holds the 30-cell matrix
 * (6 subnations × 5 stages × 7 backends — Phase 6). This component
 * renders the leaderboard via realtime Firestore subscriptions.
 *
 * The 280-cell perTopicAssets comparison is loaded separately via
 * `firestoreQueries.subscribePerTopicAssets` (see `web/src/lib/firestore.ts`).
 */

import { useEffect, useState } from "react";
import { subscribeCertificateComparisons } from "../../lib/firestore";

interface ComparisonRow {
  id: string;
  subnation: string;
  stage: string;
  backend: string;
  modelKey: string;
  judgeScore: number;
  costUsd: number;
  latencyMs: number;
  paletteFidelity: number;
}

export function ComparisonLeaderboard() {
  const [rows, setRows] = useState<ComparisonRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const unsub = subscribeCertificateComparisons(
      "ireland",         // default subnation (the active session's value comes via useSession)
      "scoil_sinsearach", // default stage
      (data: unknown[]) => {
        setRows(data as ComparisonRow[]);
        setLoading(false);
      },
      (err) => {
        setError(String(err));
        setLoading(false);
      },
    );
    return unsub;
  }, []);

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
          <th style={{ padding: "0.5rem" }}>Judge</th>
          <th style={{ padding: "0.5rem" }}>Latency (ms)</th>
          <th style={{ padding: "0.5rem" }}>Cost (USD)</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.id} style={{ borderBottom: "1px solid var(--color-secondary)/20" }}>
            <td style={{ padding: "0.5rem", fontFamily: "var(--font-body)" }}>{row.modelKey}</td>
            <td style={{ padding: "0.5rem" }}>{row.backend}</td>
            <td style={{ padding: "0.5rem", fontWeight: row.judgeScore >= 4 ? "bold" : "normal" }}>
              {row.judgeScore.toFixed(1)}/5
            </td>
            <td style={{ padding: "0.5rem" }}>{row.latencyMs}</td>
            <td style={{ padding: "0.5rem" }}>${row.costUsd.toFixed(4)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}