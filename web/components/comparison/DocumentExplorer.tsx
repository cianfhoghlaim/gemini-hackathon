import { useEffect, useState } from "react";
import { useDocumentExplorer, type DocumentRow } from "~/lib/duckdb";

export function DocumentExplorer() {
  const { fetchDocuments } = useDocumentExplorer();
  const [rows, setRows] = useState<DocumentRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDocuments()
      .then(setRows)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div>Loading document explorer…</div>;
  if (error) return <div style={{ color: "var(--color-secondary)" }}>{error}</div>;

  return (
    <table style={{ width: "100%", fontSize: "0.875rem", borderCollapse: "collapse" }}>
      <thead>
        <tr style={{ textAlign: "left", borderBottom: "1px solid var(--color-primary)" }}>
          <th style={{ padding: "0.5rem" }}>Source</th>
          <th style={{ padding: "0.5rem" }}>Subject</th>
          <th style={{ padding: "0.5rem" }}>Level</th>
          <th style={{ padding: "0.5rem" }}>Pages</th>
          <th style={{ padding: "0.5rem" }}>SHA-256</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={`${row.source_key}-${row.sha256_hash}`} style={{ borderBottom: "1px solid var(--color-secondary)/20" }}>
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
