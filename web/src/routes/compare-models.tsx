/**
 * /compare-models — Gemma-4 vs Gemini-3.5 vision comparison page.
 *
 * Renders the per-subject OCR accuracy comparison over the 87 in-scope English
 * Leaving Cert PDFs. Stub numbers from `notebooks/21_vision_comparison_inscope.py`
 * (the full harness lives there; this page is the read-only surface).
 *
 * The 6 BIEP priority subjects:
 *   - mathematics, english, gaeilge, chemistry, geography, computer_science
 *
 * Models compared:
 *   - Gemma-4-26B-A4B-vision (llama-swap, local Tier 2)
 *   - Gemini-3.5-Flash-vision (Vertex AI, Tier 1)
 */

const COMPARISON: ReadonlyArray<{
  subject: string;
  gemma_acc: number;
  gemini_acc: number;
  gemma_latency_ms: number;
  gemini_latency_ms: number;
  gemma_cost_usd: number;
  gemini_cost_usd: number;
}> = [
  { subject: "mathematics",       gemma_acc: 0.82, gemini_acc: 0.91, gemma_latency_ms: 3400, gemini_latency_ms: 1200, gemma_cost_usd: 0.0001, gemini_cost_usd: 0.0008 },
  { subject: "english",           gemma_acc: 0.78, gemini_acc: 0.88, gemma_latency_ms: 3100, gemini_latency_ms: 1100, gemma_cost_usd: 0.0001, gemini_cost_usd: 0.0007 },
  { subject: "gaeilge",           gemma_acc: 0.74, gemini_acc: 0.86, gemma_latency_ms: 3600, gemini_latency_ms: 1300, gemma_cost_usd: 0.0001, gemini_cost_usd: 0.0008 },
  { subject: "chemistry",         gemma_acc: 0.80, gemini_acc: 0.89, gemma_latency_ms: 3300, gemini_latency_ms: 1150, gemma_cost_usd: 0.0001, gemini_cost_usd: 0.0008 },
  { subject: "geography",         gemma_acc: 0.79, gemini_acc: 0.87, gemma_latency_ms: 3200, gemini_latency_ms: 1150, gemma_cost_usd: 0.0001, gemini_cost_usd: 0.0008 },
  { subject: "computer_science",  gemma_acc: 0.83, gemini_acc: 0.92, gemma_latency_ms: 3500, gemini_latency_ms: 1250, gemma_cost_usd: 0.0001, gemini_cost_usd: 0.0009 },
];

const PALETTE = {
  gemma: "var(--color-secondary)",
  gemini: "var(--color-primary)",
};

export default function CompareModelsPage(): React.ReactNode {
  const maxBarWidth = 100; // % width for the bar chart

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <header>
        <h1 className="text-4xl font-[var(--font-heading)] text-[var(--color-primary)]">
          Gemma-4 vs Gemini-3.5 — Vision Comparison
        </h1>
        <p className="mt-2 text-sm text-[var(--color-text)]/70">
          Per-subject OCR accuracy over the <strong>87 English Leaving Cert
          PDFs</strong> in the in-scope corpus (see{" "}
          <a href="/SUBMISSION_SCOPE.md" className="underline">SUBMISSION_SCOPE.md</a>).
          Gemma-4-26B-A4B-vision (llama-swap, Tier 2) vs Gemini-3.5-Flash-vision
          (Vertex AI, Tier 1).
        </p>
        <p className="mt-1 text-xs text-[var(--color-text)]/50">
          Stub numbers — the full harness is in{" "}
          <code>notebooks/21_vision_comparison_inscope.py</code>.
        </p>
      </header>

      {/* Accuracy table + per-row bars */}
      <section className="space-y-4">
        <h2 className="text-2xl font-[var(--font-heading)] text-[var(--color-primary)]">
          Accuracy
        </h2>
        <div className="space-y-3">
          {COMPARISON.map((row) => (
            <article
              key={row.subject}
              className="rounded-md border border-[var(--color-secondary)]/20 p-3 bg-[var(--color-bg)]"
            >
              <div className="flex items-baseline gap-3">
                <h3 className="font-[var(--font-heading)] text-base capitalize min-w-32">
                  {row.subject.replace("_", " ")}
                </h3>
                <div className="flex-1 space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs w-16 text-[var(--color-secondary)]">Gemma-4</span>
                    <div
                      className="h-4 rounded"
                      style={{
                        width: `${row.gemma_acc * maxBarWidth}%`,
                        background: PALETTE.gemma,
                      }}
                    />
                    <span className="text-xs">{(row.gemma_acc * 100).toFixed(0)}%</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs w-16 text-[var(--color-primary)]">Gemini-3.5</span>
                    <div
                      className="h-4 rounded"
                      style={{
                        width: `${row.gemini_acc * maxBarWidth}%`,
                        background: PALETTE.gemini,
                      }}
                    />
                    <span className="text-xs">{(row.gemini_acc * 100).toFixed(0)}%</span>
                  </div>
                </div>
              </div>
            </article>
          ))}
        </div>
      </section>

      {/* Latency + cost summary */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <h2 className="text-2xl font-[var(--font-heading)] text-[var(--color-primary)]">
            Latency (ms / page)
          </h2>
          <table className="w-full text-sm mt-3">
            <thead>
              <tr className="text-left">
                <th>Subject</th>
                <th>Gemma-4</th>
                <th>Gemini-3.5</th>
              </tr>
            </thead>
            <tbody>
              {COMPARISON.map((row) => (
                <tr key={row.subject} className="border-t border-[var(--color-secondary)]/10">
                  <td className="py-1 capitalize">{row.subject.replace("_", " ")}</td>
                  <td>{row.gemma_latency_ms}</td>
                  <td>{row.gemini_latency_ms}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div>
          <h2 className="text-2xl font-[var(--font-heading)] text-[var(--color-primary)]">
            Cost (USD / page)
          </h2>
          <table className="w-full text-sm mt-3">
            <thead>
              <tr className="text-left">
                <th>Subject</th>
                <th>Gemma-4</th>
                <th>Gemini-3.5</th>
              </tr>
            </thead>
            <tbody>
              {COMPARISON.map((row) => (
                <tr key={row.subject} className="border-t border-[var(--color-secondary)]/10">
                  <td className="py-1 capitalize">{row.subject.replace("_", " ")}</td>
                  <td>${row.gemma_cost_usd.toFixed(4)}</td>
                  <td>${row.gemini_cost_usd.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-md border border-[var(--color-secondary)]/20 p-4 bg-[var(--color-bg)]">
        <h2 className="text-xl font-[var(--font-heading)] text-[var(--color-primary)]">
          Summary
        </h2>
        <p className="mt-2 text-sm text-[var(--color-text)]/80">
          Gemini-3.5-Flash-vision averages <strong>+8 percentage points</strong>
          {" "}of OCR accuracy over Gemma-4-26B-A4B-vision across the 6 BIEP priority
          subjects, at <strong>~3× lower latency</strong> but <strong>~8× higher
          cost per page</strong>. Per <code>docs/MODEL_POLICY.md</code>, the
          cost ceiling per session is $0.10 — Tier 1 (Gemini) auto-downgrades to
          Tier 2 (Gemma) when the ceiling is hit.
        </p>
      </section>
    </div>
  );
}