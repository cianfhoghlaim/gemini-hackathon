/**
 * /api/duckdb — returns a signed URL to the latest `.parquet` export of
 * the analytics database (was DuckDB-WASM in the browser; now a Parquet
 * export in Firebase Storage + DuckDB-WASM or BigQuery from the client).
 *
 * Replaces `web/src/routes/api/duckdb.ts` (which served a filesystem-read
 * binary `.duckdb`). The `.duckdb` export is run on a Cloud Scheduler →
 * Cloud Function → uploads the latest snapshot to `gs://.../analytics/duckdb.parquet`.
 */

import type { Request, Response } from "express";
import { initializeApp, getApps } from "firebase-admin/app";
import { getStorage } from "firebase-admin/storage";
import { trace } from "@opentelemetry/api";

if (!getApps().length) initializeApp();

const BUCKET = process.env.GEMINI_HACKATHON_STORAGE_BUCKET ?? "gemini-hackathon-prod.appspot.com";
const ANALYTICS_OBJECT = "analytics/duckdb.parquet";
const SIGNED_URL_TTL_MS = 60 * 60 * 1000; // 1 hour

const tracer = trace.getTracer("gemini-hackathon-functions");

export async function duckdbAsset(req: Request, res: Response): Promise<void> {
  await tracer.startActiveSpan("duckdbAsset", async (span) => {
    try {
      const bucket = getStorage().bucket(BUCKET);
      const file = bucket.file(ANALYTICS_OBJECT);
      const [exists] = await file.exists();
      if (!exists) {
        res.status(404).json({
          status: "not_ready",
          message:
            `DuckDB Parquet export not yet materialised at gs://${BUCKET}/${ANALYTICS_OBJECT}. ` +
            "Run 'gemini-hackathon compare --pdf ...' first (or wait for the next Cloud Scheduler trigger).",
        });
        return;
      }
      const [signedUrl] = await file.getSignedUrl({
        version: "v4",
        action: "read",
        expires: Date.now() + SIGNED_URL_TTL_MS,
      });
      // 302 redirect to the signed Cloud Storage URL (cheaper than proxying)
      res.redirect(302, signedUrl);
      span.setAttribute("storage.bucket", BUCKET);
      span.setAttribute("storage.object", ANALYTICS_OBJECT);
    } catch (err) {
      span.recordException(err as Error);
      res.status(500).json({ error: "internal", detail: String(err) });
    } finally {
      span.end();
    }
  });
}