/**
 * MarimoEmbed — embeds the per-subject marimo notebook in the web UI.
 *
 * Two render modes:
 *   - "wasm"  (default for dev) — loads the marimo WASM bundle from
 *     marimo.app (no infra). Best for offline demos and judges.
 *   - "app"   — embeds a marimo.run-deployed app via iframe (production).
 *     Requires the user to have run `marimo deploy notebooks/per_subject.py`.
 *
 * The session identity is passed as URL query params so the notebook
 * pre-populates the (subnation, cycle, subject) dropdowns.
 */

export interface MarimoEmbedProps {
  subnation: string;
  cycle: string;
  subject: string;
  /** "wasm" = marimo.app hosted WASM; "app" = marimo.run iframe. */
  mode?: "wasm" | "app";
  /** Override the marimo.run URL (only used when mode === "app"). */
  appUrl?: string;
  /** Override the marimo.app WASM URL (only used when mode === "wasm"). */
  wasUrl?: string;
  width?: number;
  height?: number;
  className?: string;
}

const DEFAULT_WASM_URL =
  "https://marimo.app/github/ciandfhoghlaim/gemini-hackathon/blob/main/notebooks/per_subject.py/wasm";

export function MarimoEmbed({
  subnation,
  cycle,
  subject,
  mode = "wasm",
  appUrl,
  wasUrl,
  width = 800,
  height = 600,
  className,
}: MarimoEmbedProps) {
  const src = (() => {
    if (mode === "app" && appUrl) {
      const u = new URL(appUrl);
      u.searchParams.set("subnation", subnation);
      u.searchParams.set("cycle", cycle);
      u.searchParams.set("subject", subject);
      return u.toString();
    }
    const base = wasUrl ?? DEFAULT_WASM_URL;
    const u = new URL(base);
    u.searchParams.set("embed", "true");
    u.searchParams.set("subnation", subnation);
    u.searchParams.set("cycle", cycle);
    u.searchParams.set("subject", subject);
    return u.toString();
  })();

  return (
    <iframe
      src={src}
      title={`Per-subject notebook for ${subnation} / ${cycle} / ${subject}`}
      sandbox="allow-scripts allow-same-origin allow-downloads allow-popups allow-forms"
      allow="microphone"
      allowFullScreen
      width={width}
      height={height}
      className={className}
      style={{
        width,
        height,
        border: "1px solid var(--color-secondary)/20",
        borderRadius: 8,
        background: "var(--color-background)",
      }}
    />
  );
}
