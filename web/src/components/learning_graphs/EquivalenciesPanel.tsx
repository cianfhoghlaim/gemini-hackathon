/**
 * EquivalenciesPanel — Firestore-backed cell-level equivalency panel.
 *
 * Phase 5 of the OpenSpec change
 * [`2026-08-31-ncce-showcase-complete-v1`](../../../../openspec/changes/2026-08-31-ncce-showcase-complete-v1/proposal.md)
 * + Change B (`2026-08-31-learning-graph-equivalency-graph-v1`).
 *
 * Subscribes to the Firestore `cellEquivalents` collection (the
 * Phase 8 cross-walk destination from Change B's Dagster asset
 * group). Filters by jurisdiction = `UK_NCCE` (the canonical NCCE
 * showcase source) and limits to 50 records.
 *
 * Each row renders `(sourceCell, targetCell, targetJurisdiction,
 * confidence)` — the canonical schema from the Change B
 * `ExtractCellEquivalencies` BAML function. When Firestore is
 * unreachable (offline dev), the panel renders an empty-state hint
 * instead of crashing.
 */

import { useEffect, useState } from "react";
import { where, orderBy, limit } from "firebase/firestore";
import { subscribeCollection } from "../../lib/firestore.ts";

interface CellEquivalent {
  id: string;
  sourceCell?: string;
  sourceCellId?: string;
  targetCell?: string;
  targetCellId?: string;
  targetJurisdiction?: string;
  jurisdiction?: string;
  subject?: string;
  confidence?: number;
  notes?: string;
}

const SOURCE_JURISDICTION = "UK_NCCE";
const MAX_ROWS = 50;

export function EquivalenciesPanel() {
  const [rows, setRows] = useState<CellEquivalent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    try {
      const unsub = subscribeCollection<CellEquivalent>(
        "cellEquivalents",
        (data) => {
          setRows(data);
          setLoading(false);
        },
        [
          where("sourceJurisdiction", "==", SOURCE_JURISDICTION),
          orderBy("confidence", "desc"),
          limit(MAX_ROWS),
        ],
        (err) => {
          setError(String(err?.message ?? err));
          setLoading(false);
        },
      );
      return unsub;
    } catch (err) {
      setError(String((err as Error)?.message ?? err));
      setLoading(false);
      return undefined;
    }
  }, []);

  if (loading)
    return (
      <div className="text-sm text-[var(--color-text)]/60">
        Loading equivalencies…
      </div>
    );
  if (error)
    return (
      <div className="space-y-2">
        <div className="text-sm text-[var(--color-secondary)]">
          Could not load `cellEquivalents`: <code className="font-mono">{error}</code>
        </div>
        <div className="text-xs text-[var(--color-text)]/60">
          The cell-level equivalency Firestore collection is populated by the
          <code className="font-mono"> learning_graph_equivalency_graph </code>
          Dagster asset (Change B). Run{" "}
          <code className="font-mono">make ncce-extract</code> to populate it
          locally.
        </div>
      </div>
    );
  if (rows.length === 0)
    return (
      <div className="space-y-2">
        <div className="text-sm text-[var(--color-text)]/60">
          No <code className="font-mono">cellEquivalents</code> rows for{" "}
          <code className="font-mono">{SOURCE_JURISDICTION}</code> yet.
        </div>
        <div className="text-xs text-[var(--color-text)]/60">
          The 7-jurisdiction cell-level cross-walk is produced by the{" "}
          <code className="font-mono">
            orchestration/defs/3_model_lifecycle/uk_ncce_learning_graph_equivalencies.py
          </code>{" "}
          Dagster asset group (Change B). Run{" "}
          <code className="font-mono">make ncce-extract</code> + the Change B
          asset materialisation to populate the Firestore mirror.
        </div>
      </div>
    );

  return (
    <div className="space-y-2">
      <div className="text-xs text-[var(--color-text)]/60">
        Showing <strong>{rows.length}</strong> of <strong>{MAX_ROWS}</strong> max
        rows from <code className="font-mono">cellEquivalents</code> for source
        jurisdiction <code className="font-mono">{SOURCE_JURISDICTION}</code>.
      </div>
      <table
        style={{
          width: "100%",
          fontSize: "0.875rem",
          borderCollapse: "collapse",
        }}
      >
        <thead>
          <tr style={{ textAlign: "left", borderBottom: "2px solid var(--color-primary)" }}>
            <th style={{ padding: "0.5rem" }}>Source cell</th>
            <th style={{ padding: "0.5rem" }}>Target jurisdiction</th>
            <th style={{ padding: "0.5rem" }}>Target cell</th>
            <th style={{ padding: "0.5rem" }}>Subject</th>
            <th style={{ padding: "0.5rem" }}>Confidence</th>
            <th style={{ padding: "0.5rem" }}>Notes</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={row.id}
              style={{ borderBottom: "1px solid var(--color-secondary)/20" }}
            >
              <td style={{ padding: "0.5rem", fontFamily: "monospace" }}>
                {row.sourceCellId ?? row.sourceCell ?? row.id}
              </td>
              <td style={{ padding: "0.5rem" }}>
                {row.targetJurisdiction ?? row.jurisdiction ?? "—"}
              </td>
              <td style={{ padding: "0.5rem", fontFamily: "monospace" }}>
                {row.targetCellId ?? row.targetCell ?? "—"}
              </td>
              <td style={{ padding: "0.5rem" }}>{row.subject ?? "—"}</td>
              <td style={{ padding: "0.5rem" }}>
                {typeof row.confidence === "number"
                  ? row.confidence.toFixed(2)
                  : "—"}
              </td>
              <td style={{ padding: "0.5rem" }}>
                {row.notes ?? <span className="text-[var(--color-text)]/40">—</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default EquivalenciesPanel;
