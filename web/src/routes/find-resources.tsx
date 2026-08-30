/**
 * Find resources that help — cross-national resource discovery page
 * (migrated to CopilotKit v2 + react-router-dom).
 *
 * Replaces the prior `fetch("/api/copilotkit/chat/completions")` with the
 * v2 `useAgent()` pattern: agent.messages is the live chat history
 * (streamed from the AG-UI SSE bridge); agent.isRunning is true while
 * a turn is in-flight; `agent.addMessage(...)` posts a new user turn
 * followed by `agent.runAgent()` to start the run.
 *
 * The server-side `find_similar_resources` tool's result is streamed as
 * a TOOL_CALL_RESULT (a `tool` role message); we read the JSON out of
 * its `content` field and surface the list.
 */

import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useAgent } from "@copilotkit/react-core/v2";
import { useSession } from "../components/session/SessionContext";

interface FindResourceResult {
  source_subnation: string;
  source_name: string;
  source_flag: string;
  awarding_body: string;
  resource_type: string;
  title: string;
  url: string;
  score: number;
  rationale: string;
}

export default function FindResourcesPage(): React.ReactNode {
  const { subnation } = useSession();
  const [search] = useSearchParams();
  const [topic, setTopic] = useState(
    search.get("subject") || search.get("topic") || "Algebra",
  );
  const [results, setResults] = useState<FindResourceResult[] | null>(null);

  const { agent, isReady } = useAgent({ agentId: "find_resources" });

  // Watch the agent's tool-call messages; the server-side `find_similar_resources`
  // tool returns a TOOL_CALL_RESULT message; parse it and surface the list.
  useEffect(() => {
    for (let i = agent.messages.length - 1; i >= 0; i--) {
      const m = agent.messages[i];
      if (m.role === "tool") {
        try {
          const parsed = JSON.parse(String(m.content));
          if (Array.isArray(parsed)) {
            setResults(parsed as FindResourceResult[]);
            return;
          }
        } catch {
          /* keep looking */
        }
      }
    }
    setResults(null);
  }, [agent.messages]);

  async function runSearch() {
    setResults(null);
    try {
      agent.addMessage({
        id: crypto.randomUUID(),
        role: "user",
        content: `Find resources from other British Isles jurisdictions that may help with ${topic}. I'm in ${subnation.name} (${subnation.awardingBodyShort}). Use the find_similar_resources tool.`,
      });
      await agent.runAgent();
    } catch (e) {
      console.error("agent.runAgent failed:", e);
    }
  }

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <header>
        <h1 className="text-3xl font-[var(--font-heading)] text-[var(--color-primary)]">
          Find resources that help
        </h1>
        <p className="mt-2 text-sm text-[var(--color-text)]/70">
          Cross-national resource discovery. Your home is{" "}
          <strong>
            {subnation.flag} {subnation.name}
          </strong>
          . The agent searches the official sources of the other 4 active
          British Isles jurisdictions and surfaces resources that may help
          you.
        </p>
      </header>

      <section
        className="rounded border p-4 space-y-3"
        style={{ borderColor: "var(--color-primary)" }}
      >
        <label className="block text-sm font-[var(--font-heading)]">
          What topic are you studying?
        </label>
        <div className="flex gap-2">
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g. Algebra, Mechanics, Shakespeare..."
            className="flex-1 px-3 py-2 rounded border text-sm"
            style={{
              borderColor: "var(--color-secondary)/30",
              background: "var(--color-background)",
              color: "var(--color-text)",
            }}
          />
          <button
            type="button"
            onClick={runSearch}
            disabled={!isReady || agent.isRunning || !topic}
            className="px-4 py-2 rounded text-sm"
            style={{
              background: "var(--color-primary)",
              color: "var(--color-background)",
              opacity: !isReady || agent.isRunning || !topic ? 0.5 : 1,
            }}
          >
            {agent.isRunning ? "Searching…" : "Find resources"}
          </button>
        </div>
        <p className="text-xs text-[var(--color-text)]/50">
          Searches: 4 other active British Isles jurisdictions (England,
          Scotland, Wales, Northern Ireland)
        </p>
      </section>

      {results && results.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-xl font-[var(--font-heading)]">
            {results.length} cross-national matches
          </h2>
          {results.map((r, i) => (
            <article
              key={i}
              className="rounded border p-4"
              style={{ borderColor: "var(--color-secondary)/20" }}
            >
              <header className="flex items-baseline gap-2">
                <span className="text-2xl">{r.source_flag}</span>
                <h3 className="font-[var(--font-heading)] text-lg">
                  {r.title}
                </h3>
                <span className="ml-auto text-xs text-[var(--color-text)]/50">
                  score {(r.score * 100).toFixed(0)}%
                </span>
              </header>
              <p className="text-xs text-[var(--color-text)]/60 mt-1">
                {r.source_name} · {r.awarding_body} · {r.resource_type}
              </p>
              <p className="text-sm text-[var(--color-text)]/80 mt-2">
                {r.rationale}
              </p>
            </article>
          ))}
        </section>
      )}

      {results && results.length === 0 && !agent.isRunning && (
        <p className="text-sm text-[var(--color-text)]/60 text-center">
          No results yet. Enter a topic above and click Find resources.
        </p>
      )}
    </div>
  );
}