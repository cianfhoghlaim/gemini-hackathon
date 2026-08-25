/**
 * Find resources that help — the cross-national resource discovery page.
 *
 * Triggered from the home page (per-role quick action), the subjects
 * detail cards, and the chat agent. Surfaces resources from OTHER
 * British Isles jurisdictions that may help with the user's topic.
 *
 * In dev (no RAG corpus), the page calls the Python backend's
 * /api/chat/completions endpoint with a fixed prompt that exercises
 * the ADK agent's `find_similar_resources` tool. The Python backend
 * runs the stub tool and returns labelled cross-national matches.
 *
 * In production: BAML ExtractResource → RAG top-K → ADK agent surfaces
 * the results with citations to source PDF + page + outcome_id.
 */

import { createFileRoute, useLoaderData, useSearch } from "@tanstack/react-router";
import { useState } from "react";
import { useSession } from "../components/session/SessionContext";

export const Route = createFileRoute("/find-resources")({
  validateSearch: (search: Record<string, unknown> = {}): { subject?: string; topic?: string } => {
    const s = (search ?? {}) as Record<string, unknown>;
    return {
      subject: typeof s.subject === "string" ? s.subject : undefined,
      topic: typeof s.topic === "string" ? s.topic : undefined,
    };
  },
  loader: async ({ search }) => {
    // The loader pre-fetches results if subject/topic are in the query string.
    if ((search?.subject) || (search?.topic)) {
      return { ready: true, search };
    }
    return { ready: false, search: {} };
  },
  component: FindResourcesPage,
});

interface FindResourcesResult {
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

function FindResourcesPage() {
  const { subnation } = useSession();
  const search = useSearch({ from: "/find-resources" });
  const loaderData = useLoaderData({ from: "/find-resources" }) as { ready: boolean; search: any };
  const [topic, setTopic] = useState(search?.topic ?? search?.subject ?? "Algebra");
  const [results, setResults] = useState<FindResourcesResult[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function runSearch() {
    setLoading(true);
    setError(null);
    setResults(null);
    try {
      const res = await fetch("/api/copilotkit/chat/completions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [{
            role: "user",
            content: `Find resources from other British Isles jurisdictions that may help with ${topic}. I'm in ${subnation.name} (${subnation.awardingBodyShort}). Use the find_similar_resources tool.`,
          }],
          temperature: 0.2,
        }),
      });
      if (!res.ok) {
        const detail = await res.text();
        setError(`Backend error: ${res.status} — ${detail.slice(0, 200)}`);
        return;
      }
      const body = await res.json();
      // The ADK tool returns a list of {source_subnation, source_name, ...} objects.
      // In dev (stub), the backend returns a JSON-encoded list inside content.
      try {
        const parsed = JSON.parse(body.choices?.[0]?.message?.content ?? "[]");
        if (Array.isArray(parsed)) {
          setResults(parsed);
        } else {
          setResults([]);
        }
      } catch {
        setResults([]);
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
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
          <strong>{subnation.flag} {subnation.name}</strong>. The agent
          searches the official sources of the other 4 active British
          Isles jurisdictions and surfaces resources that may help you.
          Each result is labelled with its source nation.
        </p>
      </header>

      <section className="rounded border p-4 space-y-3" style={{ borderColor: "var(--color-primary)" }}>
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
            disabled={loading || !topic}
            className="px-4 py-2 rounded text-sm"
            style={{
              background: "var(--color-primary)",
              color: "var(--color-background)",
              opacity: loading ? 0.5 : 1,
            }}
          >
            {loading ? "Searching…" : "Find resources"}
          </button>
        </div>
        <p className="text-xs text-[var(--color-text)]/50">
          Searches: 4 other active British Isles jurisdictions
          (England, Scotland, Wales, Northern Ireland)
        </p>
      </section>

      {error && (
        <div className="rounded border p-3 text-sm" style={{ borderColor: "var(--color-secondary)", color: "var(--color-secondary)" }}>
          {error}
        </div>
      )}

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
                <h3 className="font-[var(--font-heading)] text-lg">{r.title}</h3>
                <span className="ml-auto text-xs text-[var(--color-text)]/50">
                  score {(r.score * 100).toFixed(0)}%
                </span>
              </header>
              <p className="text-xs text-[var(--color-text)]/60 mt-1">
                {r.source_name} · {r.awarding_body} · {r.resource_type}
              </p>
              <p className="text-sm text-[var(--color-text)]/80 mt-2">{r.rationale}</p>
            </article>
          ))}
        </section>
      )}

      {results && results.length === 0 && !loading && (
        <p className="text-sm text-[var(--color-text)]/60 text-center">
          No results yet. Enter a topic above and click Find resources.
        </p>
      )}
    </div>
  );
}
