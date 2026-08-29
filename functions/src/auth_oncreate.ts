/**
 * Auth onCreate trigger — sets Firebase Auth custom claims on every new user.
 *
 * Custom claims shape:
 *   - subnation: "ireland" (default; user changes via onboarding)
 *   - role:      "student"  (default; user changes via onboarding)
 *   - cycle:     "leaving_cycle" (default)
 *
 * Per the All Things Agentic Hackathon Fortified Enterprise Fleet sub-criterion
 * "Agent Identity (zero-trust access control)" + the Firebase 3-layer security
 * model (Roger Martinez's July 2026 Firebase blog).
 */

import type { AuthEvent } from "firebase-functions/v2/auth";
import { initializeApp, getApps } from "firebase-admin/app";
import { getAuth } from "firebase-admin/auth";
import { trace } from "@opentelemetry/api";

import { logStructured } from "./observability.js";

if (!getApps().length) initializeApp();

const tracer = trace.getTracer("gemini-hackathon-functions");

const DEFAULT_CLAIMS = {
  subnation: "ireland",
  role: "student",
  cycle: "leaving_cycle",
  onboarded: false,
};

export async function authOnCreate(event: AuthEvent): Promise<void> {
  await tracer.startActiveSpan("authOnCreate", async (span) => {
    try {
      const uid = event.data?.uid;
      const email = event.data?.email ?? "(unknown)";
      if (!uid) {
        span.setStatus({ code: 2, message: "no_uid_in_event" });
        return;
      }
      span.setAttribute("auth.uid", uid);
      span.setAttribute("auth.email", email);

      // Set the default custom claims (user changes via onboarding flow)
      await getAuth().setCustomUserClaims(uid, {
        ...DEFAULT_CLAIMS,
        email,
        sign_in_provider: event.data?.providerId ?? "anonymous",
      });

      // Also create the Firestore user doc
      const { getFirestore } = await import("firebase-admin/firestore");
      const db = getFirestore();
      await db.collection("users").doc(uid).set(
        {
          email,
          subnation: DEFAULT_CLAIMS.subnation,
          role: DEFAULT_CLAIMS.role,
          cycle: DEFAULT_CLAIMS.cycle,
          onboarded: false,
          created_at: new Date().toISOString(),
        },
        { merge: true },
      );

      logStructured("INFO", {
        event: "user_created",
        uid,
        email,
        claims: DEFAULT_CLAIMS,
      });
    } catch (err) {
      span.recordException(err as Error);
      logStructured("ERROR", { event: "user_create_failed", detail: String(err) });
      throw err;
    } finally {
      span.end();
    }
  });
}