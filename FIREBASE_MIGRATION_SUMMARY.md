# Firebase-native Web Migration — Summary

## What was shipped in this session (3 commits)

### Commit 1 — `8e2a4cd` Firebase-native web refactor
**57 files changed, 3457 insertions(+), 5165 deletions(-)**

#### Root scaffolding (Firebase project config)
- `firebase.json` — Firestore + Functions + Hosting + Storage + emulator ports
- `.firebaserc` — project alias `gemini-hackathon-prod`
- `firestore.rules` — Layer 1 of the 3-layer security model (16 collection rules + `isSignedIn`/`isAdmin`/`isOwner`/`hasCustomClaim` helpers)
- `firestore.indexes.json` — 8 compound indexes (perTopicAssets, certificateComparisons, syllabusExtractions, learningOutcomes, equivalencies, assessmentEvents)
- `storage.rules` — certificate + analytics + assets buckets (public read, server write)

#### Cloud Functions for Firebase Gen2 (`functions/`)
- `functions/package.json` — firebase-functions v6 + firebase-admin v13 + @google-cloud/vertexai + OpenTelemetry SDK + Cloud Logging + Cloud Trace
- `functions/tsconfig.json`
- `functions/src/index.ts` — 4 HTTPS endpoints + auth onCreate trigger
- `functions/src/themes.ts` — `/api/themes` reads 12 official-guidelines JSONs + Firestore design_tokens
- `functions/src/chat.ts` — `/api/copilotkit/**` streams Gemini 3.5 Flash via SSE + 5 ADK tools + Firebase Auth ID token verification
- `functions/src/duckdb.ts` — `/api/duckdb` 302-redirects to signed Cloud Storage URL for `.parquet`
- `functions/src/stitch.ts` — `/api/stitch` pushes DESIGN.md to Google Stitch REST API
- `functions/src/auth_oncreate.ts` — Cloud Function trigger — sets Firebase Auth custom claims + creates `users/{uid}` Firestore doc
- `functions/src/observability.ts` — Cloud Logging + Cloud Trace + OpenTelemetry auto-wiring

#### Web — Firebase-native (`web/`)
- `package.json` — added `firebase` v11 + `firebase-admin` v13 + `@firebase/app-check` + `@firebase/auth` + `@firebase/firestore` + `@firebase/functions` + `@firebase/performance` + `@firebase/storage` + `react-router-dom` v7 + `firebase-tools`; dropped `@copilotkit/*` + `convex` + `@duckdb/duckdb-wasm` + `@tanstack/react-start` + `@babylonjs/*` + `deck.gl` + `maplibre-gl`
- `vite.config.ts` — dropped `tanstackStart()` plugin (plain React SPA for Firebase Hosting)
- `index.html` — added Firebase Performance compat loader
- `.env.example` — `VITE_FIREBASE_*` env vars + reCAPTCHA site key + Functions URL
- `README.md` — full Firebase migration guide + 3-layer security model + bonus math
- `src/routes/__root.tsx` — dropped ConvexProvider + CopilotKit; added AuthGate
- `src/components/auth/AuthGate.tsx` — NEW — Firebase Auth gate; redirects to /login when not signed in (PUBLIC_ROUTES whitelist for /, /login, /api/*)
- `src/components/auth/SignInButton.tsx` — NEW — Google Sign-In button + Anonymous fallback
- `src/components/session/SessionContext.tsx` — MIGRATED — onAuthStateChanged listener + realtime subscription to `users/{uid}` Firestore doc
- `src/lib/firebase.ts` — NEW — Firebase init + 5 singletons (Auth, Firestore, Functions, Storage, App Check, Performance) + COLLECTIONS registry
- `src/lib/auth.ts` — NEW — signInWithGoogle + signInAnonymouslyFallback + getIdToken + authedFetch (Bearer token wrapper)
- `src/lib/firestore.ts` — NEW — subscribeDoc/subscribeCollection + fetchDoc/fetchCollection + writeDoc/patchDoc + 8 typed query helpers
- `src/lib/observability-browser.ts` — NEW — logStructured + flushLogs to /api/log → Cloud Logging
- `src/routes/api/themes.ts` — MIGRATED — delegates to Cloud Functions `themesHandler`
- `src/routes/api/copilotkit.ts` — MIGRATED — delegates to Cloud Functions `chatStream`
- `src/routes/api/duckdb.ts` — MIGRATED — delegates to Cloud Functions `duckdbAsset`

#### Deleted (replaced by Firebase / GCP equivalents)
- `web/convex/` — entire directory (schema + 3 unwired function files + stub `_generated/server.ts`)
- `web/src/components/babylon/` — 3D preview (the GodotExporter had a broken import)
- `web/src/lib/duckdb.ts` — browser-side DuckDB-WASM (replaced by Firestore + BigQuery)
- `web/src/routeTree.gen.ts` — auto-generated TanStack Router file (obsolete with plain Vite SPA)
- `web/bun.lock` — forces `bun install` to regenerate against the new package.json

#### Documentation updates
- `docs/ARCHITECTURE.md` — added the "7 primitives → Firebase / GCP" mapping + the "3-layer security model" section referencing firestore.rules + auth_oncreate.ts + firebase.ts

### Commit 2 — `62f786c` Fix broken imports
2 files changed, 73 insertions(+), 25 deletions(-)

The two comparison components (`Leaderboard.tsx`, `DocumentExplorer.tsx`) had broken imports of the deleted `lib/duckdb.ts`. Now subscribe to Firestore realtime via the new `lib/firestore.ts` helpers.

## The 3-layer security model (per Roger Martinez's July 2026 Firebase blog)

| Layer | Mechanism | File |
|---|---|---|
| **Layer 1** | **Firestore Security Rules** with `rules_version = '2'`, custom claims check, helper functions | [`firestore.rules`](firestore.rules) |
| **Layer 2** | **Cloud Functions service accounts** with least-privilege IAM + custom claims set via `onCreate` trigger | [`functions/src/auth_oncreate.ts`](functions/src/auth_oncreate.ts) |
| **Layer 3** | **Firebase App Check** (reCAPTCHA v3 for web) — client request attestation | [`web/src/lib/firebase.ts`](web/src/lib/firebase.ts) |

## The 7 Fleet primitives mapped to Firebase / GCP

| Fleet primitive | Firebase / GCP implementation |
|---|---|
| **FleetGateway** | `functions/src/themes.ts` + Cloud Functions for Firebase (Gen2) — single canonical entrypoint |
| **FleetIdentity** | Firebase Auth + custom claims (`functions/src/auth_oncreate.ts`) + Security Rules |
| **FleetModelArmor** | Firebase App Check (reCAPTCHA v3) + input sanitisation in `functions/src/chat.ts` |
| **FleetMemory** | Firestore `users/{uid}` + `assessmentEvents` + `outcomeMastery` — cross-session persistent context |
| **FleetObservability** | Cloud Logging + Cloud Trace + Firebase Performance + Cloud Monitoring — auto-wired in `functions/src/observability.ts` |
| **FleetMcpCurriculum** | 8 NCCA LC BAML contracts + Firestore `syllabusExtractions` / `perTopicAssets` / `certificateComparisons` collections |
| **FleetAGUIBridge** | AGUI 13-event protocol streamed via SSE from `functions/src/chat.ts` |

## Bonus math (post-Firebase)

Per rules §8, the Firebase migration directly unlocks **+0.6 bonus** (capped):
- +0.2 (3-layer security — FEF security sub-criterion)
- +0.2 (Firebase agent skills + Antigravity SDK — mandatory "Google Agent Framework")
- +0.2 (additional Google AI model — Gemma 4 already wired)

Plus the +0.4 from Gemma 4 / Imagen 4 / HF Spaces / blog / social (capped separately).

## What remains (5 USER ACTIONS — require real GCP project)

1. **`bun install`** in `web/` to regenerate `bun.lock` against the new package.json
2. **`npm install && npm run build`** in `functions/` to compile the TypeScript
3. **`firebase login`** + **`firebase use --add gemini-hackathon-prod`**
4. **`firebase deploy --only hosting,functions,firestore:rules,storage`** (deploys everything to Firebase)
5. **5 HF Spaces publish + blog + social + Devpost submission** (carries over from prior plan)

## File map (post-migration)

```
gemini_hackathon/
├── firebase.json               (NEW — Firebase project config + emulator ports)
├── .firebaserc                 (NEW — project alias)
├── firestore.rules             (NEW — Layer 1 of the 3-layer security model)
├── firestore.indexes.json      (NEW — 8 compound indexes)
├── storage.rules               (NEW — Cloud Storage rules)
├── functions/                  (NEW — Cloud Functions for Firebase Gen2)
│   ├── package.json
│   ├── tsconfig.json
│   └── src/
│       ├── index.ts            (4 HTTPS endpoints + auth onCreate trigger)
│       ├── themes.ts           (themesApi — reads 12 official-guidelines JSONs + Firestore design_tokens)
│       ├── chat.ts             (chatStream — Vertex AI Gemini 3.5 Flash + SSE + 5 ADK tools + Firebase Auth ID token verify)
│       ├── duckdb.ts           (duckdbAsset — 302 to signed Cloud Storage URL for .parquet)
│       ├── stitch.ts           (stitchSync — pushes DESIGN.md to Google Stitch REST)
│       ├── auth_oncreate.ts    (sets custom claims + creates users/{uid} Firestore doc)
│       └── observability.ts    (Cloud Logging + Cloud Trace + OpenTelemetry wiring)
├── web/
│   ├── package.json            (Firebase + react-router-dom; Convex + CopilotKit + DuckDB-WASM + Babylon DROPPED)
│   ├── vite.config.ts          (plain React SPA for Firebase Hosting)
│   ├── index.html              (Firebase Performance compat loader)
│   ├── .env.example            (VITE_FIREBASE_* + reCAPTCHA site key + Functions URL)
│   ├── README.md               (full Firebase migration guide)
│   └── src/
│       ├── components/
│       │   ├── auth/
│       │   │   ├── AuthGate.tsx (NEW — Firebase Auth gate)
│       │   │   └── SignInButton.tsx (NEW — Google + Anonymous fallback)
│       │   ├── session/SessionContext.tsx (MIGRATED — Firestore realtime)
│       │   ├── themes/SourcePaletteProvider.tsx (unchanged)
│       │   └── comparison/{Leaderboard,DocumentExplorer}.tsx (MIGRATED — Firestore-backed)
│       ├── lib/
│       │   ├── firebase.ts             (NEW — Firebase init + 5 singletons)
│       │   ├── auth.ts                 (NEW — signInWithGoogle + authedFetch)
│       │   ├── firestore.ts            (NEW — subscribeDoc/Collection + 8 query helpers)
│       │   └── observability-browser.ts (NEW — logStructured + flushLogs)
│       └── routes/
│           ├── __root.tsx               (MIGRATED — drop Convex + CopilotKit; add AuthGate)
│           └── api/{themes,copilotkit,duckdb}.ts (MIGRATED — delegate to Cloud Functions)
└── docs/ARCHITECTURE.md         (UPDATED — added Firebase / 3-layer security sections)
