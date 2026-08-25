# 4-min Demo Video Script — All Things Agentic Hackathon

**Target length:** 4:00 (only the first 4 min are evaluated)
**Required proof:** backend running on Google Cloud (Cloud Run dashboard, Vertex AI logs, or live `.run` URL)
**Required narrative:** problem → value prop → demo → proof

---

## 0:00–0:30 — Problem (30s)

> The British Isles is an archipelago of **8 distinct education systems**.
> Five live awarding bodies (NCCA, AQA/OCR/Pearson, SQA, WJEC, CCEA) plus
> three future expansion (Jersey, Guernsey, Isle of Man). A student in
> Ireland, a parent in Wales, a teacher in Northern Ireland — they all
> need a different view of the world.
>
> Today, the typical school either:
> - hires a developer to build a per-jurisdiction dashboard (months, $50K+), or
> - sends students to generic quiz apps that ignore their curriculum
>   entirely.
>
> [SCREEN: a 30-second montage of NCCA / AQA / SQA / WJEC / CCEA / States
> of Jersey logos — all 8 in a grid]

## 0:30–1:00 — Value proposition (30s)

> We built **one product** that adapts to each: theming is the user
> identity, not a colour picker. **Three audiences** (student / parent /
> teacher) × **8 subnations** × **7 idea-agent capabilities** — from a
> single codebase.
>
> The same chunking + indexing pipeline turns 148 official source PDFs
> into a single RAG corpus. The chat agent is a **Google ADK** agent
> with 5 tools. The backend runs on **Google Cloud Run**. Every session
> is durable, multi-device, account-bound.
>
> [SCREEN: the archipelagic unity ribbon on the home page — all 8
> flags in one line, the active subnation's flag bold]

## 1:00–2:30 — Demo (90s)

### 1:00–1:20 — Student flow (20s)

> [SCREEN: home page as Ireland, student, Leaving Cert cycle]
>
> I'm a student in Ireland studying Leaving Cert Maths. The home page
> shows me my subjects. I click Mathematics.
>
> [SCREEN: subjects page filtered to Ireland + JC + LC, with NCCA's
> 12 subjects]
>
> I ask the agent: "find me English AQA mechanics papers that cover
> vectors."
>
> [SCREEN: /find-resources page, after the agent responds with 4
> cross-national matches: England AQA, NI CCEA, Scotland SQA, Wales WJEC]

### 1:20–1:40 — Switch to parent flow (20s)

> [SCREEN: same browser, same session, role switched to parent]
>
> I'm a parent in Wales now. The home page changes — I see what my child
> is studying, the safeguarding policy in effect, and the resources
> that might help.
>
> [SCREEN: Wales home page with parent quick actions, WJEC safeguarding]

### 1:40–2:00 — Switch to teacher flow (20s)

> [SCREEN: same session, role switched to teacher, subnation = NI]
>
> I'm a teacher in Northern Ireland. I can mark a paper against the
> CCEA marking scheme, see the curriculum changes this week, and
> plan a lesson that uses resources from any of the 5 active
> subnations.
>
> [SCREEN: NI home, teacher quick actions, mark_answer tool being invoked]

### 2:00–2:30 — The /archipelago view (30s)

> [SCREEN: /archipelago page showing all 8 subnations side-by-side]
>
> The /archipelago view shows the same platform across all 8
> subnations. The 5 live ones are clickable to switch home. The 3
> future expansion pack ones (Jersey, Guernsey, Isle of Man) are
> rendered as locked "coming soon" cards — the productisation
> framing, not a TODO.

## 2:30–3:30 — Architecture (60s)

> [SCREEN: the Mermaid diagram from docs/ARCHITECTURE.md]
>
> The frontend is TanStack Start with a per-tab session context. The
> chat agent is a Google ADK `LlmAgent` with 5 tools. The Python
> backend on Cloud Run enforces the 2-tier model policy: Tier 1 is
> Gemini 3.5 Flash via Vertex AI; Tier 2 is Gemma 4 26B-A4B via
> Unsloth Studio. The chunking + indexing pipeline is the canonical
> 4-path ensemble: PaddleOCR for handwritten / forms, qwen3-vl-8b for
> English OCR, gemma-4-26b-a4b for Irish / gaelic, and a stub fallback
> for offline dev.
>
> [SCREEN: scroll through the diagram, highlighting the 4 pillars
> of the Fortified Enterprise Fleet track]
>
> This is exactly the Fortified Enterprise Fleet track's 4 pillars:
> Agent Registry, Agent Runtime, Memory Bank, Agent Identity — all
> implemented in one codebase. Plus Agent Gateway, Model Armor, and
> Agent Observability as the 5th / 6th / 7th primitives.

## 3:30–4:00 — Proof of execution (30s)

> [SCREEN: GCP Console — Cloud Run dashboard showing the running service]
>
> Visible proof the backend is running on Google Cloud — the Cloud
> Run dashboard shows the service is up, the Vertex AI logs show the
> last 100 invocations, and the live `.run` URL is in the address bar.
>
> [SCREEN: langfuse.cianfhoghlaim.ie or the live local Langfuse]
>
> The same trace shows up in Langfuse — the canonical observability
> stack. Every LLM call has `tier`, `model`, `backend`, `latency_ms`.
> Every agent invocation has its own span.
>
> [SCREEN: /find-resources page with 4 cross-national matches]
>
> Three audiences. Eight nations. Two default. One platform. Built on
> Gemini 3.5 + Gemma 4 + the Google ADK. One platform for the
> British Isles.

---

## Production checklist

Before recording:

- [ ] GCP project with billing account
- [ ] `$150 in Google Cloud credits` (form by Aug 28 12:00 PM PT)
- [ ] Cloud Run service deployed with the Python backend
- [ ] BetterAuth + PocketID wired (or mock + clear comment)
- [ ] Vertex AI logs visible in the demo
- [ ] Langfuse traces captured for the demo session
- [ ] Live `.run` URL works

## Technical recording notes

- Use a screen recorder (OBS or Loom). Audio via a USB headset.
- Do NOT edit the demo — judges want to see the live thing working
  (see the FAQ: "the proof of action does the video show an
  unedited, live execution").
- Capture the GCP Console at the start of recording so it's fresh
  when you start the demo.
- Save the .run URL in a sticky note for the end-of-video shot.

## 30-second teaser (for social media)

> One platform. Eight subnations. Three audiences. Built on Gemini 3.5
> + Gemma 4 + the Google ADK. A student in Ireland studying Maths
> finds English AQA mechanics papers that help. A parent in Wales
> sees the safeguarding policy that matters. A teacher in Northern
> Ireland marks a paper against the CCEA scheme. One platform for
> the British Isles.
