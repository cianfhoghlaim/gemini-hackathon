/**
 * PedagogyOverlay — Firestore-backed 12 NCCE pedagogy principles overlay.
 *
 * Phase 5 of the OpenSpec change
 * [`2026-08-31-ncce-showcase-complete-v1`](../../../../openspec/changes/2026-08-31-ncce-showcase-complete-v1/proposal.md)
 * + Change C (`2026-08-31-pedagogy-overlay-renderer-v1`).
 *
 * Subscribes to the Firestore `annotatedLearningGraphs` collection
 * (the canonical Change C destination) and renders the 12 NCCE
 * pedagogy principles as coloured badges overlaid on the learning
 * graph cells.
 *
 * The 12 canonical NCCE pedagogy principles (per the disk cache at
 * `data/bi_ep/syllabi_md/uk_ncce/pedagogy_principles.json`) each get
 * a stable colour hash so the badge palette is consistent across
 * sessions.
 *
 * When Firestore is unreachable (offline dev), the panel falls back
 * to the disk-cached 12 principles so the showcase still renders.
 */

import { useEffect, useMemo, useState } from "react";
import { where, orderBy, limit } from "firebase/firestore";
import { subscribeCollection } from "../../lib/firestore.ts";

interface AnnotatedLearningGraph {
  id: string;
  graphId?: string;
  subject?: string;
  graph?: {
    id?: string;
    subject?: string;
    rows?: Array<{ id: string; label?: string }>;
    columns?: Array<{ id: string; label?: string }>;
    cells?: Array<{
      id: string;
      row_id?: string;
      column_id?: string;
      skill_description?: string;
    }>;
  };
  cell_annotations?: Record<string, string[]>;
  cellAnnotations?: Record<string, string[]>;
  pedagogy_source?: string;
}

interface PrincipleMeta {
  id: string;
  name: string;
  summary: string;
  how_to_apply: string;
  color: string;
}

// Stable palette (the 12 British Isles 5-stage palette + extras).
const PALETTE: ReadonlyArray<string> = [
  "#00733B", // NCCA green
  "#1e80c6", // Bunscoil sea-blue
  "#28955e", // MeanScoil meadow-green
  "#cc9966", // Scoil Sinsearach harvest-gold
  "#5a4fcf", // Ollscoil scholarship-indigo
  "#a83a2a", // Crimson
  "#e8915c", // Aistear dawn-orange
  "#5c2c0c", // Aistear ink
  "#7ab5d8", // Bunscoil soft
  "#7cc09c", // MeanScoil soft
  "#e3c2a0", // Scoil Sinsearach soft
  "#9b93e6", // Ollscoil soft
];

const CANONICAL_PRINCIPLES: ReadonlyArray<{ id: string; name: string; summary: string }> = [
  { id: "primm", name: "PRIMM", summary: "Predict → Run → Investigate → Modify → Make" },
  { id: "pair_programming", name: "Pair programming", summary: "Two students at one keyboard" },
  { id: "semantic_waves", name: "Semantic waves", summary: "Cycle concrete ↔ abstract" },
  { id: "lead_with_concepts", name: "Lead with concepts", summary: "Anchor new ideas in prior knowledge" },
  { id: "live_coding", name: "Live coding", summary: "Teacher writes code in front of the class" },
  { id: "worked_examples", name: "Worked examples", summary: "Show fully worked solutions first" },
  { id: "formative_assessment", name: "Formative assessment", summary: "Mini-checks every 10-15 minutes" },
  { id: "talking_points", name: "Talking points", summary: "Structured partner-talk prompts" },
  { id: "unplugged_first", name: "Unplugged first", summary: "Introduce without a computer" },
  { id: "spaced_retrieval", name: "Spaced retrieval", summary: "Revisit at increasing intervals" },
  { id: "dual_coding", name: "Dual coding", summary: "Verbal explanations + visual diagrams" },
  { id: "interleaving", name: "Interleaving", summary: "Mix problem types" },
];

function _paletteFor(idx: number): string {
  return PALETTE[idx % PALETTE.length] ?? "#bcb8b0";
}

function _buildCanonicalPrinciples(): PrincipleMeta[] {
  return CANONICAL_PRINCIPLES.map((p, idx) => ({
    id: p.id,
    name: p.name,
    summary: p.summary,
    how_to_apply: "See the canonical NCCE 'Pedagogy in Action' guidance document.",
    color: _paletteFor(idx),
  }));
}

interface PedagogyOverlayProps {
  /** Optional graphId to filter by; defaults to first NCCE subject. */
  graphId?: string;
  /** Max annotatedLearningGraphs rows to subscribe to. */
  maxRows?: number;
}

export function PedagogyOverlay({ graphId, maxRows = 1 }: PedagogyOverlayProps) {
  const [rows, setRows] = useState<AnnotatedLearningGraph[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPrinciple, setSelectedPrinciple] = useState<string | null>(null);

  useEffect(() => {
    try {
      const constraints = [
        ...(graphId ? [where("graphId", "==", graphId)] : []),
        orderBy("generated_at", "desc"),
        limit(maxRows),
      ];
      const unsub = subscribeCollection<AnnotatedLearningGraph>(
        "annotatedLearningGraphs",
        (data) => {
          setRows(data);
          setLoading(false);
        },
        constraints,
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
  }, [graphId, maxRows]);

  const principles = useMemo(() => _buildCanonicalPrinciples(), []);

  const cellsForPrinciple = useMemo(() => {
    if (!selectedPrinciple) return 0;
    let count = 0;
    for (const row of rows) {
      const ann = row.cell_annotations ?? row.cellAnnotations ?? {};
      for (const ids of Object.values(ann)) {
        if (ids.includes(selectedPrinciple)) count += 1;
      }
    }
    return count;
  }, [rows, selectedPrinciple]);

  if (loading)
    return (
      <div className="text-sm text-[var(--color-text)]/60">
        Loading annotated learning graphs…
      </div>
    );

  if (error || rows.length === 0) {
    return (
      <div className="space-y-3">
        <div className="text-sm text-[var(--color-text)]/60">
          No <code className="font-mono">annotatedLearningGraphs</code> in
          Firestore yet. Showing the canonical 12 NCCE pedagogy principles below
          — run <code className="font-mono">make ncce-extract</code> +
          <code className="font-mono"> materialise_annotated_learning_graphs.py</code>
          to populate the Firestore mirror.
        </div>
        <PrincipleBadges
          principles={principles}
          onSelect={setSelectedPrinciple}
          selectedPrinciple={selectedPrinciple}
        />
        {error ? (
          <div className="text-xs text-[var(--color-secondary)]">
            Firestore error: <code className="font-mono">{error}</code>
          </div>
        ) : null}
      </div>
    );
  }

  const first = rows[0];
  const totalCells = first.graph?.cells?.length ?? 0;
  const subject = first.graph?.subject ?? first.subject ?? "Unknown";
  const source = first.pedagogy_source ?? "unknown";

  return (
    <div className="space-y-4">
      <div className="text-sm text-[var(--color-text)]/80">
        <strong>Subject:</strong> <code className="font-mono">{subject}</code> ·
        <strong> Cells:</strong> <code className="font-mono">{totalCells}</code> ·
        <strong> Pedagogy source:</strong>{" "}
        <code className="font-mono">{source}</code>
      </div>
      <PrincipleBadges
        principles={principles}
        onSelect={setSelectedPrinciple}
        selectedPrinciple={selectedPrinciple}
      />
      {selectedPrinciple ? (
        <div className="text-xs text-[var(--color-text)]/60">
          <strong>
            {principles.find((p) => p.id === selectedPrinciple)?.name}
          </strong>{" "}
          appears on <strong>{cellsForPrinciple}</strong> of{" "}
          <strong>{totalCells}</strong> cells in this graph.
        </div>
      ) : null}
    </div>
  );
}

interface PrincipleBadgesProps {
  principles: PrincipleMeta[];
  selectedPrinciple: string | null;
  onSelect: (id: string | null) => void;
}

function PrincipleBadges({ principles, selectedPrinciple, onSelect }: PrincipleBadgesProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {principles.map((p) => {
        const isActive = selectedPrinciple === p.id;
        return (
          <button
            key={p.id}
            type="button"
            onClick={() => onSelect(isActive ? null : p.id)}
            className="rounded-full border px-3 py-1 text-xs font-medium transition-colors"
            style={{
              backgroundColor: isActive ? p.color : "transparent",
              color: isActive ? "#fff" : p.color,
              borderColor: p.color,
            }}
            title={p.summary}
            data-testid={`pedagogy-badge-${p.id}`}
          >
            {p.name}
          </button>
        );
      })}
    </div>
  );
}

export default PedagogyOverlay;
