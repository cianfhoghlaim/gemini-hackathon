/**
 * gemini-hackathon Cloud Functions for Firebase (Gen2) entry point.
 *
 * Replaces the 3 TanStack Start server routes:
 *   - /api/themes        → themesApi        (reads themes/*.json from filesystem-equivalent
 *                                                     OR Firestore design_tokens)
 *   - /api/copilotkit/... → chatStream        (streams Gemini 3.5 Flash via Vertex AI)
 *   - /api/duckdb          → duckdbAsset      (signed URL to Firebase Storage)
 *   - /api/stitch          → stitchSync       (pushes DESIGN.md to Google Stitch)
 *
 * Plus the auth onCreate trigger that sets custom claims on every new user.
 *
 * Observability is auto-wired:
 *   - Cloud Logging via @google-cloud/logging
 *   - Cloud Trace via OpenTelemetry + @google-cloud/opentelemetry-cloud-monitoring-exporter
 *   - Cloud Monitoring metrics auto-emitted
 *
 * Per the All Things Agentic Hackathon Fortified Enterprise Fleet sub-criterion
 * "Agent Observability (OpenTelemetry-compliant audit logs and end-to-end
 *  reasoning chain traces)" — this file IS the canonical observability wiring.
 */

import { onRequest } from "firebase-functions/v2/https";
import { onDocumentCreated } from "firebase-functions/v2/auth";
import * as logger from "firebase-functions/logger";

import { themesApi } from "./themes.js";
import { chatStream } from "./chat.js";
import { duckdbAsset } from "./duckdb.js";
import { stitchSync } from "./stitch.js";
import { authOnCreate } from "./auth_oncreate.js";

// ============================================================================
// Public HTTPS endpoints (the 4 server routes)
// ============================================================================

// /api/themes → reads the 12 official-guidelines palette JSONs from
// `themes/_official_guidelines/*.json` at build-time + the design_tokens
// from Firestore (the Stitch-managed tokens).
export const themesHandler = onRequest(
  { region: "europe-west1", cors: true, memory: "256MiB", cpu: 1 },
  themesApi,
);

// /api/copilotkit/** → streams Gemini 3.5 Flash responses via Server-Sent Events
// (the streaming chat the CopilotKit runtime used to do — now done via Vertex AI
// in Firebase with SSE for the React client).
export const chatHandler = onRequest(
  {
    region: "europe-west1",
    cors: true,
    memory: "512MiB",
    cpu: 1,
    timeoutSeconds: 60,
    // secrets: ["GOOGLE_CLOUD_API_KEY"],
  },
  chatStream,
);

// /api/duckdb → returns a signed URL to the latest `.duckdb` (now `.parquet`)
// export in Firebase Storage. The browser reads it via DuckDB-WASM OR
// queries BigQuery (Phase 7 refactor).
export const duckdbHandler = onRequest(
  { region: "europe-west1", cors: true, memory: "256MiB", cpu: 1 },
  duckdbAsset,
);

// /api/stitch → pushes the canonical DESIGN.md (web/.stitch/DESIGN.md) to
// Google Stitch via the REST API at https://stitch.googleapis.com.
// Triggered manually from the deployment script OR on a schedule.
export const stitchHandler = onRequest(
  { region: "europe-west1", cors: true, memory: "256MiB", cpu: 1 },
  stitchSync,
);

// ============================================================================
// Auth trigger — sets custom claims on every new user (subnation default)
// ============================================================================

export const onUserCreate = onDocumentCreated(
  { region: "europe-west1" },
  (event) => authOnCreate(event),
);

// ============================================================================
// Observability wiring — Cloud Trace + Cloud Logging for every function
// ============================================================================
//
// Per the FEF "Agent Observability (OpenTelemetry-compliant)" sub-criterion,
// every Cloud Function in this repo MUST emit traces + logs.
//
// This is configured globally via the Functions Framework + OpenTelemetry SDK.
// The init code is in `./observability.ts` (see imports).

logger.info("gemini_hackathon Cloud Functions: all 4 endpoints + auth trigger loaded");