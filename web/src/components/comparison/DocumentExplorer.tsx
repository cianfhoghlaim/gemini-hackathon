/**
 * Firestore-backed document explorer — replaces the DuckDB-WASM
 * `official_documents` table access with a Firestore realtime query.
 *
 * The Firestore collection name is `documents` (or `palettes` —
 * see the schema definition in `firestore.rules`).
 */

import { useEffect, useState } from "react";
import { subscribeCollection } from "../../lib/firestore.ts";

interface DocRow {
  id: string;
  source_key: string;
  pdf_path: string;
  page_count: number;
  sha256_hash: string;
  subject: string;
  level: string;
  jurisdiction: string;
}

export function DocumentExplorer() {
  const [rows, setRows] = useState<DocRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const unsub = subscribeCollection<DocRow>(
      "documents",
      (data) => {
        setRows(data);
        setLoading(false);
      },
      [],
      (err) => {
        setError(String(err));
        setLoading(false);
      },
    );
    return unsub;
  }, []);

  if (loading) return <div className="text-sm text-[var(--color-text)]/60">Loading document explorer…</div>;
  if (error) return <div className="text-sm text-[var(--color-secondary)]">{error}</div>;
  if (rows.length === 0)
    return (
      <div className="text-sm text-[var(--color-text)]/60">
        No official_documents rows yet. Run <code className="font-mono">dlt_pipelines/official_doc_fetcher</code> to populate.
      </div>
    );

  return (
    <table style={{ width: "100%", fontSize: "0.875rem", borderCollapse: "collapse" }}>
      <thead>
        <tr style={{ textAlign: "left", borderBottom: "2px solid var(--color-primary)" }}>
          <th style={{ padding: "0.5rem" }}>Source</th>
          <th style={{ padding: "0.5rem" }}>Subject</th>
          <th style={{ padding: "0.5rem" }}>Level</th>
          <th style={{ padding: "0.5rem" }}>Pages</th>
          <th style={{ padding: "0.5rem" }}>SHA-256</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.id} style={{ borderBottom: "1px solid var(--color-secondary)/20" }}>
            <td style={{ padding: "0.5rem" }}>{row.source_key}</td>
            <td style={{ padding: "0.5rem" }}>{row.subject}</td>
            <td style={{ padding: "0.5rem" }}>{row.level}</td>
            <td style={{ padding: "0.5rem" }}>{row.page_count}</td>
            <td style={{ padding: "0.5rem", fontFamily: "monospace", fontSize: "0.75rem" }}>
              {row.sha256_hash.slice(0, 12)}…
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}