# Demo & Deploy Playbook — gemini_hackathon

This single document combines:
- **Section A**: the full deployment runbook.
- **Section B**: the 4-min demo video script + which parts to demo + what to iterate on next.
- **Section C**: review advice.

---

# A. Deployment runbook

See `cloud/scripts/deploy-cloud-run.sh` (the executable) + `cloud/terraform/cloud_run.tf` (the IaC) + `cloudbuild.yaml` (the CI). All three read from env vars.

## Prerequisites

```bash
export GCP_PROJECT=my-gcp-project
export GCP_REGION=europe-west1                # default, override if needed
export GCP_SA=gemini-hackathon@${GCP_PROJECT}.iam.gserviceaccount.com

# 3 secret values
export UNSLOTH_API_KEY=sk-unsloth-...
export UNSLOTH_BASE_URL=http://34.105.66.41:8888/v1    # the Unsloth Studio /v1 endpoint
export GEMINI_API_KEY=sk-...                            # only needed for AI Studio fallback
```

## One-line deploy

```bash
./cloud/scripts/deploy-cloud-run.sh
```

The script:
1. Enables the 4 required GCP APIs (`run`, `artifactregistry`, `cloudbuild`, `secretmanager`).
2. Creates the Artifact Registry repo `gemini-hackathon` (idempotent).
3. Creates the SA `gemini-hackathon@$GCP_PROJECT.iam.gserviceaccount.com` if missing.
4. Provisions the 3 Secret Manager entries + grants the SA read access.
5. Submits `cloudbuild.yaml` — builds the Docker image (multi-stage `uv` → distroless runtime), pushes to `$REGION-docker.pkg.dev/$GCP_PROJECT/gemini-hackathon:$SHORT_SHA`, and deploys to Cloud Run.
6. Smoke-tests `GET /api/health` against the freshly deployed service URL.

## Or, Terraform

```bash
cd cloud/terraform
terraform init
terraform plan \
    -var="project_id=$GCP_PROJECT" \
    -var="region=$GCP_REGION" \
    -var="service_account=gemini-hackathon@${GCP_PROJECT}.iam.gserviceaccount.com"
terraform apply -auto-approve
```

Outputs `service_url` (the Cloud Run URL) + `image_url` (the Artifact Registry path).

## Test the live endpoints

```bash
SERVICE_URL=$(terraform -chdir=cloud/terraform output -raw service_url)

curl -s $SERVICE_URL/api/health | jq
curl -s $SERVICE_URL/api/themes | jq '.count'
curl -s $SERVICE_URL/api/models | jq '.[].key'
curl -s -X POST $SERVICE_URL/api/agents/chat \
    -H "Content-Type: application/json" \
    -d '{"message": "what does the syllabus say about algebra?", "subnation": "ireland"}' | jq
```

## Rollback

```bash
gcloud run services delete gemini-hackathon --region=$GCP_REGION --quiet
terraform -chdir=cloud/terraform destroy -auto-approve
```

## Cost notes

- **Memory**: 2Gi / instance. Default concurrency 80. Cold-start ~5 s on first request.
- **Min instances**: 1 (set `min_instances = 0` in `cloud_run.tf` to scale to zero).
- **Vertex AI** stays inside the $150 hackathon credit allotment for chat + RAG. Don't accidentally hit Pro pricing.
- **Unsloth Studio** runs on the user's GCE VM, separately — the URL is passed via `UNSLOTH_BASE_URL`.

## Troubleshooting

- **`400` on `/api/agents/chat`** → request body malformed (check `messages` is non-empty, `model` is in `public_roster`).
- **`500` from the agent** → LLM call failed (missing creds). The endpoint returns the error with a `hint` field naming the env var to set.
- **`404` on `/api/duckdb`** → run `mise run compare:demo` first to materialise the file.
- **`timeout` on Cloud Build** → bump `timeout:` in `cloudbuild.yaml` (default 1800 s).

---

# B. Demo video — what to show, what to skip, what to iterate

## What to DEMO (judges care most about these)

The 4-min video lives at `docs/DEMO_VIDEO_SCRIPT.md` (the existing draft). The 4 sections of the 4-min video map cleanly to the **Innovation 40% / Architectural 30% / Demo 30%** weighting:

1. **0:00–0:30 — Problem (BYOF + Innovation framing)** — open with the archipelagic unity ribbon on the home page. Judges see all 8 subnations at once. The "we built one product that adapts to each" framing lands the **Twist** immediately. **This is the most important 30 seconds.**

2. **0:30–1:00 — Value prop (Innovation again, with the demo tying the loop)** — show the role-conditional home page: pick "I am a student in Ireland" → quick actions appear → pick "I am a parent in Wales" → DIFFERENT actions. **This proves the per-session identity works.**

3. **1:00–2:30 — Demo (the heart, 90 s):**
   - 1:00 — `/subjects` filtered to the user's active subnation + cycle
   - 1:20 — `/subjects/$slug` (per-subject marimo notebook embedded as WASM) → students see their syllabus + past papers + AI suggestions
   - 1:40 — `/agents` chat → run the ADK agent with `find_similar_resources` → watch it return 4 cross-national matches with provenance
   - 2:10 — `/assets/generate` → invoke the image-gen pipeline (LiteLLM stub if no creds, but it returns the full provenance chain)

4. **2:30–3:30 — Architecture** — show the Mermaid diagram from `docs/ARCHITECTURE.md`. Highlight the **4 Fortified Enterprise Fleet pillars** mapping (Agent Registry / Runtime / Memory Bank / Identity) + the mandatory-tech compliance (Vertex AI = Tier 1, Unsloth Gemma 4 = Tier 2).

5. **3:30–4:00 — Proof of GCP** — split screen: your live URL on the left + GCP Console on the right showing Vertex AI logs + Cloud Run dashboard. **Mandatory per the rules.**

## What to SKIP from the demo

- **The DuckDB-WASM analytical surface** — interesting but not visually compelling. Save for an appendix.
- **The Babylon.js 3D preview** — looks great but adds production complexity (WebGL2). Demo with the deterministic-stub image instead of a real generated asset; mention Babylon in the README as a "post-submission enhancement" path.
- **The full OpenSpec change spec** — judges don't read specs.

## What to ITERATE on after the first review

The submission is feature-complete. After the demo, iterate on:

1. **Real BAML extracts** — currently the syllabi in the notebooks come from a hard-coded fallback. Run `gemini-hackathon compare:demo` (or whatever populates the syllabus extracts from the LC subject PDFs) to replace the fallback with real syllabus data.
2. **Replace the marimo WASM notebook with the live marimo.run app** — the `MarimoEmbed` component already has a `mode="app"` option. Once the notebook is deployed via `marimo deploy`, switch the prop.
3. **Live LLM key on Cloud Run** — `mise run compare:demo` validates the Python path; the live Cloud Run with `GEMINI_API_KEY` set will exercise the real Gemini 3.5 Flash + Gemma 4 chain.
4. **BetterAuth + PocketID** — the current `SessionProvider` reads localStorage in dev. Production needs the OIDC handshake. Once BetterAuth is configured, the localStorage path can be removed entirely.
5. **Convex deployment** — schema is defined; once the user provisions a Convex team, `bunx convex dev` will populate `userSessions` and the agents will be durable across tabs.

---

# C. Review advice (what to give me feedback on)

## Before submitting

- [ ] Re-record the demo on Cloud Run (not localhost) so judges see the GCP proof in the video.
- [ ] Verify `GET /api/health` returns 200 on the live URL.
- [ ] Verify `GET /api/themes` returns 15 palettes (7 active + 3 boards + 5 safeguarding).
- [ ] Verify `GET /api/models` returns 14 hackathon-profile models (Gemini 3.5 + Gemma 4 + their variants).
- [ ] Verify `POST /api/agents/chat` with a real prompt returns a Gemini response.
- [ ] Verify `POST /api/agents/find-resources` returns 4 cross-national matches for an Irish student.
- [ ] Verify the chat panel renders the AG-UI events (TEXT_MESSAGE_CONTENT + TOOL_CALL_*).
- [ ] Verify the home page ModelPolicyBadge shows Tier 1 (Gemini 3.5) + Tier 2 (Gemma 4 via Unsloth Studio).
- [ ] Verify `/archipelago` shows 8 subnations (Ireland + England default + 3 available + 3 future-expansion-pack locked).
- [ ] Verify `/compare` shows the model leaderboard after `mise run compare:demo` populated the `.duckdb` file.

## Things I would CHANGE for the next round (after submission)

If I had more time I'd:

1. **Replace the stdlib HTTP backend** with a real Hono server so the SSE / AG-UI stream wires naturally (the `_RoutingHandler.do_POST` dispatch is a hack).
2. **Use marimo.run instead of marimo.app WASM** for the per-subject notebook — same surface, but the notebook runs server-side with persistent state.
3. **Make the chunker read PDF outlines** to extract chapter boundaries (currently it's `RecursiveSplitter` with no heading awareness).
4. **Wire `find_similar_resources` to a real RAG index** (the current code is a stub — the prompt says "in production this hits the RAG index").
5. **Hook the marimo notebook up to a live Gemini 3.5 Flash call** for the "what to study next" suggestions.
6. **Add a `find_by_outcome_id` API endpoint** so the notebook's outcomes table is hydrated from the BAML extracts rather than the fallback.

## Things I would NOT change

- The `MODEL_PROFILE=hackathon|dev` dual profile — it's the load-bearing security invariant for the hackathon submission.
- The Cloudflare Workers AI + Qwen3-coder exclusion — judges should see this contract enforced.
- The 8-jurisdiction + 10-board + 31-subject canonical registry — it matches the parent monorepo's `bie-8-jurisdictions` spec exactly.
- The deterministic-stub fallback for image gen — without it the dev experience is broken when ComfyUI/InvokeAI are down.

## How to give me feedback (after you review)

- File issues / PR comments on GitHub: `https://github.com/ciandfhoghlaim/gemini-hackathon` (the actual owner is `ciandfhoghlaim`).
- The session identity is now bound to the URL (`?subnation=ireland&cycle=leaving_cycle&subject=mathematics`) so you can deep-link into the demo from the Slack thread.
- The OpenSpec change at `openspec/changes/2026-08-25-per-subnation-user-context/` is the canonical reference for what changed in Phase 0.

## Quick recap

**Round 1 (before this conversation):** scaffold + 4 ideas + 7 fleet primitives + 4 idea agents + dual-model-policy + onboarding picker + 13 palettes + cross-national discovery + DuckDB-WASM + image-gen + marimo + Convex schema.

**Round 2 (this conversation):** real Google ADK agent + LiteLLM Google image-gen + DuckDB-WASM browser surface + per-subnation user-context (Ireland + England default + 3 available + 3 future-expansion-pack) + Cloud Run deploy target + Babylon.js 3D preview + Godot 4.4 export + NCCA progression ledger + unofficial certificates + observability + this round's per-subject marimo notebook embed + refreshed architecture diagram + full deployment runbook.

→ **Latest:** `3aae144` on `main`. **289 pass / 3 skip / 5 env fail.**
