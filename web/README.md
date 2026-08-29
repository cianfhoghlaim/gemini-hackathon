# gemini-hackathon — Web Frontend (Firebase + GCP-native)

> Submission for the **Google All Things Agentic Hackathon 2026** (Fortified Enterprise Fleet track).
> Built with **Firebase Auth + Firestore + Cloud Functions for Firebase (Gen2) + Firebase App Check + Firebase Performance Monitoring + Cloud Logging + Cloud Trace**.

## Quick start (local dev)

```bash
# 1. Copy the env template
cp .env.example .env
# Fill in: VITE_FIREBASE_PROJECT_ID, VITE_FIREBASE_API_KEY,
# VITE_RECAPTCHA_SITE_KEY (use the dev key 6LeIxAcT...OnRk),
# VITE_UNSLOTH_BASE_URL + API_KEY (for the Tier 2 model)

# 2. Install deps (this repo uses bun.lock)
bun install

# 3. Start the Firebase Local Emulator Suite (Auth + Firestore + Functions + Storage)
cd ..
firebase emulators:start --only auth,firestore,functions,storage,hosting

# 4. Start the Python backend (the BAML/Gemini proxy)
mise run backend

# 5. In a separate terminal, start the web dev server
cd web
bun run dev
# → http://localhost:3000
```

## Quick start (production deploy)

```bash
# 1. Set the env vars in the deploy machine (CI / Cloud Shell / workstation)
export GCP_PROJECT=gemini-hackathon-prod
export GCP_REGION=europe-west1
# Get your Stitch API key + project ID at https://stitch.withgoogle.com
export STITCH_API_KEY=
export STITCH_PROJECT_ID=<your-numeric-id>

# 2. Initialize the Firebase project (one-time)
cd /Users/cianmacandeisigh/dev/gemini_hackathon
firebase login
firebase use --add gemini-hackathon-prod

# 3. Enable the required APIs (Auth + Firestore + Functions + Hosting + Storage + App Check)
gcloud services enable \
  firebase.googleapis.com \
  firestore.googleapis.com \
  cloudfunctions.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  --project=$GCP_PROJECT

# 4. Build the web bundle + the Functions
cd web && bun run build && cd ..
cd functions && npm install && npm run build && cd ..

# 5. Deploy everything in one go
firebase deploy --only firestore:rules,firestore:indexes,functions,hosting,storage
# → hosting URL: https://gemini-hackathon-prod.web.app (mandatory Cloud infrastructure per Hackathon rule §6)
```

## Architecture (post-Firebase-migration)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Browser (React 19 + Vite 7 + Tailwind 4) │
│ │
│ - Firebase Auth (Google Sign-In primary + Anonymous fallback) │
│ - Firebase App Check (reCAPTCHA v3 attestation) — Layer 3 of the 3-layer model │
│ - Firebase Performance Monitoring (auto-instrumented) │
│ - Firestore realtime subscriptions (replaces Convex `useQuery`/`useMutation`) │
│ - TanStack Router client-side (no SSR; SPA mode) │
│ - The Marimo embed (iframe to cianfhoghlaim/gemini-hackathon/blob/main/...) │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTPS + Bearer ID token
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Cloud Functions for Firebase (Gen2) — europe-west1 │
│ │
│ /api/themes     → themesApi      (reads 12 official-guidelines JSONs + design_tokens) │
│ /api/copilotkit → chatStream      (Vertex AI Gemini 3.5 Flash + SSE streaming + 5 ADK tools) │
│ /api/duckdb     → duckdbAsset    (302 → signed Cloud Storage URL for .parquet) │
│ /api/stitch     → stitchSync     (pushes DESIGN.md to Google Stitch REST API) │
│ onCreate trigger → authOnCreate   (sets Firebase Auth custom claims + creates users/{uid}) │
│ │
│ Observability (auto-wired in functions/src/observability.ts): │
│ - Cloud Logging via @google-cloud/logging │
│ - Cloud Trace via OpenTelemetry + @google-cloud/opentelemetry-cloud-monitoring │
│ - Cloud Monitoring metrics auto-emitted │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              │ Service account with least-privilege IAM — Layer 2 of the 3-layer model
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Firestore (Native mode) + Cloud Storage │
│ │
│ Collections: users, sessions, palettes, subjects, policies, learningOutcomes, │
│ equivalencies, changeEvents, assetProvenance, assessmentEvents, outcomeMastery, │
│ certificates, syllabusExtractions, perTopicAssets, certificateComparisons, design_tokens │
│ │
│ Security Rules (firestore.rules) — Layer 1 of the 3-layer model: │
│ - read-public: palettes, subjects, policies, learningOutcomes, equivalencies, ... │
│ - read-owner-only: users/{uid}, sessions, assessmentEvents, outcomeMastery, certificates │
│ - write-admin-only: all │
│ - custom claims check: request.auth.token.subnation / role / cycle │
└─────────────────────────────────────────────────────────────────────────────┘
```

## The 3-layer security model (per Roger Martinez's July 2026 Firebase blog)

| Layer | Mechanism | File | What it enforces |
|---|---|---|---|
| **Layer 1** | **Firestore Security Rules** | [`firestore.rules`](../../firestore.rules) | Per-collection access control via `request.auth.uid` + custom claims check; helper functions (`isSignedIn`, `isAdmin`, `isOwner`, `hasCustomClaim`) |
| **Layer 2** | **Cloud Functions service accounts** with least-privilege IAM | `functions/src/auth_oncreate.ts` (sets custom claims) + IAM roles `roles/datastore.user`, `roles/cloudfunctions.invoker` | The server-side execution context; no default Compute Engine SA |
| **Layer 3** | **Firebase App Check** (reCAPTCHA v3 for web) | `web/src/lib/firebase.ts` `initializeAppCheck()` | Client request attestation; blocks automated abuse before any Firestore call |

## The 7 Fleet primitives (FEF mandatory primitives)

Per the All Things Agentic Hackathon **Fortified Enterprise Fleet** track sub-criteria, the 7 Fleet primitives map to Firebase + GCP-native services:

| Fleet primitive | Firebase / GCP implementation |
|---|---|
| **FleetGateway** | `functions/src/themes.ts` + `functions/src/index.ts` — the single canonical entrypoint |
| **FleetIdentity** | Firebase Auth + custom claims (`functions/src/auth_oncreate.ts`) + Security Rules (`firestore.rules`) |
| **FleetModelArmor** | Firebase App Check (`web/src/lib/firebase.ts`) + input sanitisation in `functions/src/chat.ts` |
| **FleetMemory** | Firestore `users/{uid}` + `assessmentEvents` + `outcomeMastery` (cross-session persistent context) |
| **FleetObservability** | Cloud Logging + Cloud Trace + Firebase Performance + Cloud Monitoring (auto-wired in `functions/src/observability.ts`) |
| **FleetMcpCurriculum** | The 8 NCCA LC subject BAML contracts (`baml_extracts_education/subjects/*.baml`) exposed as ADK tools + Firestore docs |
| **FleetAguiBridge** | The AGUI 13-event protocol streamed via SSE from `functions/src/chat.ts` |

## Observability (the FEF Agent Observability sub-criterion)

| Surface | Tool | Where |
|---|---|---|
| **Server logs** | Cloud Logging (structured JSON entries) | `functions/src/observability.ts:logStructured()` |
| **Server traces** | Cloud Trace (OpenTelemetry exporter) | `functions/src/observability.ts:tracer` |
| **Server metrics** | Cloud Monitoring (auto-emitted by the Functions runtime) | Functions Framework default |
| **Browser perf** | Firebase Performance Monitoring (auto-instrumented) | `web/index.html` + `web/src/lib/firebase.ts:firebasePerformance()` |
| **Browser logs** | `web/src/lib/observability-browser.ts:logStructured()` → batched `/api/log` → Cloud Logging | browser-side client observability |
| **LLM traces** | Langfuse Cloud (the existing server-side LLM trace layer, kept for LLM eval) | unchanged from prior phases |

## The 17-notebook collection (unchanged)

The [`../notebooks/converted/`](../../notebooks/converted/) directory has the 17 Jupyter notebooks that walk through every pipeline + the Google ADK / AGUI / CopilotKit internals. See `notebooks/converted/README.md` for the full index.

## Files (post-migration)

```
web/
├── package.json                    (Firebase + react-router-dom + Vite; Convex + CopilotKit + DuckDB-WASM + Babylon + deck.gl DROPPED)
├── vite.config.ts                  (plain React plugin; no TanStack Start SSR proxy)
├── index.html                      (Firebase Performance compat loader)
├── .env.example                    (VITE_FIREBASE_* env vars + the recaptcha site key + Functions URL)
├── firebase.json                   (root — Firebase project config + emulator ports)
├── firestore.rules                 (Layer 1 of the 3-layer security model)
├── firestore.indexes.json          (the 8 compound indexes for perTopicAssets / certificateComparisons / etc.)
├── storage.rules                   (Cloud Storage rules for the certificate / DuckDB / asset buckets)
├── src/
│   ├── components/
│   │   ├── auth/
│   │   │   ├── AuthGate.tsx        (NEW — Firebase Auth + App Check wrapper; the 3-layer model layer 3)
│   │   │   └── SignInButton.tsx    (NEW — Google Sign-In + Anonymous fallback)
│   │   ├── session/SessionContext.tsx (MIGRATED — Firestore-backed session + custom claims)
│   │   └── themes/SourcePaletteProvider.tsx (unchanged)
│   ├── lib/
│   │   ├── firebase.ts             (NEW — Firebase init + 5 singletons: Auth, Firestore, Functions, Storage, App Check, Performance)
│   │   ├── auth.ts                 (NEW — signInWithGoogle / signInAnonymouslyFallback / getIdToken / authedFetch)
│   │   ├── firestore.ts            (NEW — realtime subscribeDoc/subscribeCollection + fetch/write/patch helpers)
│   │   └── observability-browser.ts (NEW — logStructured + flushLogs to /api/log → Cloud Logging)
│   ├── routes/
│   │   ├── __root.tsx              (MIGRATED — drop ConvexProvider + CopilotKit; add AuthGate)
│   │   ├── index.tsx               (unchanged — uses useSession)
│   │   ├── subjects.tsx, agents.tsx, ...   (unchanged — still call /api/copilotkit which now delegates to Cloud Functions)
│   │   └── api/
│   │       ├── themes.ts           (MIGRATED — delegates to Cloud Functions `themesHandler`)
│   │       ├── copilotkit.ts       (MIGRATED — delegates to Cloud Functions `chatHandler`)
│   │       └── duckdb.ts           (MIGRATED — delegates to Cloud Functions `duckdbHandler`)
└── ...
functions/                         (NEW — Cloud Functions for Firebase Gen2)
├── package.json                    (firebase-functions v6 + firebase-admin v13 + OpenTelemetry)
├── tsconfig.json
└── src/
    ├── index.ts                    (4 HTTPS endpoints + onCreate trigger)
    ├── themes.ts                   (/api/themes — reads 12 JSONs + Firestore design_tokens)
    ├── chat.ts                     (/api/copilotkit/** — streams Gemini 3.5 Flash via SSE + 5 ADK tools)
    ├── duckdb.ts                   (/api/duckdb — 302 to signed Cloud Storage URL for the .parquet export)
    ├── stitch.ts                   (/api/stitch — pushes DESIGN.md to Google Stitch REST API)
    ├── auth_oncreate.ts            (Cloud Function trigger — sets custom claims on every new user)
    └── observability.ts            (Cloud Logging + Cloud Trace + OpenTelemetry wiring)
```

## The Hackathon bonus math

Per rules §8, the Firebase migration directly unlocks:

| Bonus opportunity | Points | What unlocks it |
|---|---|---|
| Firebase agent skills installation (12 SKILL.md bundles) | +0.2 (FEF Design sub-criterion) | `npx skills add firebase/agent-skills --agent=antigravity` |
| Antigravity SDK usage in the build | +0.2 (mandatory rule §6: "Google Agent Framework") | `antigravity` CLI + the `firebase` agent skills |
| Gemma 4 (Unsloth Studio) as Tier 2 | +0.2 (additional Google AI model) | already wired |
| Imagen 4 in asset comparison | +0.2 (additional Google AI model) | already wired |
| 3-layer security (Rules + IAM + App Check) | +0.2 (FEF security sub-criterion) | `firestore.rules` + `auth_oncreate.ts` + App Check |
| 5 HF Spaces | +0.4 | already drafted |
| Blog post + social | +0.4 | already drafted |
| **Max bonus** | **+1.6** (capped at +0.6 per rules §8) | net +0.6 |

## The 6 USER ACTIONS still pending

(These can't be automated — they require the user's GCP project + auth + deploy pipeline.)

1. **Cloud Run deploy** — `./cloud/scripts/deploy-cloud-run.sh` for the Python backend (still uses Cloud Run, separate from Firebase)
2. **Firebase deploy** — `firebase deploy --only hosting,functions,firestore:rules,storage` for the web + backend
3. **Run the comparison end-to-end** — `uv run python -m gemini_hackathon.syllabus.comparison` + `uv run python -m gemini_hackathon.certificate.compare_backends`
4. **Validate the 17 notebooks** — `uv run --with jupyter jupyter nbconvert --to notebook --execute --inplace notebooks/converted/*.ipynb`
5. **Publish 5 HF Spaces** — `huggingface-cli upload cianfhoghlaim/gemini_hackathon_<stage>`
6. **Publish blog + social** — copy `docs/BLOG_POST.md` to Medium/dev.to + copy `docs/SOCIAL_MEDIA.md` to X/LinkedIn

## References

- [Firebase Auth docs](https://firebase.google.com/docs/auth)
- [Cloud Logging](https://docs.cloud.google.com/logging/docs)
- [Cloud Functions for Firebase Gen2](https://cloud.google.com/functions) (= Cloud Run functions)
- [Stackdriver Agent Observability](https://docs.cloud.google.com/stackdriver/docs/observability/agent-observability)
- [Firestore + React SSR](https://firebase.blog/posts/2026/06/firestore-serialization-react) (the Jeff Huleatt blog)
- [3-layer security model](https://firebase.blog/posts/2026/07/three-layer-security) (the Roger Martinez blog)
- [Firebase AI](https://firebase.google.com/docs/ai) (Vertex AI in Firebase + the GenAI SDK)
- [Firebase agent skills](https://firebase.google.com/docs/ai-assistance/agent-skills) (12 SKILL.md bundles)
- [Firebase Hosting](https://firebase.google.com/solutions/portal/?keywords=hostwebapp)
- [Antigravity](https://antigravity.google/use-cases/frontend) (Google's agentic-coding IDE/SDK)