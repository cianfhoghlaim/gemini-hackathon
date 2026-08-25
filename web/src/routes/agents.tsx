/**
 * /agents — the ADK-powered chat agent.
 *
 * The active session (subnation, role, cycle, subjects) is sent to the
 * Python backend's /api/chat/completions endpoint, which composes the
 * ADK agent's system prompt from the session and the per-tool
 * implementations in `gemini_hackathon.agents.tools`.
 */

import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useSession } from "../components/session/SessionContext";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export const Route = createFileRoute("/agents")({
  component: AgentChatPage,
});

function AgentChatPage() {
  const { subnation, session } = useSession();
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content: `Hi! I'm your assistant for ${subnation.flag} ${subnation.name}. I know the ${subnation.awardingBodyShort} syllabus and the active safeguarding policy. Ask me anything, or use "Find resources that help" to discover cross-national resources.`,
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function send() {
    if (!input.trim() || loading) return;
    const userMsg: ChatMessage = { role: "user", content: input };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/copilotkit/chat/completions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [...messages, userMsg].map((m) => ({
            role: m.role,
            content: m.content,
          })),
          temperature: 0.2,
        }),
      });
      if (!res.ok) {
        const detail = await res.text();
        setError(`Backend error: ${res.status} — ${detail.slice(0, 200)}`);
        return;
      }
      const body = await res.json();
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: body.choices?.[0]?.message?.content ?? "(no response)",
        },
      ]);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-4">
      <header>
        <h1 className="text-3xl font-[var(--font-heading)] text-[var(--color-primary)]">
          {subnation.flag} {subnation.name} agent
        </h1>
        <p className="text-sm text-[var(--color-text)]/70">
          {subnation.awardingBody} · {subnation.awardingBodyShort} ·
          {session?.role ?? "guest"} · {session?.cycle?.replace(/_/g, " ") ?? "—"}
        </p>
      </header>

      <section
        className="rounded border p-4 space-y-2 h-96 overflow-y-auto"
        style={{ borderColor: "var(--color-secondary)/20", background: "var(--color-background)" }}
      >
        {messages.map((m, i) => (
          <div
            key={i}
            className={`p-3 rounded ${
              m.role === "user"
                ? "bg-[var(--color-primary)]/10 ml-12"
                : "bg-[var(--color-secondary)]/10 mr-12"
            }`}
          >
            <div className="text-xs text-[var(--color-text)]/50 mb-1">
              {m.role === "user" ? "You" : subnation.awardingBodyShort}
            </div>
            <div className="text-sm whitespace-pre-wrap">{m.content}</div>
          </div>
        ))}
        {loading && (
          <div className="text-xs text-[var(--color-text)]/50 italic">
            {subnation.awardingBodyShort} is thinking…
          </div>
        )}
      </section>

      {error && (
        <div className="rounded border p-3 text-sm" style={{ borderColor: "var(--color-secondary)", color: "var(--color-secondary)" }}>
          {error}
        </div>
      )}

      <section className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder={`Ask the ${subnation.awardingBodyShort} agent…`}
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
          disabled={loading || !input.trim()}
          className="px-4 py-2 rounded text-sm"
          style={{
            background: "var(--color-primary)",
            color: "var(--color-background)",
            opacity: loading || !input.trim() ? 0.5 : 1,
          }}
        >
          {loading ? "…" : "Send"}
        </button>
      </section>
    </div>
  );
}
