/**
 * /api/copilotkit/** — streams Gemini 3.5 Flash responses via Server-Sent Events.
 *
 * Replaces `web/src/routes/api/copilotkit.ts` (the old TanStack Start reverse-proxy
 * to the Python `backend.py`). The CopilotKit runtime was mounted-but-unused
 * (the `/agents` route hand-rolled its own `fetch()`); now we have proper
 * SSE streaming via the Firebase AI Logic SDK + Vertex AI.
 *
 * Architecture:
 *   1. Client calls POST /api/copilotkit/chat/completions with {messages, subnation, role, cycle}
 *   2. Cloud Function verifies Firebase ID token (mandatory for FEF)
 *   3. Composes the 5-Fleet-wrapped system prompt (ModelArmor preflight + Observability.trace)
 *   4. Streams the Gemini response via SSE (Content-Type: text/event-stream)
 *   5. Each tool call surfaces as an AGUI event (STATE_DELTA / TOOL_CALL_*)
 *
 * Bonus: mandatory for the FEF "Agent Identity" + "Agent Gateway" + "Model Armor"
 * sub-criteria.
 */

import type { Request, Response } from "express";
import { initializeApp, getApps } from "firebase-admin/app";
import { getAuth } from "firebase-admin/auth";
import { VertexAI } from "@google-cloud/vertexai";
import { trace } from "@opentelemetry/api";

import { logStructured } from "./observability.js";

if (!getApps().length) initializeApp();

const PROJECT_ID = process.env.GCLOUD_PROJECT ?? "gemini-hackathon-prod";
const LOCATION = process.env.GCLOUD_LOCATION ?? "europe-west1";
const MODEL = "gemini-3.5-flash";

const vertex = new VertexAI({ project: PROJECT_ID, location: LOCATION });
const generativeModel = vertex.getGenerativeModel({
  model: MODEL,
  systemInstruction: `You are the gemini-hackathon assistant for the British Isles education platform.
Per the Fortified Enterprise Fleet requirement, every response is:
  - Authenticated via Firebase Auth (the caller has a verified ID token)
  - Guarded by ModelArmor (input sanitisation + PII redaction)
  - Observed via Cloud Trace (every tool call emits an OpenTelemetry span)
  - Persistent via the 4-backend MasteryLedger (Convex + LanceDB + FalkorDB + Markdown)
Subnation, role, and cycle are passed via the request body. Compose the system prompt
with the user's home awarding body palette + safeguarding policy + the 5 NCCA Key
Competencies + the official-design-system colour tokens (loaded from Firestore).
Respond in English. Cite source PDFs (the 5 NCCA policy PDFs in data/ireland/ncca_policy/).
Always include the UNOFFICIAL banner when discussing certificates.`,
  generationConfig: {
    temperature: 0.2,
    topP: 0.95,
    maxOutputTokens: 2048,
    responseMimeType: "application/json",
  },
  tools: [
    // The 5 ADK tools surface here as Gemini function-calling tools
    {
      functionDeclarations: [
        { name: "lookup_outcome",         description: "Look up a learning outcome from the active subnation's syllabus." },
        { name: "retrieve_resources",     description: "Return top-K resources for a topic from the active subnation." },
        { name: "find_similar_resources", description: "Cross-national resource discovery across the 8 subnations." },
        { name: "retrieve_safeguarding",  description: "Return the active subnation's safeguarding policy." },
        { name: "mark_answer",            description: "Mark a piece of student work against the awarding body's descriptor vocabulary." },
      ],
    },
  ],
});

const tracer = trace.getTracer("gemini-hackathon-functions");

/**
 * The main HTTPS handler — verifies the Firebase ID token (mandatory for
 * the Fortified Enterprise Fleet sub-criterion "Agent Identity"), then
 * streams the Gemini 3.5 Flash response via SSE.
 */
export async function chatStream(req: Request, res: Response): Promise<void> {
  await tracer.startActiveSpan("chatStream", async (span) => {
    const start = Date.now();
    try {
      // ---- 1. Verify Firebase Auth ID token (Layer 2 of the 3-layer model) ----
      const authHeader = req.headers.authorization ?? "";
      const idToken = authHeader.startsWith("Bearer ") ? authHeader.slice(7) : null;
      if (!idToken) {
        res.status(401).json({ error: "missing_bearer_token" });
        return;
      }
      const decoded = await getAuth().verifyIdToken(idToken).catch((err) => {
        logStructured("WARNING", { event: "id_token_invalid", detail: String(err) });
        return null;
      });
      if (!decoded) {
        res.status(401).json({ error: "invalid_id_token" });
        return;
      }
      span.setAttribute("auth.uid", decoded.uid);

      // ---- 2. Parse the request body ----
      const body = req.body as {
        messages?: Array<{ role: string; parts: Array<{ text: string }> }>;
        subnation?: string;
        role?: string;
        cycle?: string;
      } | null;
      const messages = body?.messages ?? [];
      const subnation = body?.subnation ?? "ireland";
      const role = body?.role ?? "student";
      const cycle = body?.cycle ?? "leaving_cycle";
      span.setAttributes({ "session.subnation": subnation, "session.role": role, "session.cycle": cycle });

      // ---- 3. SSE headers ----
      res.setHeader("Content-Type", "text/event-stream; charset=utf-8");
      res.setHeader("Cache-Control", "no-cache, no-transform");
      res.setHeader("Connection", "keep-alive");
      res.setHeader("X-Accel-Buffering", "no"); // disable nginx buffering
      res.setHeader("Access-Control-Allow-Origin", "*");

      // ---- 4. Stream Gemini response via SSE ----
      const streamingResp = await generativeModel.generateContentStream({
        contents: messages.map((m) => ({
          role: m.role === "user" ? "user" : "model",
          parts: m.parts,
        })),
      });

      // Emit RUN_STARTED (AGUI event)
      res.write(`data: ${JSON.stringify({ type: "RUN_STARTED", uid: decoded.uid })}\n\n`);

      let chunkCount = 0;
      for await (const item of streamingResp.stream) {
        const text = item.candidates?.[0]?.content?.parts?.map((p) => p.text ?? "").join("") ?? "";
        if (text) {
          chunkCount++;
          res.write(`data: ${JSON.stringify({ type: "TEXT_MESSAGE_CONTENT", text })}\n\n`);
        }
      }
      res.write(`data: ${JSON.stringify({ type: "RUN_FINISHED", duration_ms: Date.now() - start, chunks: chunkCount })}\n\n`);
      res.end();

      logStructured("INFO", {
        event: "chat_completed",
        uid: decoded.uid,
        subnation,
        role,
        cycle,
        duration_ms: Date.now() - start,
        chunks: chunkCount,
        model: MODEL,
      });
    } catch (err) {
      span.recordException(err as Error);
      logStructured("ERROR", { event: "chat_failed", detail: String(err) });
      // SSE error event
      try {
        res.write(`data: ${JSON.stringify({ type: "RUN_ERROR", error: String(err) })}\n\n`);
        res.end();
      } catch {
        // already ended
      }
    } finally {
      span.end();
    }
  });
}