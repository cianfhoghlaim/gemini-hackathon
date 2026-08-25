/**
 * The archipelagic unity ribbon.
 *
 * Single horizontal element that shows the user's home subnation first +
 * all other BI subnations behind it, all in the active palette's colour.
 * Renders the "one platform for the British Isles" message.
 */

import { SUBNATIONS } from "../../types/session";
import type { ActiveSubnation } from "../../types/session";

export function ArchipelagicRibbon({ activeSubnation }: { activeSubnation: ActiveSubnation }) {
  return (
    <div
      className="rounded p-3 flex items-center gap-3 text-sm"
      style={{
        background: "var(--color-primary)/8",
        borderColor: "var(--color-primary)",
      }}
    >
      <span className="font-[var(--font-heading)] text-[var(--color-primary)] whitespace-nowrap">
        The British Isles
      </span>
      <span className="text-xs text-[var(--color-text)]/50">·</span>
      <div className="flex items-center gap-2 flex-wrap">
        {SUBNATIONS.map((s) => {
          const isActive = s.code === activeSubnation;
          return (
            <span
              key={s.code}
              className={`${isActive ? "font-bold" : "opacity-60"}`}
              style={isActive ? { color: "var(--color-primary)" } : undefined}
              title={s.name}
            >
              {s.flag}
            </span>
          );
        })}
      </div>
      <span className="ml-auto text-xs text-[var(--color-text)]/50">
        one platform · 8 nations
      </span>
    </div>
  );
}
