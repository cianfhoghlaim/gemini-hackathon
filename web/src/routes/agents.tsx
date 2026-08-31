/**
 * /agents — the ADK-powered chat agent (CopilotKit v2 + AG-UI + A2UI).
 *
 * Replaces the prior hand-rolled SSE handler (fetch("/api/copilotkit/
 * chat/completions")) with the v2 client primitives:
 *
 *   useAgent()         — reactive state for the active agent (messages +
 *                        isRunning + threadId); pushes the session into
 *                        the agent's state via agent.setState before each
 *                        turn; agent.addMessage() posts a new user turn
 *                        followed by agent.runAgent() to start the run.
 *
 *   useFrontendTool()  — module-level registration (handled at the
 *                        <CopilotKitProvider> in src/routes/__root.tsx
 *                        via `frontendTools={[setThemeColorTool]}` —
 *                        we don't call it here).
 *
 *   useRenderToolCall  — server-side tool result UI (also wired via
 *                        `renderToolCalls={[citePdfRenderer]}` in
 *                        src/routes/__root.tsx).
 *
 * The A2UI panels surface via <A2UIRenderer/> from the
 * @copilotkit/a2ui-renderer package — driven by the catalog mounted
 * in src/routes/__root.tsx.
 */

import { Component, type ErrorInfo, type ReactNode, useRef, useState } from "react";
import { useAgent } from "@copilotkit/react-core/v2";
import { A2UIRenderer, DEFAULT_SURFACE_ID } from "@copilotkit/a2ui-renderer";
import { useSession } from "../components/session/SessionContext";

/**
 * Defensive error boundary so a missing A2UI runtime / unrecognised catalog
 * schema doesn't crash the whole chat page — the chat surface still renders
 * even if the JSONL → React bridge is unavailable.
 */
class A2UIErrorBoundary extends Component<
  { children: ReactNode; fallback: ReactNode },
  { error: Error | null }
> {
  state = { error: null as Error | null };
  static getDerivedStateFromError(error: Error) {
    return { error };
  }
  componentDidCatch(error: Error, info: ErrorInfo) {
    console.warn("[A2UI] renderer error:", error, info);
  }
  render() {
    if (this.state.error) return this.props.fallback;
    return this.props.children;
  }
}

export default function AgentChatPage(): React.ReactNode {
  const { subnation } = useSession();
  const { agent, isReady } = useAgent({ agentId: "ncca_panel" });
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);

  // The session is already pushed into the agent via SessionAgentContext
  // (mounted in __root.tsx) — subnation, role, cycle, subjects, and
  // safeguarding source are all available via useAgentContext slots.

  async function send() {
    const input = inputRef.current;
    if (!input || !input.value.trim()) return;
    const message = input.value.trim();
    input.value = "";
    setError(null);
    try {
      agent.addMessage({
        id: crypto.randomUUID(),
        role: "user",
        content: message,
      });
      await agent.runAgent();
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-4">
      <header>
        <h1 className="text-3xl font-[var(--font-heading)] text-[var(--color-primary)]">
          {subnation.flag} {subnation.name} agent
        </h1>
        <p className="text-sm text-[var(--color-text)]/70">
          {subnation.awardingBody} · {subnation.awardingBodyShort} ·{" "}
          {isReady ? (agent.isRunning ? "running…" : "ready") : "connecting…"}
        </p>
      </header>

      <section
        className="rounded border p-4 space-y-2 h-96 overflow-y-auto"
        style={{
          borderColor: "var(--color-secondary)/20",
          background: "var(--color-background)",
        }}
      >
        {agent.messages.map((m, i) => (
          <div
            key={m.id ?? i}
            className={`p-3 rounded ${
              m.role === "user"
                ? "bg-[var(--color-primary)]/10 ml-12"
                : "bg-[var(--color-secondary)]/10 mr-12"
            }`}
          >
            <div className="text-xs text-[var(--color-text)]/50 mb-1">
              {m.role === "user" ? "You" : subnation.awardingBodyShort}
            </div>
            <div className="text-sm whitespace-pre-wrap">
              {typeof m.content === "string"
                ? m.content
                : JSON.stringify(m.content)}
            </div>
          </div>
        ))}
        {agent.isRunning && (
          <div className="text-xs text-[var(--color-text)]/50 italic">
            {subnation.awardingBodyShort} is thinking…
          </div>
        )}
      </section>

      <section data-testid="a2ui-surface-mount" className="mt-4">
        <A2UIErrorBoundary
          fallback={
            <div className="text-xs text-[var(--color-text)]/40 italic">
              A2UI panel unavailable — chat continues above.
            </div>
          }
        >
          <A2UIRenderer surfaceId={DEFAULT_SURFACE_ID} />
        </A2UIErrorBoundary>
      </section>

      {error && (
        <div
          className="rounded border p-3 text-sm"
          style={{
            borderColor: "var(--color-secondary)",
            color: "var(--color-secondary)",
          }}
        >
          {error}
        </div>
      )}

      <section className="flex gap-2">
        <input
          ref={inputRef}
          type="text"
          placeholder={`Ask the ${subnation.awardingBodyShort} agent…`}
          onKeyDown={(e) => e.key === "Enter" && send()}
          disabled={!isReady || agent.isRunning}
          className="flex-1 px-3 py-2 rounded border text-sm"
          style={{
            borderColor: "var(--color-secondary)/30",
            background: "var(--color-background)",
            color: "var(--color-text)",
          }}
        />
        <button
          type="button"
          onClick={send}
          disabled={!isReady || agent.isRunning}
          className="px-4 py-2 rounded text-sm"
          style={{
            background: "var(--color-primary)",
            color: "var(--color-background)",
            opacity: !isReady || agent.isRunning ? 0.5 : 1,
          }}
        >
          {agent.isRunning ? "…" : "Send"}
        </button>
      </section>
    </div>
  );
}