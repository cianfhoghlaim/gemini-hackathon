import { createFileRoute, Link } from "@tanstack/react-router";
import { BritainIslesMap } from "~/components/map/BritainIslesMap";
import { usePalette } from "~/components/themes/SourcePaletteProvider";

export const Route = createFileRoute("/")({
  component: HomePage,
});

function HomePage() {
  const { palettes, current, setPalette } = usePalette();

  // Quick capability banner — visible to judges at first glance.
  const tierRows = [
    { tier: "1 (primary)",  model: "gemini-3.5-flash",       backend: "Vertex AI / AI Studio" },
    { tier: "2 (fallback)", model: "gemma-4-26b-a4b",        backend: "Unsloth Studio :8888" },
  ];

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-8">
      {/* Hero */}
      <header className="text-center">
        <h2 className="text-4xl font-[var(--font-heading)] text-[var(--color-primary)]">
          Per-Source Theming Across the British Isles
        </h2>
        <p className="mt-4 text-base text-[var(--color-text)]/70 max-w-2xl mx-auto">
          {current?.sourceName ?? "Loading palettes..."} — every official source,
          one adaptive theme.
        </p>
      </header>

      {/* Model policy banner — judges see this first */}
      <section
        className="rounded-lg border p-4"
        style={{
          borderColor: "var(--color-primary)",
          background: "var(--color-background)",
        }}
      >
        <h3 className="text-sm uppercase tracking-wide text-[var(--color-secondary)]">
          Active model policy (hackathon profile)
        </h3>
        <table className="mt-2 w-full text-sm">
          <thead>
            <tr className="text-left">
              <th className="py-1">Tier</th>
              <th className="py-1">Model</th>
              <th className="py-1">Backend</th>
            </tr>
          </thead>
          <tbody>
            {tierRows.map((row) => (
              <tr key={row.tier} className="border-t border-[var(--color-secondary)]/10">
                <td className="py-2 font-mono">{row.tier}</td>
                <td className="py-2 font-mono">{row.model}</td>
                <td className="py-2">{row.backend}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-2 text-xs text-[var(--color-secondary)]/60">
          Excluded by policy: Cloudflare Workers AI (@cf/*) and Qwen3-coder-*.
          Dev profile adds minimax-m3 + the wider Unsloth Studio text set.
        </p>
      </section>

      {/* Map + sidebar */}
      <section className="grid grid-cols-2 gap-6">
        <div>
          <h3 className="text-2xl font-[var(--font-heading)] mb-3">
            British Isles — click a region
          </h3>
          <div className="h-96 rounded-lg overflow-hidden border border-[var(--color-primary)]/30">
            <BritainIslesMap />
          </div>
        </div>
        <div>
          <h3 className="text-2xl font-[var(--font-heading)] mb-3">
            Or pick from {palettes.length} palettes
          </h3>
          <div className="flex flex-wrap gap-2 max-h-96 overflow-y-auto">
            {palettes.map((p) => (
              <button
                key={p.sourceKey}
                type="button"
                onClick={() => setPalette(p.sourceKey)}
                className="px-3 py-1.5 text-sm rounded-full border transition"
                style={{
                  background:
                    current?.sourceKey === p.sourceKey
                      ? p.palette.primary
                      : "var(--color-background)",
                  color:
                    current?.sourceKey === p.sourceKey
                      ? p.palette.background
                      : p.palette.primary,
                  borderColor: p.palette.primary,
                }}
                title={`${p.sourceName} — ${p.jurisdiction}`}
              >
                {p.flag ?? ""} {p.sourceName.split(" - ")[0]}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* Feature surface — links to the rest */}
      <section className="grid grid-cols-4 gap-4">
        <FeatureLink to="/subjects"     title="Subjects"     desc="Per-source subject catalogue (from DLT)" />
        <FeatureLink to="/safeguarding" title="Safeguarding" desc="Child protection context per jurisdiction" />
        <FeatureLink to="/equivalency"  title="Equivalencies" desc="Cross-jurisdiction topic mapping" />
        <FeatureLink to="/compare"      title="Comparisons"   desc="Gemini vs Gemma 4 leaderboard (DuckDB-WASM)" />
      </section>

      {/* Quick-start */}
      <section className="rounded border border-[var(--color-secondary)]/20 p-4 text-sm">
        <h3 className="font-[var(--font-heading)] mb-2">Quick-start (offline)</h3>
        <pre className="bg-black/5 rounded p-3 text-xs overflow-x-auto">
{`# From the repo root
mise run smoke          # 11-step offline E2E
mise run backend:test   # Python backend /api/health probe
mise run compare:demo   # Gemini vs Gemma 4 harness -> DuckDB
cd web && bun run dev    # Vite on :3000 (this window)`}
        </pre>
      </section>
    </div>
  );
}

function FeatureLink({ to, title, desc }: { to: string; title: string; desc: string }) {
  return (
    <Link
      to={to}
      className="rounded border p-3 hover:shadow-md transition"
      style={{
        borderColor: "var(--color-secondary)/20",
        background: "var(--color-background)",
      }}
    >
      <h4 className="font-[var(--font-heading)] text-lg">{title}</h4>
      <p className="text-xs text-[var(--color-text)]/60 mt-1">{desc}</p>
    </Link>
  );
}
