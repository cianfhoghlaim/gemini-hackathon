/**
 * Browser-side observability — wires Firebase Performance + Cloud Logging.
 *
 * Per the All Things Agentic Hackathon Fortified Enterprise Fleet sub-criterion
 * "Agent Observability (OpenTelemetry-compliant audit logs and end-to-end
 *  reasoning chain traces)" — every client-side action emits an event.
 *
 * Uses `console.log` for the dev surface + `fetch` to `/api/log` for the
 * production surface (which forwards to Google Cloud Logging via the
 * Cloud Function in `functions/src/chat.ts`).
 */

type LogSeverity = "debug" | "info" | "warn" | "error";

export function logStructured(
  severity: LogSeverity,
  payload: Record<string, unknown>,
): void {
  const entry = JSON.stringify({ severity, ts: new Date().toISOString(), ...payload });
  if (import.meta.env.DEV) {
    // dev: pretty-print to console
    const fn = severity === "error" ? console.error
            : severity === "warn"  ? console.warn
            : console.log;
    fn(`[${severity.toUpperCase()}]`, entry);
  }
  if (typeof window !== "undefined") {
    // prod: batch + ship to /api/log → Cloud Logging
    const w = window as unknown as { __logBuffer?: Array<{ severity: LogSeverity; payload: Record<string, unknown> }> };
    (w.__logBuffer ??= []).push({ severity, payload });
    if ((w.__logBuffer ?? []).length >= 25) flushLogs();
  }
}

let _flushing = false;
export async function flushLogs(): Promise<void> {
  if (_flushing) return;
  if (typeof window === "undefined") return;
  _flushing = true;
  try {
    const w = window as unknown as { __logBuffer?: Array<{ severity: LogSeverity; payload: Record<string, unknown> }> };
    const batch = w.__logBuffer ?? [];
    if (batch.length === 0) return;
    w.__logBuffer = [];
    try {
      await fetch("/api/log", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ entries: batch }),
        keepalive: true,
      });
    } catch {
      // re-buffer if flush fails
      w.__logBuffer = [...batch, ...(w.__logBuffer ?? [])].slice(-100);
    }
  } finally {
    _flushing = false;
  }
}

// Auto-flush on unload
if (typeof window !== "undefined") {
  window.addEventListener("beforeunload", () => { void flushLogs(); });
  window.addEventListener("pagehide",        () => { void flushLogs(); });
}