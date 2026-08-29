/**
 * Cloud Logging + Cloud Trace init (the OpenTelemetry exporter).
 *
 * Wires the global tracer + logger so every Cloud Function in this repo
 * emits spans to Google Cloud Trace + log entries to Google Cloud Logging,
 * automatically correlated via the same trace ID.
 *
 * Per the All Things Agentic Hackathon Fortified Enterprise Fleet
 * sub-criterion "Agent Observability (OpenTelemetry-compliant audit logs
 *  and end-to-end reasoning chain traces)" — this is THE wiring.
 */

import { trace, type Tracer } from "@opentelemetry/api";
import {
  BatchSpanProcessor,
  type ReadableSpan,
  type Span,
} from "@opentelemetry/sdk-trace-base";
import { NodeTracerProvider } from "@opentelemetry/sdk-trace-node";
import { Resource } from "@opentelemetry/resources";
import {
  ATTR_SERVICE_NAME,
  ATTR_SERVICE_VERSION,
} from "@opentelemetry/semantic-conventions";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-http";
import { HttpInstrumentation } from "@opentelemetry/instrumentation-http";
import { VertexAIInstrumentation } from "@opentelemetry/instrumentation-vertexai";
import { Logging } from "@google-cloud/logging";

// Per-function resource attributes (overridden per function)
const SERVICE_NAME = "gemini-hackathon-functions";
const SERVICE_VERSION = "0.1.0";
const PROJECT_ID = process.env.GCLOUD_PROJECT ?? "gemini-hackathon-prod";
const REGION = process.env.FUNCTION_REGION ?? "europe-west1";

// Cloud Logging (the canonical structured logger)
const logging = new Logging({ projectId: PROJECT_ID });
const cloudLog = logging.log("gemini-hackathon-agents");

// OpenTelemetry: Cloud Trace exporter (uses OTLP HTTP to Cloud Trace)
// Note: Cloud Functions Gen2 + Cloud Run have OTLP exporters built in
// — we just need to register the SDK + instrument HTTP/VertexAI.
const provider = new NodeTracerProvider({
  resource: new Resource({
    [ATTR_SERVICE_NAME]: SERVICE_NAME,
    [ATTR_SERVICE_VERSION]: SERVICE_VERSION,
    "cloud.region": REGION,
  }),
});

// Cloud Trace exporter (OTLP HTTP endpoint)
const traceExporter = new OTLPTraceExporter({
  url: `https://telemetry.googleapis.com/v1/traces`,
});

provider.addSpanProcessor(
  new BatchSpanProcessor(traceExporter, {
    maxQueueSize: 2048,
    maxExportBatchSize: 512,
    scheduledDelayMillis: 5000,
  }),
);

// Auto-instrumentation: HTTP + Vertex AI (the two surfaces that matter)
const instrumentations = [
  new HttpInstrumentation({
    ignoreIncomingRequestHook: (req) => {
      const url = req.url ?? "";
      return url.includes("/healthz") || url.includes("/_ah/");
    },
  }),
  new VertexAIInstrumentation(),
];

provider.register({ instrumentations });

// Re-export the global tracer + a typed Cloud Logging helper
export const tracer: Tracer = trace.getTracer(SERVICE_NAME, SERVICE_VERSION);

/**
 * Structured logger that writes to Cloud Logging as a JSON entry with the
 * active trace ID + span ID correlated.
 */
export function logStructured(
  severity: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL",
  payload: Record<string, unknown>,
): void {
  const span = trace.getActiveSpan();
  const entry = cloudLog.entry(
    {
      severity,
      span: span
        ? { traceId: span.spanContext().traceId, spanId: span.spanContext().spanId }
        : undefined,
      labels: { function_name: process.env.FUNCTION_TARGET ?? "unknown" },
      resource: { type: "global" },
    },
    payload,
  );
  cloudLog.write(entry).catch((err) => {
    // never throw from logging
    console.error("logStructured failed", err);
  });
}

/** Flush pending spans on shutdown (called from `process.on('SIGTERM')`). */
export async function shutdownTelemetry(): Promise<void> {
  await provider.shutdown();
}