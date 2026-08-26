/**
 * Browser-side DuckDB-WASM engine. Reads the gemini_hackathon.duckdb file
 * over HTTP range requests — same SQL dialect as server-side DuckDB.
 */

import { useEffect, useState } from "react";

// duckdb-wasm types are incomplete in v1.29; untyped declare.
declare const duckdb: any;

let cachedDb: any = null;

async function getDb(): Promise<any> {
  if (cachedDb) return cachedDb;
  const bundle = await duckdb.selectBundle(duckdb.getJsDelivrBundles());
  const worker = new Worker(
    new URL("@duckdb/duckdb-wasm", import.meta.url),
    { type: "module" },
  );
  const logger = new duckdb.ConsoleLogger();
  cachedDb = await duckdb.AsyncDuckDB.create(worker, bundle, logger);
  return cachedDb;
}

export interface ComparisonRow {
  pdf_sha256: string;
  pdf_path: string;
  model_key: string;
  model_alias: string | null;
  backend: string;
  profile: string;
  family: string;
  role: string;
  content: string;
  latency_ms: number;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
  ragas_score: number;
  ragas_breakdown: string;
  captured_at: string;
}

const DUCKDB_URL = "/api/duckdb";

export function useDuckDb(): {
  db: any;
  error: string | null;
  query: <T = unknown>(sql: string) => Promise<T[]>;
} {
  const [db, setDb] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const instance = await getDb();
        if (cancelled) return;
        const resp = await fetch(DUCKDB_URL);
        if (!resp.ok) {
          throw new Error(
            `DuckDB file not available (HTTP ${resp.status}). Run 'gemini-hackathon compare --pdf data/syllabi/sample_lc_maths_2024.pdf' to materialise it.`,
          );
        }
        const buf = new Uint8Array(await resp.arrayBuffer());
        await instance.registerFileBuffer("gemini.duckdb", buf);
        await instance.open({ path: "gemini.duckdb" });
        setDb(instance);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const query = async <T = unknown>(sql: string): Promise<T[]> => {
    if (!db) throw new Error("DuckDB not yet initialised");
    const conn = await db.connect();
    try {
      const result = await conn.query(sql);
      return (result.toArray?.() ?? []) as unknown as T[];
    } finally {
      await conn.close();
    }
  };

  return { db, error, query };
}

export function useComparisonLeaderboard() {
  const { query } = useDuckDb();
  return {
    fetchLeaderboard: async (): Promise<ComparisonRow[]> => {
      return query<ComparisonRow>(`
        SELECT
          pdf_sha256, pdf_path, model_key, model_alias, backend, profile,
          family, role, content, latency_ms, tokens_in, tokens_out,
          cost_usd, ragas_score, ragas_breakdown, captured_at
        FROM model_comparisons
        ORDER BY ragas_score DESC, latency_ms ASC
      `);
    },
  };
}

export function useDocumentExplorer() {
  const { query } = useDuckDb();
  return {
    fetchDocuments: async (): Promise<{
      source_key: string;
      pdf_path: string;
      page_count: number;
      sha256_hash: string;
      subject: string;
      level: string;
      jurisdiction: string;
    }[]> => {
      return query<{
        source_key: string;
        pdf_path: string;
        page_count: number;
        sha256_hash: string;
        subject: string;
        level: string;
        jurisdiction: string;
      }>(`
        SELECT
          source_key, pdf_path, page_count, sha256_hash,
          subject, level, jurisdiction
        FROM official_documents
        ORDER BY jurisdiction, subject
      `);
    },
  };
}
