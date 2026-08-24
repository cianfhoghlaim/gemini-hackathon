import { useEffect, useRef, useState } from "react";
import { CopilotChat } from "@copilotkit/react-ui";
import { CopilotKit } from "@copilotkit/react-core";
import { usePalette } from "~/components/themes/SourcePaletteProvider";

type ModelTier = "tier-1" | "tier-2" | "tier-3";
const TIER_LABEL: Record<ModelTier, string> = {
  "tier-1": "minimax-m3",
  "tier-2": "unsloth/gemma-4-26B",
  "tier-3": "gemini-3.5-flash",
};

export function AGUIChat() {
  const { current } = usePalette();
  const [tier, setTier] = useState<ModelTier>("tier-1");
  const processedRef = useRef(0);

  useEffect(() => {
    processedRef.current = 0;
  }, [current?.sourceKey, tier]);

  return (
    <div
      className="agui-chat"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "0.75rem",
        height: "100%",
      }}
    >
      <div>
        <label
          htmlFor="tier-select"
          className="block text-xs uppercase tracking-wide text-[var(--color-secondary)]"
        >
          Model tier
        </label>
        <select
          id="tier-select"
          value={tier}
          onChange={(e) => setTier(e.target.value as ModelTier)}
          className="mt-1 block w-full rounded border border-[var(--color-primary)] px-2 py-1 text-sm"
          style={{
            background: "var(--color-background)",
            color: "var(--color-text)",
          }}
        >
          <option value="tier-1">Tier 1 — {TIER_LABEL["tier-1"]}</option>
          <option value="tier-2">Tier 2 — {TIER_LABEL["tier-2"]} (fallback)</option>
          <option value="tier-3">Tier 3 — {TIER_LABEL["tier-3"]} (final fallback)</option>
        </select>
        <p className="mt-1 text-xs text-[var(--color-secondary)]/60">
          Active palette: {current?.sourceName ?? "loading…"}
        </p>
      </div>
      <div
        style={{
          flex: 1,
          minHeight: "300px",
          border: "1px solid var(--color-secondary)/30",
          borderRadius: "0.25rem",
          padding: "0.5rem",
        }}
      >
        <CopilotKit runtimeUrl="/api/copilotkit" agent="gemini_hackathon_agent">
          <CopilotChat
            labels={{
              title: "Gemini Hackathon Agent",
              initial:
                "Hi! I can extract palettes, generate equivalencies, or detect curriculum changes. Ask me anything.",
            }}
          />
        </CopilotKit>
      </div>
    </div>
  );
}
