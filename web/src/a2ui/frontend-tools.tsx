/**
 * Frontend (client-side) tools registered with
 * <CopilotKitProvider frontendTools={...}>.
 *
 * Each tool is a function the agent can invoke over AG-UI's bidirectional
 * tool-call channel; the runtime streams the tool call from the agent,
 * the client runs `handler`, and the result is sent back over SSE to
 * the agent's next turn.
 *
 * The shape is the `FrontendTool` interface from @copilotkit/core —
 * `parameters` is a Standard Schema V1 (Zod works) and `handler` runs
 * with the inferred arg shape.
 */

import { z } from "zod";
import type { FrontendTool } from "@copilotkit/core";

/** Client-side tool: change the page's primary theme color. */
export const setThemeColorTool: FrontendTool<Record<string, unknown>> = {
  name: "set_theme_color",
  description: "Set the page's primary theme color (hex, e.g. '#0F4C81').",
  parameters: z.object({
    color: z.string().describe("Hex color, e.g. '#0F4C81'."),
  }),
  handler: async ({ color }) => {
    document.documentElement.style.setProperty("--color-primary", String(color));
    return `Set primary color to ${color}.`;
  },
};