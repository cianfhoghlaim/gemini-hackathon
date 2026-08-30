/**
 * web/src/components/drill_down/DrillDownPanel.tsx — Phase 7b hierarchical drill-down.
 *
 * Three drill levels:
 *   1. Subnation (Ireland / England / Scotland / Wales / Northern Ireland)
 *   2. Stage (Leaving Certificate / Junior Cycle / GCSE / A-Level / ...)
 *   3. Subject (Mathematics / English / Gaeilge / Chemistry / ...)
 *
 * Each level renders a card list + a "drill in" button. The terminal level
 * (subject) also surfaces:
 *   - Topic equivalence arrows (Phase 4 graph)
 *   - A markdown preview link (Phase 2b .md file path)
 *
 * The component is purely client-side — it reads from `firestoreQueries`
 * (already wired in `web/src/lib/firestore.ts`) for the syllabus_extractions
 * collection. The graph data + markdown paths are passed in as props from
 * the parent route.
 */

import { useEffect, useState } from "react";
import { firestoreQueries } from "../../lib/firestore";

export interface DrillDownTopicEdge {
  source_subnation: string;
  target_subnation: string;
  target_topic_name: string;
  confidence: number;
}

export interface DrillDownPanelProps {
  initialSubnation?: string;
  initialSubject?: string;
  edges?: DrillDownTopicEdge[];
  markdownPath?: string;
  onSelectMarkdown?: (path: string) => void;
}

interface DrillRow {
  subnation: string;
  stage: string;
  subject_slug: string;
  language: string;
  source_pdf: string;
}

const SUBNATIONS = [
  "ireland",
  "england",
  "scotland",
  "wales",
  "northern_ireland",
] as const;

const STAGES = [
  "leaving_cycle",
  "junior_cycle",
  "gcse",
  "a_level",
  "national_5",
] as const;

const SUBJECTS = [
  "mathematics",
  "english",
  "gaeilge",
  "chemistry",
  "biology",
  "physics",
  "geography",
  "computer_science",
] as const;

type Level = "subnation" | "stage" | "subject";

export function DrillDownPanel({
  initialSubnation,
  initialSubject,
  edges = [],
  markdownPath,
  onSelectMarkdown,
}: DrillDownPanelProps) {
  const [subnation, setSubnation] = useState<string | undefined>(initialSubnation);
  const [stage, setStage] = useState<string | undefined>(undefined);
  const [subject, setSubject] = useState<string | undefined>(initialSubject);
  const [rows, setRows] = useState<DrillRow[]>([]);

  // Level 3 — subscribe to the syllabus_extractions Firestore collection
  // when both subnation + subject are picked. The level-1 + level-2 lists
  // are static (the canonical 5 subnations + 5 stages).
  useEffect(() => {
    if (!subnation || !subject) {
      setRows([]);
      return;
    }
    const unsub = firestoreQueries.subscribePerTopicAssets(
      subject,
      subnation,
      (raw: unknown[]) => {
        const typed: DrillRow[] = (raw as Record<string, unknown>[]).map(
          (r) => ({
            subnation: String(r.subnation ?? subnation),
            stage: String(r.stage ?? "leaving_cycle"),
            subject_slug: String(r.subject_slug ?? subject),
            language: String(r.language ?? "en"),
            source_pdf: String(r.source_pdf ?? ""),
          }),
        );
        setRows(typed);
      },
    );
    return unsub;
  }, [subnation, subject]);

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <header>
        <h1 className="text-3xl font-[var(--font-heading)] text-[var(--color-primary)]">
          Hierarchical drill-down
        </h1>
        <p className="text-sm text-[var(--color-text)]/70">
          Phase 7b — subnation → stage → subject (Phase 3 extracted_syllabi
          + Phase 4 equivalency graph)
        </p>
      </header>

      {/* Level 1 — subnation picker */}
      <LevelPicker
        level="subnation"
        title="1. Pick a subnation"
        options={[...SUBNATIONS]}
        selected={subnation}
        onPick={(v) => {
          setSubnation(v);
          setStage(undefined);
          setSubject(undefined);
        }}
      />

      {/* Level 2 — stage picker (appears after level 1) */}
      {subnation && (
        <LevelPicker
          level="stage"
          title="2. Pick a stage"
          options={[...STAGES]}
          selected={stage}
          onPick={(v) => {
            setStage(v);
            setSubject(undefined);
          }}
        />
      )}

      {/* Level 3 — subject picker (appears after level 2) */}
      {subnation && stage && (
        <LevelPicker
          level="subject"
          title="3. Pick a subject"
          options={[...SUBJECTS]}
          selected={subject}
          onPick={setSubject}
        />
      )}

      {/* Terminal — topic edges + markdown preview link */}
      {subnation && subject && (
        <section className="rounded border p-4 space-y-3">
          <h2 className="text-xl font-[var(--font-heading)]">
            Topic equivalencies — {subject}
          </h2>
          {edges.length === 0 ? (
            <p className="text-sm text-[var(--color-text)]/60">
              No edges in the Phase 4 graph for this subject yet. Run{" "}
              <code className="font-mono">
                python -m cocoindex_flows.equivalency.equivalency_graph_app
              </code>{" "}
              to populate.
            </p>
          ) : (
            <ul className="space-y-1">
              {edges.map((e, i) => (
                <li key={i} className="text-sm">
                  <span className="font-mono">{e.source_subnation}</span>{" "}
                  <span aria-hidden>→</span>{" "}
                  <span className="font-mono">{e.target_subnation}</span>{" "}
                  &ldquo;{e.target_topic_name}&rdquo;{" "}
                  <span className="text-xs text-[var(--color-text)]/60">
                    ({e.confidence.toFixed(2)})
                  </span>
                </li>
              ))}
            </ul>
          )}

          {markdownPath && (
            <p className="text-sm">
              <span className="text-[var(--color-text)]/60">Markdown: </span>
              <button
                type="button"
                onClick={() => onSelectMarkdown?.(markdownPath)}
                className="font-mono underline text-[var(--color-primary)]"
              >
                {markdownPath}
              </button>
            </p>
          )}

          {rows.length > 0 && (
            <details>
              <summary className="text-sm cursor-pointer">
                {rows.length} extracted row(s) for this subnation + subject
              </summary>
              <ul className="mt-2 space-y-1">
                {rows.map((r, i) => (
                  <li key={i} className="text-xs font-mono">
                    {r.subnation}/{r.stage}/{r.subject_slug}/{r.language}/
                    {r.source_pdf}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </section>
      )}
    </div>
  );
}

interface LevelPickerProps<L extends Level> {
  level: L;
  title: string;
  options: readonly string[];
  selected?: string;
  onPick: (value: string) => void;
}

function LevelPicker<L extends Level>({
  title,
  options,
  selected,
  onPick,
}: LevelPickerProps<L>) {
  return (
    <section className="rounded border p-4 space-y-2">
      <h2 className="text-lg font-[var(--font-heading)]">{title}</h2>
      <div className="flex flex-wrap gap-2">
        {options.map((opt) => (
          <button
            key={opt}
            type="button"
            onClick={() => onPick(opt)}
            className={`px-3 py-1 rounded text-sm border ${
              selected === opt
                ? "bg-[var(--color-primary)] text-[var(--color-background)]"
                : "bg-[var(--color-background)] text-[var(--color-text)] hover:bg-[var(--color-primary)]/10"
            }`}
          >
            {opt}
          </button>
        ))}
      </div>
    </section>
  );
}

export default DrillDownPanel;