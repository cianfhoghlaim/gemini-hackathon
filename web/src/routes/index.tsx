import { createFileRoute, Link } from "@tanstack/react-router";
import { BritainIslesMap } from "~/components/map/BritainIslesMap";
import { usePalette } from "~/components/themes/SourcePaletteProvider";

export const Route = createFileRoute("/")({
  component: HomePage,
});

function HomePage() {
  const { palettes, current, setPalette } = usePalette();
  return (
    <div className="max-w-5xl mx-auto">
      <header className="text-center py-12">
        <h2 className="text-4xl font-[var(--font-heading)] text-[var(--color-primary)]">
          Per-Source Theming Across the British Isles
        </h2>
        <p className="mt-4 text-lg text-[var(--color-text)]/70 max-w-2xl mx-auto">
          {current?.sourceName ?? "Loading palettes..."} — every official source,
          one adaptive theme.
        </p>
      </header>

      <section className="my-8">
        <h3 className="text-2xl font-[var(--font-heading)] mb-4">
          3-Tier Model Policy
        </h3>
        <div className="grid grid-cols-3 gap-4">
          <div className="p-4 rounded-lg border border-[var(--color-primary)] bg-[var(--color-background)]">
            <div className="text-xs uppercase text-[var(--color-secondary)]">Tier 1 (primary)</div>
            <div className="text-lg font-mono mt-1">minimax-m3</div>
            <div className="text-xs mt-1 opacity-70">minimax.io</div>
          </div>
          <div className="p-4 rounded-lg border border-[var(--color-primary)] bg-[var(--color-background)]">
            <div className="text-xs uppercase text-[var(--color-secondary)]">Tier 2 (fallback)</div>
            <div className="text-lg font-mono mt-1">unsloth/gemma-4-26B</div>
            <div className="text-xs mt-1 opacity-70">unsloth-studio</div>
          </div>
          <div className="p-4 rounded-lg border border-[var(--color-primary)] bg-[var(--color-background)]">
            <div className="text-xs uppercase text-[var(--color-secondary)]">Tier 3 (final)</div>
            <div className="text-lg font-mono mt-1">gemini-3.5-flash</div>
            <div className="text-xs mt-1 opacity-70">vertex_ai</div>
          </div>
        </div>
        <p className="mt-3 text-xs text-[var(--color-secondary)]/60">
          Cloudflare Workers AI and Qwen3-coder are explicitly excluded.
        </p>
      </section>

      <section className="my-12">
        <h3 className="text-2xl font-[var(--font-heading)] mb-4">
          Choose a source
        </h3>
        <div className="flex flex-wrap gap-2 mb-6">
          {palettes.map((p) => (
            <button
              key={p.sourceKey}
              type="button"
              onClick={() => setPalette(p.sourceKey)}
              className="px-3 py-1.5 text-sm rounded-full border"
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
            >
              {p.flag ?? ""} {p.sourceName.split(" - ")[0]}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm">
              Click any region on the map, or pick a button above. The interface
              re-themes in real time, drawing colours from the official source.
            </p>
            <ul className="mt-6 space-y-2 text-sm">
              <li>
                <Link to="/subjects" className="text-[var(--color-primary)] underline">
                  Browse subjects →
                </Link>
              </li>
              <li>
                <Link to="/safeguarding" className="text-[var(--color-primary)] underline">
                  Safeguarding context →
                </Link>
              </li>
              <li>
                <Link to="/equivalency" className="text-[var(--color-primary)] underline">
                  Cross-jurisdiction equivalencies →
                </Link>
              </li>
            </ul>
          </div>
          <div className="h-80 rounded-lg overflow-hidden border border-[var(--color-primary)]/30">
            <BritainIslesMap />
          </div>
        </div>
      </section>
    </div>
  );
}
