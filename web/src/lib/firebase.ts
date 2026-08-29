/**
 * gemini-hackathon web Firebase init.
 *
 * Single source of truth for the Firebase app, App Check, and the
 * 4 backend instances (Auth + Firestore + Functions + Storage + Performance).
 *
 * Per the All Things Agentic Hackathon Fortified Enterprise Fleet sub-criterion
 * "Agent Identity (zero-trust access control)" — every Firebase call goes
 * through this single instance.
 */

import { initializeApp, getApps, type FirebaseApp } from "firebase/app";
import { getAuth, type Auth } from "firebase/auth";
import { getFirestore, type Firestore } from "firebase/firestore";
import { getFunctions, type Functions } from "firebase/functions";
import { getStorage, type FirebaseStorage } from "firebase/storage";
import { getPerformance, type FirebasePerformance } from "firebase/performance";
import { initializeAppCheck, ReCaptchaV3Provider, type AppCheck } from "firebase/app-check";

const firebaseConfig = {
  apiKey:            import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain:        import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId:         import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket:     import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId:             import.meta.env.VITE_FIREBASE_APP_ID,
};

const REGION = "europe-west1";

let _app: FirebaseApp | null = null;
let _auth: Auth | null = null;
let _db: Firestore | null = null;
let _functions: Functions | null = null;
let _storage: FirebaseStorage | null = null;
let _performance: FirebasePerformance | null = null;
let _appCheck: AppCheck | null = null;

function ensureApp(): FirebaseApp {
  if (_app) return _app;
  _app = getApps().length ? getApps()[0]! : initializeApp(firebaseConfig);
  return _app;
}

export function firebaseApp(): FirebaseApp {
  return ensureApp();
}

export function firebaseAuth(): Auth {
  if (!_auth) _auth = getAuth(ensureApp());
  return _auth;
}

export function firebaseDb(): Firestore {
  if (!_db) _db = getFirestore(ensureApp());
  return _db;
}

export function firebaseFunctions(): Functions {
  if (!_functions) _functions = getFunctions(ensureApp(), REGION);
  return _functions;
}

export function firebaseStorage(): FirebaseStorage {
  if (!_storage) _storage = getStorage(ensureApp());
  return _storage;
}

export function firebasePerformance(): FirebasePerformance {
  if (typeof window === "undefined") {
    // SSR safety
    throw new Error("Firebase Performance is browser-only");
  }
  if (!_performance) _performance = getPerformance(ensureApp());
  return _performance;
}

export function firebaseAppCheck(): AppCheck {
  if (!_appCheck) {
    _appCheck = initializeAppCheck(ensureApp(), {
      provider: new ReCaptchaV3Provider(
        import.meta.env.VITE_RECAPTCHA_SITE_KEY ?? "6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXdiaZOnRk",
      ),
      isTokenAutoRefreshEnabled: true,
    });
  }
  return _appCheck;
}

/** The Firebase Functions region (Cloud Run functions are pinned to europe-west1). */
export const FUNCTIONS_REGION = REGION;

/** The Firestore collection names (one source of truth). */
export const COLLECTIONS = {
  USERS: "users",
  SESSIONS: "sessions",
  PALETTES: "palettes",
  SUBJECTS: "subjects",
  POLICIES: "policies",
  LEARNING_OUTCOMES: "learningOutcomes",
  EQUIVALENCIES: "equivalencies",
  CHANGE_EVENTS: "changeEvents",
  ASSET_PROVENANCE: "assetProvenance",
  ASSESSMENT_EVENTS: "assessmentEvents",
  OUTCOME_MASTERY: "outcomeMastery",
  CERTIFICATES: "certificates",
  SYLLABUS_EXTRACTIONS: "syllabusExtractions",
  PER_TOPIC_ASSETS: "perTopicAssets",
  CERTIFICATE_COMPARISONS: "certificateComparisons",
  DESIGN_TOKENS: "design_tokens",
} as const;