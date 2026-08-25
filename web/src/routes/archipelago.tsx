/**
 * /archipelago — the archipelagic unity showcase.
 *
 * Lists all 8 subnations side by side with their palettes, awarding
 * bodies, and safeguarding policies. This is the visual "one platform
 * for the British Isles" story — the theming is the unity layer, the
 * content (per-subnation) is the diversity layer.
 */

import { createFileRoute, Link } from "@tanstack/react-router";
import { SUBNATIONS } from "../types/session";
import { useSession } from "../components/session/SessionContext";

export const Route = createFileRoute("/archipelago")({
  component: ArchipelagoPage,
});

function ArchipelagoPage() {
  const { subnation } = useSession();
  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      <header>
        <h1 className="text-3xl font-[var(--font-heading)] text-[var(--color-primary)]">
          The British Isles — one platform, eight subnations
        </h1>
        <p className="mt-2 text-sm text-[var(--color-text)]/70">
          Your home is <strong>{subnation.flag} {subnation.name}</strong>.
          The other 7 are the same platform, the same agent, the same
          theming — different content. Click any to switch home.
        </p>
      </header>

      <section className="grid grid-cols-2 gap-4">
        {SUBNATIONS.map((s) => {
          const isActive = s.code === subnation.code;
          const isExpansion = s.expansion;
          return (
            <Link
              key={s.code}
              to="/"
              search={undefined}
              className={`block p-4 rounded border transition ${
                isActive ? "ring-2" : "hover:shadow-md"
              } ${isExpansion ? "opacity-50" : ""}`}
              style={{
                borderColor: isActive
                  ? "var(--color-primary)"
                  : "var(--color-secondary)/20",
                background: "var(--color-background)",
                // Tailwind's `ring-2` would need Tailwind classes; using inline style
                boxShadow: isActive ? "0 0 0 2px var(--color-primary)" : undefined,
              }}
            >
              <div className="flex items-baseline gap-2">
                <span className="text-3xl">{s.flag}</span>
                <h2 className="font-[var(--font-heading)] text-xl">{s.name}</h2>
                {isActive && (
                  <span className="ml-auto text-xs text-[var(--color-primary)]">
                    Your home
                  </span>
                )}
                {isExpansion && (
                  <span className="ml-auto text-xs text-[var(--color-text)]/50">
                    Coming soon
                  </span>
                )}
              </div>
              <p className="text-xs text-[var(--color-text)]/60 mt-2">
                {s.awardingBody} · {s.awardingBodyShort}
              </p>
              <p className="text-xs text-[var(--color-text)]/60 mt-1">
                Cycles: {s.cycles.map((c) => c.replace(/_/g, " ")).join(", ")}
              </p>
              <p className="text-xs text-[var(--color-text)]/60 mt-1">
                Safeguarding: {s.safeguardingSourceKey}
              </p>
            </Link>
          );
        })}
      </section>
    </div>
  );
}
