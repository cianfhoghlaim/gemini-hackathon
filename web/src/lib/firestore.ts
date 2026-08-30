/**
 * Firestore helpers — the realtime DB layer that replaces Convex.
 *
 * The 3 actually-used Convex tables (`palettes`, `subjects`, `policies`)
 * get realtime subscriptions via `onSnapshot`. The wider 10 tables
 * (`learningOutcomes`, `equivalencies`, `changeEvents`, etc.) are queried
 * via `getDocs` once + cached in TanStack Query for 5 minutes.
 *
 * Per the All Things Agentic Hackathon Fortified Enterprise Fleet sub-criterion
 * "Agent Memory Bank (for persistent, secure cross-session context)" — the
 * `assessmentEvents` + `outcomeMastery` collections are user-scoped via
 * Firestore Security Rules (only the owner can read/write).
 */

import {
  collection,
  doc,
  onSnapshot,
  query,
  where,
  orderBy,
  limit,
  getDocs,
  getDoc,
  setDoc,
  updateDoc,
  deleteDoc,
  type DocumentData,
  type QueryConstraint,
  type FirestoreError,
  type Unsubscribe,
} from "firebase/firestore";
import { firebaseDb, COLLECTIONS } from "./firebase";

/** Generic type-safe Firestore document subscription. */
export function subscribeDoc<T extends DocumentData>(
  collectionName: string,
  docId: string,
  onValue: (value: T | null) => void,
  onError?: (err: FirestoreError) => void,
): Unsubscribe {
  return onSnapshot(
    doc(firebaseDb(), COLLECTIONS[collectionName as keyof typeof COLLECTIONS] ?? collectionName, docId),
    (snap) => onValue(snap.exists() ? ({ id: snap.id, ...snap.data() } as unknown as T) : null),
    onError,
  );
}

/** Generic type-safe Firestore collection subscription. */
export function subscribeCollection<T extends DocumentData>(
  collectionName: string,
  onValue: (values: T[]) => void,
  constraints: QueryConstraint[] = [],
  onError?: (err: FirestoreError) => void,
): Unsubscribe {
  const ref = collection(firebaseDb(), collectionName);
  return onSnapshot(
    query(ref, ...constraints),
    (snap) => onValue(snap.docs.map((d) => ({ id: d.id, ...d.data() }) as unknown as T)),
    onError,
  );
}

/** One-shot fetch of a document. */
export async function fetchDoc<T extends DocumentData>(
  collectionName: string,
  docId: string,
): Promise<T | null> {
  const snap = await getDoc(doc(firebaseDb(), collectionName, docId));
  return snap.exists() ? ({ id: snap.id, ...snap.data() } as unknown as T) : null;
}

/** One-shot fetch of a collection (no realtime). */
export async function fetchCollection<T extends DocumentData>(
  collectionName: string,
  constraints: QueryConstraint[] = [],
): Promise<T[]> {
  const ref = collection(firebaseDb(), collectionName);
  const snap = await getDocs(query(ref, ...constraints));
  return snap.docs.map((d) => ({ id: d.id, ...d.data() }) as unknown as T);
}

/** Write (upsert) a document. */
export async function writeDoc<T extends DocumentData>(
  collectionName: string,
  docId: string,
  value: T,
): Promise<void> {
  await setDoc(doc(firebaseDb(), collectionName, docId), value as DocumentData);
}

/** Update an existing document. */
export async function patchDoc<T extends DocumentData>(
  collectionName: string,
  docId: string,
  value: Partial<T>,
): Promise<void> {
  await updateDoc(doc(firebaseDb(), collectionName, docId), value as DocumentData);
}

/** Delete a document. */
export async function removeDoc(collectionName: string, docId: string): Promise<void> {
  await deleteDoc(doc(firebaseDb(), collectionName, docId));
}

// ============================================================================
// Common query helpers (the 13 collection names from the prior Convex schema)
// ============================================================================

export const firestoreQueries = {
  // Palettes (replaces Convex `themes.ts`)
  subscribePalettes: (onValue: (palettes: unknown[]) => void): Unsubscribe =>
    subscribeCollection("palettes", onValue, [orderBy("sourceKey")]),

  // Subjects (replaces Convex `subjects.ts`)
  subscribeSubjects: (onValue: (subjects: unknown[]) => void): Unsubscribe =>
    subscribeCollection("subjects", onValue, [orderBy("sourceKey")]),

  // Policies (replaces Convex `policies.ts`)
  subscribePolicies: (onValue: (policies: unknown[]) => void): Unsubscribe =>
    subscribeCollection("policies", onValue, [orderBy("sourceKey")]),

  // Phase 5 — syllabus extractions comparison (32 rows)
  subscribeSyllabusExtractions: (
    subject: string,
    onValue: (rows: unknown[]) => void,
  ): Unsubscribe =>
    subscribeCollection("syllabusExtractions", onValue, [
      where("subject", "==", subject),
      orderBy("judgeScore", "desc"),
    ]),

  // Phase 6 — per-topic assets comparison (280 rows)
  subscribePerTopicAssets: (
    subject: string,
    topic: string,
    onValue: (rows: unknown[]) => void,
  ): Unsubscribe =>
    subscribeCollection("perTopicAssets", onValue, [
      where("subject", "==", subject),
      where("topic", "==", topic),
      orderBy("judgeScore", "desc"),
    ]),

  // Phase 6 — certificate comparison (30 rows)
  subscribeCertificateComparisons: (
    subnation: string,
    stage: string,
    onValue: (rows: unknown[]) => void,
  ): Unsubscribe =>
    subscribeCollection("certificateComparisons", onValue, [
      where("subnation", "==", subnation),
      where("stage", "==", stage),
      orderBy("judgeScore", "desc"),
    ]),

  // Per-user assessment events (the formative ledger)
  subscribeAssessmentEvents: (userId: string, onValue: (rows: unknown[]) => void): Unsubscribe =>
    subscribeCollection("assessmentEvents", onValue, [
      where("userId", "==", userId),
      orderBy("capturedAt", "desc"),
      limit(100),
    ]),

  // Stitch-managed design tokens (the canonical source of truth)
  subscribeDesignTokens: (onValue: (rows: unknown[]) => void): Unsubscribe =>
    subscribeCollection("design_tokens", onValue, [limit(100)]),
};

export { where, orderBy, limit, query };