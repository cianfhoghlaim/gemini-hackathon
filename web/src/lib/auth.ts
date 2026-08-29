/**
 * Firebase Auth helpers — the canonical sign-in / sign-out / ID-token flow.
 *
 * Per the All Things Agentic Hackathon Fortified Enterprise Fleet sub-criterion
 * "Agent Identity (zero-trust access control)" — every chat request includes
 * the Firebase ID token in `Authorization: Bearer <idToken>`; the Cloud Function
 * verifies it via `firebase-admin/auth.verifyIdToken()`.
 */

import {
  GoogleAuthProvider,
  signInWithPopup,
  signInAnonymously,
  linkWithCredential,
  type User,
  type UserCredential,
} from "firebase/auth";
import { firebaseAuth } from "./firebase";
import { logStructured } from "./observability-browser";

const googleProvider = new GoogleAuthProvider();
googleProvider.setCustomParameters({
  prompt: "select_account",
  login_hint: "ciandfhoghlaim+gemini-hackathon@gmail.com",
});

/** Sign in with Google — the primary auth method. */
export async function signInWithGoogle(): Promise<UserCredential> {
  const result = await signInWithPopup(firebaseAuth(), googleProvider);
  logStructured("info", { event: "sign_in_google", uid: result.user.uid });
  return result;
}

/** Sign in anonymously — the fallback (parents/teachers without Google). */
export async function signInAnonymouslyFallback(): Promise<UserCredential> {
  const result = await signInAnonymously(firebaseAuth());
  logStructured("info", { event: "sign_in_anonymous", uid: result.user.uid });
  return result;
}

/**
 * Sign in with email link — for parents/teachers who don't use Google.
 * Falls back to anonymous if no provider is configured.
 */
export async function signInWithEmailLink(
  email: string,
  actionCodeSettings: { url: string },
): Promise<void> {
  // Lazy import — keeps the main bundle small
  const { sendSignInLinkToEmail } = await import("firebase/auth");
  await sendSignInLinkToEmail(firebaseAuth(), email, actionCodeSettings);
}

/** Link anonymous account to Google (so anonymous onboarding survives) */
export async function linkAnonymousToGoogle(): Promise<UserCredential> {
  const result = await linkWithCredential(firebaseAuth().currentUser!, googleProvider);
  logStructured("info", { event: "anonymous_linked_google", uid: result.user.uid });
  return result;
}

/** Sign out — clears session + ID token + Firestore realtime listeners. */
export async function signOut(): Promise<void> {
  const uid = firebaseAuth().currentUser?.uid;
  await firebaseAuth().signOut();
  logStructured("info", { event: "sign_out", uid });
}

/** Get the current Firebase ID token (force-refreshed if expired). */
export async function getIdToken(forceRefresh = false): Promise<string | null> {
  const user = firebaseAuth().currentUser;
  if (!user) return null;
  return user.getIdToken(forceRefresh);
}

/**
 * Fetch the Firebase ID token via Cloud Functions (the canonical
 * server-side session verifier pattern).
 */
export async function authedFetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  const token = await getIdToken();
  const headers = new Headers(init.headers ?? {});
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return fetch(input, { ...init, headers });
}