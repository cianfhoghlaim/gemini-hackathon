/**
 * web/src/a2ui/catalog.tsx — the React side of the A2UI contract.
 *
 * Mirrors `gemini_hackathon_backend/catalog/ncca_v1.json` (the Python-side
 * catalog the ADK agent emits via AG-UI `Raw` events). The
 * `gemini_hackathon_backend/catalog/ncca_v1.json` defines 6 component
 * schemas; this file maps each to a React renderer.
 *
 * Per the A2UI v0.8 spec: a Catalog is a list of component schemas
 * + renderers. The server-side `gemini_hackathon_backend/agents/ncca_panel.py`
 * emits `updateComponents` + `updateDataModel` JSONL messages tagged with
 * our `catalogId` ("https://gemini-hackathon.cianfhoghlaim.ie/a2ui/catalogs/ncca-v1.json"),
 * and the a2ui-renderer matches `component` strings against the names
 * registered here.
 *
 * Per CopilotKit v2: `createCatalog(schemas, renderers, options)` takes a
 * `schemas` object keyed by the `component` string and a `renderers`
 * object with the same keys. We add the basic catalog to the schemas so
 * every AG-UI v0.8 message has a renderer for every primitive type the
 * NCCA panel emits (Text, Column, Row, List, Card, Button).
 */

import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { createCatalog } from "@copilotkit/a2ui-renderer";
import { z } from "zod";
import type { CatalogComponentDefinition } from "@copilotkit/a2ui-renderer";

/* ---------------------------------------------------------------- */
/* Per-component React renderers. Each receives `props` (the typed     */
/* JSON-Pointer-resolved shape from the data model) and renders the     */
/* studio's native UI for it.                                          */
/* ---------------------------------------------------------------- */

function NccaPdfCard({ pdf_id, title, blurb }: { pdf_id: string; title: string; blurb: string }): ReactNode {
  // Each PDF card links to the canonical /pdfs/<pdf_id> route in the
  // Firestore asset bucket (the same URLs the BAML extraction writes
  // to per the existing gemini_hackathon_backend/catalog layer).
  // React Router 7's <Link> doesn't take a `params` prop — it takes a
  // fully-qualified `to` URL. For our static catalog (we know the path
  // shape), build the URL directly.
  const pdfUrl = `/pdfs/${pdf_id}`;
  return (
    <article className="rounded-lg border border-[var(--color-secondary)]/30 bg-[var(--color-background)] p-4">
      <header className="flex items-center justify-between">
        <h3 className="font-[var(--font-heading)] text-base text-[var(--color-primary)]">
          {title}
        </h3>
        <span className="text-[10px] uppercase tracking-wider text-[var(--color-text)]/50 font-mono">
          {pdf_id.slice(0, 24)}…
        </span>
      </header>
      <p className="mt-2 text-sm text-[var(--color-text)]/80">{blurb}</p>
      <Link to={pdfUrl} className="mt-3 inline-block text-xs text-[var(--color-accent)] hover:underline">
        View PDF →
      </Link>
    </article>
  );
}

function KeyCompetencyRow({ number, name, description }: { number: number; name: string; description: string }): ReactNode {
  return (
    <div className="flex gap-4 py-3 border-b border-[var(--color-secondary)]/20 last:border-0">
      <div className="flex-none w-8 h-8 rounded-full bg-[var(--color-primary)] text-[var(--color-primary-foreground)] grid place-items-center font-bold">
        {number}
      </div>
      <div>
        <div className="font-[var(--font-heading)] text-[var(--color-primary)]">{name}</div>
        <p className="text-sm text-[var(--color-text)]/80">{description}</p>
      </div>
    </div>
  );
}

function ScProgrammeStatementBlock({ principle, elaboration, strand }: { principle: string; elaboration: string; strand: string }): ReactNode {
  return (
    <div className="rounded-lg bg-[var(--color-muted)]/60 p-4 my-2">
      <div className="text-xs uppercase tracking-wider text-[var(--color-text)]/50 mb-1 font-mono">
        {strand}
      </div>
      <div className="font-[var(--font-heading)] text-[var(--color-primary)]">{principle}</div>
      <p className="mt-2 text-sm text-[var(--color-text)]/80">{elaboration}</p>
    </div>
  );
}

function ScrAdvisoryHighlight({ chapter, recommendation, page }: { chapter: string; recommendation: string; page: number }): ReactNode {
  return (
    <blockquote className="border-l-4 border-[var(--color-primary)]/60 pl-4 my-2">
      <p className="italic text-[var(--color-text)]/90">"{recommendation}"</p>
      <footer className="mt-1 text-xs text-[var(--color-text)]/50 not-italic">
        — {chapter}, p.{page} · SCR Advisory Report
      </footer>
    </blockquote>
  );
}

function OnlineLearningCallout({ finding, implication, page }: { finding: string; implication: string; page: number }): ReactNode {
  return (
    <div className="rounded-md bg-amber-50 border border-amber-200 p-3 my-2 text-amber-900">
      <div className="font-semibold">{finding}</div>
      <p className="mt-1 text-sm">{implication}</p>
      <div className="mt-2 text-xs opacity-70">p.{page} · Online Learning Environments</div>
    </div>
  );
}

function CitationPill({ pdf_id, page, snippet }: { pdf_id: string; page: number; snippet: string }): ReactNode {
  // Renders inline (e.g. inside a useFrontendTool result or a useRenderTool
  // body). Click → opens the PDF anchored at the cited page.
  return (
    <a
      href={`/pdfs/${pdf_id}#page=${page}`}
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono bg-[var(--color-primary)]/10 text-[var(--color-primary)] hover:bg-[var(--color-primary)]/20"
      title={snippet}
    >
      📄 {pdf_id.slice(0, 16)}… · p.{page}
    </a>
  );
}

/**
 * NCCEHeatmap — the 7th A2UI component in the NCCA catalog.
 *
 * Renders a `(rows × columns)` heatmap of `values[i][j]` floats as a small
 * SVG grid. The colour ramp runs from a cool blue (low) through cream to
 * a warm red (high). We keep this in pure SVG (no recharts dep) so the
 * surface stays dependency-free; the heavier viz layers live in the
 * marimo notebooks (notebooks/10*, 17*, 18*, 19*).
 *
 * Props:
 *   - rows:     row labels (length = M)
 *   - columns:  column labels (length = N)
 *   - values:   2-D float matrix (M × N)
 *   - title?:   optional heading rendered above the grid
 */
function NCCEHeatmap({
  rows,
  columns,
  values,
  title,
}: {
  rows: string[];
  columns: string[];
  values: number[][];
  title?: string;
}): ReactNode {
  const cell = 26;
  const padLeft = 110;
  const padTop = 38;
  const W = padLeft + columns.length * cell + 12;
  const H = padTop + rows.length * cell + 12;

  // Flatten to compute the colour ramp range.
  const flat = values.flat();
  const min = flat.length ? Math.min(...flat) : 0;
  const max = flat.length ? Math.max(...flat) : 1;
  const span = max - min || 1;

  // Cool→warm: hsl interp 220° (blue) → 50° (red) via cream (60°) at 0.5.
  function colorFor(v: number): string {
    const t = (v - min) / span;
    const hue = 220 - 170 * t;
    const sat = 60;
    const light = 92 - 32 * t;
    return `hsl(${hue.toFixed(0)} ${sat}% ${light}%)`;
  }

  return (
    <figure className="rounded-lg border border-[var(--color-secondary)]/30 bg-[var(--color-background)] p-3 my-2">
      {title && (
        <figcaption className="font-[var(--font-heading)] text-sm text-[var(--color-primary)] mb-2">
          {title}
        </figcaption>
      )}
      <div className="overflow-x-auto">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          width={W}
          height={H}
          role="img"
          aria-label={`Heatmap ${rows.length} × ${columns.length}`}
          style={{ display: "block", maxWidth: "100%" }}
        >
          {/* column headers */}
          <g>
            {columns.map((c, j) => (
              <text
                key={`col-${j}`}
                x={padLeft + j * cell + cell / 2}
                y={padTop - 8}
                fontSize={9}
                textAnchor="middle"
                fill="var(--color-text)"
                opacity={0.7}
              >
                {c}
              </text>
            ))}
          </g>
          {/* row labels + cells */}
          <g>
            {rows.map((r, i) => (
              <g key={`row-${i}`}>
                <text
                  x={padLeft - 6}
                  y={padTop + i * cell + cell / 2 + 3}
                  fontSize={9}
                  textAnchor="end"
                  fill="var(--color-text)"
                  opacity={0.7}
                >
                  {r}
                </text>
                {columns.map((_c, j) => {
                  const v = values?.[i]?.[j] ?? 0;
                  return (
                    <rect
                      key={`cell-${i}-${j}`}
                      x={padLeft + j * cell}
                      y={padTop + i * cell}
                      width={cell - 2}
                      height={cell - 2}
                      rx={3}
                      fill={colorFor(v)}
                      stroke="var(--color-background)"
                      strokeWidth={1}
                    >
                      <title>{`${r} × ${_c}: ${v.toFixed(2)}`}</title>
                    </rect>
                  );
                })}
              </g>
            ))}
          </g>
        </svg>
      </div>
      <div className="mt-2 text-[10px] text-[var(--color-text)]/50 font-mono">
        min {min.toFixed(2)} · max {max.toFixed(2)} · range {span.toFixed(2)}
      </div>
    </figure>
  );
}

/* ---------------------------------------------------------------- */
/* The catalog — single source of truth for the React side.            */
/*                                                                     */
/* `createCatalog(definitions, renderers, options)` — definitions are  */
/* platform-agnostic Zod schemas + descriptions; renderers are React   */
/* components matching each definition key. `options.includeBasicCatalog:*/
/* true` merges the v0.8 basic catalog primitives (Text, Button, Row,*/
/* Column, List, Card, etc.) into the catalog — so we don't have to    */
/* redefine them. `options.catalogId` is embedded in every A2UI        */
/* `createSurface` message the server sends; the a2ui-renderer matches */
/* incoming catalogId strings against it to confirm client support.    */
/* ---------------------------------------------------------------- */

const catalog = createCatalog(
  {
    NccaPdfCard: {
      description: "An NCCA policy citation card — links to a PDF + short blurb.",
      // The a2ui-renderer v1 type-check expects `ZodObject<T extends ZodRawShape>`
      // but zod 4.x returns the strict variant (`.shape` differs from
      // `any`). The runtime check is correct; we cast to satisfy the
      // structural type. The catalog is correct at runtime.
      props: z.object({
        pdf_id: z.string(),
        title: z.string(),
        blurb: z.string(),
      }) as unknown as CatalogComponentDefinition["props"],
    },
    KeyCompetencyRow: {
      description: "One row in the Senior Cycle 5 Key Competencies list.",
      props: z.object({
        number: z.number().min(1).max(5),
        name: z.string(),
        description: z.string(),
      }) as unknown as CatalogComponentDefinition["props"],
    },
    ScProgrammeStatementBlock: {
      description: "SC L1/L2 Programme Statement summary block — one strand, one principle.",
      props: z.object({
        principle: z.string(),
        elaboration: z.string(),
        strand: z.enum(["Subjects", "Priority Learning", "Wellbeing"]),
      }) as unknown as CatalogComponentDefinition["props"],
    },
    ScrAdvisoryHighlight: {
      description: "A highlight pulled from the SCR Advisory Report — chapter + recommendation + page.",
      props: z.object({
        chapter: z.string(),
        recommendation: z.string(),
        page: z.number(),
      }) as unknown as CatalogComponentDefinition["props"],
    },
    OnlineLearningCallout: {
      description: "A callout panel from the Online Learning Environments PDF.",
      props: z.object({
        finding: z.string(),
        implication: z.string(),
        page: z.number(),
      }) as unknown as CatalogComponentDefinition["props"],
    },
    CitationPill: {
      description: "A clickable citation pill (deep-link to a PDF at a specific page anchor).",
      props: z.object({
        pdf_id: z.string(),
        page: z.number(),
        snippet: z.string().max(200),
      }) as unknown as CatalogComponentDefinition["props"],
    },
    NCCEHeatmap: {
      description: "An MxN heatmap grid (rows × columns) of float values rendered as a cool→warm SVG grid.",
      props: z.object({
        rows: z.array(z.string()),
        columns: z.array(z.string()),
        values: z.array(z.array(z.number())),
        title: z.string().optional(),
      }) as unknown as CatalogComponentDefinition["props"],
    },
  },
  {
    // The a2ui-renderer v1 type-check uses `Record<string, any>` for the
    // renderers' prop type — our concrete types (NccaPdfCardProps, …)
    // satisfy the runtime contract but don't conform structurally to
    // `Record<string, unknown>`. Cast the whole map to `any`; runtime
    // dispatches by component-name, not by prop type.
    NccaPdfCard: NccaPdfCard as any,
    KeyCompetencyRow: KeyCompetencyRow as any,
    ScProgrammeStatementBlock: ScProgrammeStatementBlock as any,
    ScrAdvisoryHighlight: ScrAdvisoryHighlight as any,
    OnlineLearningCallout: OnlineLearningCallout as any,
    CitationPill: CitationPill as any,
    NCCEHeatmap: NCCEHeatmap as any,
  },
  {
    catalogId: "https://gemini-hackathon.cianfhoghlaim.ie/a2ui/catalogs/ncca-v1.json",
    includeBasicCatalog: true,
  },
);

export default catalog;
export {
  NccaPdfCard,
  KeyCompetencyRow,
  ScProgrammeStatementBlock,
  ScrAdvisoryHighlight,
  OnlineLearningCallout,
  CitationPill,
  NCCEHeatmap,
};
