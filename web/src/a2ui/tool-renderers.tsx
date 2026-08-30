/**
 * Tool-call renderers registered with <CopilotKitProvider renderToolCalls={...}>.
 *
 * Each renderer maps a server-side tool name to a React component. The agent
 * emits a TOOL_CALL_RESULT message; the renderer reads the args and the
 * result, then renders the React node inline in the chat stream.
 *
 * The shape is `defineToolCallRenderer({ name, args, render })` from
 * @copilotkit/react-core/v2 — args is a Standard Schema V1 (Zod works) and
 * `render` gets `{ toolCall, toolMessage, status, args }` props.
 */

import { z } from "zod";
import { defineToolCallRenderer } from "@copilotkit/react-core/v2";
import { CitationPill } from "./catalog";

/** Server-side `cite_pdf` tool: surface the citation as a clickable pill. */
export const citePdfRenderer = defineToolCallRenderer({
  name: "cite_pdf",
  args: z.object({
    pdf_id: z.string(),
    page: z.number(),
    snippet: z.string(),
  }),
  render: ({ status, args }) => {
    if (status === "executing") {
      return (
        <span className="opacity-50 text-xs">
          ⏳ citing {args.pdf_id} p.{args.page}…
        </span>
      );
    }
    return (
      <CitationPill
        pdf_id={args.pdf_id ?? ""}
        page={args.page ?? 0}
        snippet={args.snippet ?? ""}
      />
    );
  },
});