/**
 * The Learning Graphs landing page — the NCCE showcase surface.
 *
 * Hosts the canonical 4-tab Gradio studio via an iframe embedding the
 * HF Space at `cianfhoghlaim-gemini-hackathon-learning-graphs.hf.space`.
 * Plus a 1-page summary linking to the README + the 6 priority subjects
 * (the canonical NCCE showcase list).
 *
 * Phase 5 of the
 * [`2026-08-31-ncce-showcase-complete-v1`](../../../openspec/changes/2026-08-31-ncce-showcase-complete-v1/proposal.md)
 * change replaces the Phase 4 `<em>stub</em>` placeholders for the
 * Equivalencies + Pedagogy overlay tabs with real Firestore-backed
 * React components — see `EquivalenciesPanel.tsx` + `PedagogyOverlay.tsx`.
 */

import { Link } from "react-router-dom";
import { EquivalenciesPanel } from "../../components/learning_graphs/EquivalenciesPanel.tsx";
import { PedagogyOverlay } from "../../components/learning_graphs/PedagogyOverlay.tsx";

const PRIORITY_SUBJECTS: ReadonlyArray<{
  slug: string;
  label: string;
  description: string;
}> = [
  {
    slug: "computer_science",
    label: "Computer Science",
    description: "The NCCE Y8 Python learning graph — the canonical showcase.",
  },
  {
    slug: "mathematics",
    label: "Mathematics",
    description: "NCCE-style row × column grid with the Maths strand taxonomy.",
  },
  {
    slug: "english",
    label: "English",
    description: "NCCE-style grid with the English strand + Bloom taxonomy.",
  },
  {
    slug: "gaeilge",
    label: "Gaeilge",
    description: "NCCE-style grid with the Gaeilge strand + Bloom taxonomy (bilingual surface).",
  },
  {
    slug: "chemistry",
    label: "Chemistry",
    description: "NCCE-style grid with the Chemistry strand + Bloom taxonomy.",
  },
  {
    slug: "geography",
    label: "Geography",
    description: "NCCE-style grid with the Geography strand + Bloom taxonomy.",
  },
];

const HF_SPACE_URL = "https://cianfhoghlaim-gemini-hackathon-learning-graphs.hf.space";

function LearningGraphsPage() {
  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      <header>
        <h1 className="text-4xl font-[var(--font-heading)] text-[var(--color-primary)]">
          The Learning Graph Studio
        </h1>
        <p className="mt-2 text-sm text-[var(--color-text)]/70">
          The 4-tab Gradio studio for the BIEP v3 learning-graph substrate — driven by
          the NCCE Y8 Python learning graph. Embeds the canonical HF Space mirror of
          the <code>an_learning_graph</code> studio.
        </p>
      </header>

      <section className="bronze-border">
        <h2 className="text-2xl font-[var(--font-heading)] text-[var(--color-primary)]">
          The 4 tabs
        </h2>
        <ol className="list-decimal list-inside space-y-2 text-sm text-[var(--color-text)]/80">
          <li>
            <strong>Render</strong> — pick (jurisdiction, subject, year_level), view the canonical
            LearningGraph as a Plotly SVG heatmap with prerequisite edges overlaid.
          </li>
          <li>
            <strong>Equivalencies</strong> — Firestore-backed cross-walk from a
            single NCCE cell to the equivalent cells in the 7 other British Isles
            jurisdictions (live <code>cellEquivalents</code> subscription).
          </li>
          <li>
            <strong>Generate from PDF</strong> — upload a syllabus PDF, run the per-subject BAML
            extractor, preview the generated row × column grid.
          </li>
          <li>
            <strong>Pedagogy overlay</strong> — overlay the 12 NCCE pedagogy principles
            on every cell of the learning graph (live{" "}
            <code>annotatedLearningGraphs</code> subscription).
          </li>
        </ol>
      </section>

      <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-md border border-[var(--color-secondary)]/20 p-4 bg-[var(--color-bg)]">
          <h3 className="text-lg font-semibold text-[var(--color-primary)]">
            Equivalencies (Firestore-backed)
          </h3>
          <p className="mt-1 text-xs text-[var(--color-text)]/60">
            Cell-level cross-walk from a single NCCE source cell to the equivalent
            cells in the 7 other British Isles jurisdictions.
          </p>
          <div className="mt-3">
            <EquivalenciesPanel />
          </div>
        </div>
        <div className="rounded-md border border-[var(--color-secondary)]/20 p-4 bg-[var(--color-bg)]">
          <h3 className="text-lg font-semibold text-[var(--color-primary)]">
            Pedagogy overlay (Firestore-backed)
          </h3>
          <p className="mt-1 text-xs text-[var(--color-text)]/60">
            The 12 NCCE pedagogy principles overlaid on every cell of the
            canonical NCCE Y8 Python learning graph. Click a badge to filter.
          </p>
          <div className="mt-3">
            <PedagogyOverlay graphId="uk_ncce_computer_science_y8" />
          </div>
        </div>
      </section>

      <section>
        <h2 className="text-2xl font-[var(--font-heading)] text-[var(--color-primary)] mb-3">
          Try it now
        </h2>
        <div className="aspect-[16/10] w-full rounded-md overflow-hidden border border-[var(--color-secondary)]/20 bg-black/40">
          <iframe
            title="Learning Graph Studio (HF Space)"
            src={HF_SPACE_URL}
            className="w-full h-full"
            allow="clipboard-write"
            loading="lazy"
          />
        </div>
        <p className="mt-2 text-xs text-[var(--color-text)]/60">
          If the iframe does not load,{" "}
          <a
            href={HF_SPACE_URL}
            target="_blank"
            rel="noreferrer"
            className="underline text-[var(--color-secondary)]"
          >
            open the HF Space in a new tab
          </a>
          .
        </p>
      </section>

      <section>
        <h2 className="text-2xl font-[var(--font-heading)] text-[var(--color-primary)]">
          The 6 priority subjects
        </h2>
        <p className="text-sm text-[var(--color-text)]/70 mt-1">
          The NCCE learning-graph showcase ships per-subject extractors for these 6 subjects.
          Each subject has its own strand taxonomy + Bloom taxonomy (see the BAML contract).
        </p>
        <ul className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-4">
          {PRIORITY_SUBJECTS.map((s) => (
            <li
              key={s.slug}
              className="rounded-md border border-[var(--color-secondary)]/10 p-3 bg-[var(--color-bg)]"
            >
              <h3 className="text-lg font-semibold text-[var(--color-secondary)]">
                {s.label}
              </h3>
              <p className="text-sm text-[var(--color-text)]/80 mt-1">{s.description}</p>
            </li>
          ))}
        </ul>
      </section>

      <section className="bronze-border">
        <h2 className="text-2xl font-[var(--font-heading)] text-[var(--color-primary)]">
          Notebooks (marimo)
        </h2>
        <p className="text-sm text-[var(--color-text)]/70 mt-1">
          Three live marimo notebooks that browse the BIEP v3 substrate
          end-to-end. They render in the browser via the marimo WASM
          sandbox — no local install required.
        </p>
        <ul className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-4">
          <li className="rounded-md border border-[var(--color-secondary)]/20 p-4 bg-[var(--color-bg)]">
            <h3 className="text-lg font-semibold text-[var(--color-primary)]">
              17 — LC syllabus browser
            </h3>
            <p className="text-sm text-[var(--color-text)]/70 mt-1">
              Filter the 139 lifted LC PDFs by subject / language; preview
              the BAML extractions + module_topics from{" "}
              <code>data/bi_ep/extracted_syllabi.sqlite</code>.
            </p>
            <a
              href="https://marimo.app/github.com/cianfhoghlaim/gemini-hackathon/blob/main/notebooks/17_lc_syllabus_extract_browser.py/wasm"
              target="_blank"
              rel="noreferrer"
              className="mt-3 inline-block text-xs text-[var(--color-secondary)] hover:underline"
            >
              Open notebook 17 →
            </a>
          </li>
          <li className="rounded-md border border-[var(--color-secondary)]/20 p-4 bg-[var(--color-bg)]">
            <h3 className="text-lg font-semibold text-[var(--color-primary)]">
              18 — Gaeilge / English bilingual
            </h3>
            <p className="text-sm text-[var(--color-text)]/70 mt-1">
              Side-by-side comparison of the Irish (Gaeilge) and English
              BAML extractions; aligned on <code>topic_id</code> so
              translation drift is visible at a glance.
            </p>
            <a
              href="https://marimo.app/github.com/cianfhoghlaim/gemini-hackathon/blob/main/notebooks/18_gaeilge_bilingual_view.py/wasm"
              target="_blank"
              rel="noreferrer"
              className="mt-3 inline-block text-xs text-[var(--color-secondary)] hover:underline"
            >
              Open notebook 18 →
            </a>
          </li>
          <li className="rounded-md border border-[var(--color-secondary)]/20 p-4 bg-[var(--color-bg)]">
            <h3 className="text-lg font-semibold text-[var(--color-primary)]">
              19 — NCCA policy citation explorer
            </h3>
            <p className="text-sm text-[var(--color-text)]/70 mt-1">
              The 5 NCCA policy PDFs that anchor every certificate. Each
              card links to the source document + the BAML citation
              marker.
            </p>
            <a
              href="https://marimo.app/github.com/cianfhoghlaim/gemini-hackathon/blob/main/notebooks/19_ncca_policy_citation_explorer.py/wasm"
              target="_blank"
              rel="noreferrer"
              className="mt-3 inline-block text-xs text-[var(--color-secondary)] hover:underline"
            >
              Open notebook 19 →
            </a>
          </li>
        </ul>
      </section>

      <section className="bronze-border">
        <h2 className="text-2xl font-[var(--font-heading)] text-[var(--color-primary)]">
          Learn more
        </h2>
        <ul className="list-disc list-inside space-y-1 text-sm text-[var(--color-text)]/80">
          <li>
            <Link to="/docs/LEARNING_GRAPH_SHOWCASE.md" className="underline text-[var(--color-secondary)]">
              Read the canonical showcase guide
            </Link>{" "}
            (<code>docs/LEARNING_GRAPH_SHOWCASE.md</code>)
          </li>
          <li>
            <a
              href="https://github.com/cianfhoghlaim/gemini-hackathon/blob/main/baml_extracts/learning_graph.baml"
              target="_blank"
              rel="noreferrer"
              className="underline text-[var(--color-secondary)]"
            >
              The BAML extraction contract
            </a>{" "}
            (8 classes + 9 functions)
          </li>
          <li>
            <a
              href="https://github.com/cianfhoghlaim/gemini-hackathon/blob/main/dlt_pipelines/uk_ncce_learning_graphs.py"
              target="_blank"
              rel="noreferrer"
              className="underline text-[var(--color-secondary)]"
            >
              The DLT substrate
            </a>{" "}
            (11 OFFICIAL_DOC_COLUMNS rows)
          </li>
          <li>
            <Link to="/archipelago" className="underline text-[var(--color-secondary)]">
              See all 8 British Isles jurisdictions
            </Link>
          </li>
        </ul>
      </section>
    </div>
  );
}

export default LearningGraphsPage;
