/**
 * ModelPolicyBadge — the home-page ribbon that surfaces the
 * hackathon's mandatory-tech compliance at first glance.
 *
 * Shows:
 *   - Tier 1: Gemini 3.5 (Vertex AI default; AI Studio toggle)
 *   - Tier 2: Gemma 4 26B-A4B via Unsloth Studio
 *   - The Phase 3 default-subnation list (Ireland + England) +
 *     available (NI/Scotland/Wales) + future expansion pack
 *     (Jersey/Guernsey/IoM) — the "future expansion pack" framing
 *     is a deliberate productisation of the not-yet-built data.
 */

export function ModelPolicyBadge() {
  return (
    <section
      className="rounded-lg border p-4 text-xs"
      style={{
        borderColor: "var(--color-primary)",
        background: "var(--color-background)",
      }}
      aria-label="Active model policy"
    >
      <header className="mb-2">
        <span className="text-sm font-[var(--font-heading)] text-[var(--color-primary)]">
          Active model policy
        </span>
      </header>

      <div className="grid grid-cols-2 gap-x-4 gap-y-1 mb-3">
        <div>
          <span className="text-[var(--color-secondary)]">Tier 1:</span>{" "}
          <strong>gemini-3.5-flash</strong>
          <span className="text-[var(--color-text)]/60"> (Vertex AI)</span>
        </div>
        <div>
          <span className="text-[var(--color-secondary)]">Tier 2:</span>{" "}
          <strong>unsloth/gemma-4-26B-A4B-it-GGUF</strong>
          <span className="text-[var(--color-text)]/60"> (Unsloth Studio)</span>
        </div>
      </div>

      <div className="border-t pt-2" style={{ borderColor: "var(--color-secondary)/20" }}>
        <span className="text-[var(--color-secondary)]">Subnations: </span>
        <span>
          <strong className="text-[var(--color-primary)]">Ireland</strong>,{" "}
          <strong className="text-[var(--color-primary)]">England</strong>{" "}
          <span className="text-[var(--color-text)]/40">|</span>{" "}
          <span>Scotland</span>, <span>Wales</span>,{" "}
          <span>Northern Ireland</span>{" "}
          <span className="text-[var(--color-text)]/40">|</span>{" "}
          <span className="text-[var(--color-text)]/40">
            Jersey, Guernsey, Isle of Man
          </span>{" "}
          <span className="text-[var(--color-text)]/40">
            (future expansion pack)
          </span>
        </span>
      </div>
    </section>
  );
}
