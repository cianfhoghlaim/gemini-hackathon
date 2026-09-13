# Change: ADK + Gemini Deep Research Mirror (gemini_hackathon)

## Why

This is the gemini_hackathon-side mirror of the parent change
`2026-09-06-adk-gemini-deep-research-control-plane-v1` in
`cianfhoghlaim/openspec/changes/`. The gemini_hackathon repo is
the GCP-first sibling already on ADK 2 (`gemini_hackathon_backend/`).

The new `gemini_deep_research` tool integration adds the
Gemini Deep Research API as a `FunctionTool` exposed by the
Cloud Run ADK service, bringing the gemini_hackathon backend
into feature parity with the Firecrawl + Crawl4AI + Stagehand
+ Skyvern + Browserbase + Z.AI vision backends in the cianfhoghlaim
browser stack.

## What changes

- **New module `gemini_hackathon_backend/agents/gemini_deep_research.py`** —
  wraps the Gemini Deep Research API (`https://ai.google.dev/gemini-api/docs/deep-research`)
  via the `google-genai` SDK with the new `interactions` field.
- **Re-export**: added to `gemini_hackathon_backend/agents/__init__.py`.
- **AG-UI streaming**: the `stream_interactions` function yields
  per-step events that the Cloud Run ADK service can forward to
  CopilotKit consumers.
- **New Cloud Run Terraform module**: `cloud_run_deep_research.tf`
  (the 12th module) — optional discrete Cloud Run service for
  the Deep Research workload with Workload Identity Federation +
  Google Secret Manager mount.

## Out of scope

- The 11 existing Terraform modules are unchanged.
- Vertex AI Memory Bank configuration is unchanged.

## Dependencies

```markdown
## Dependencies

`Blocked by: cianfhoghlaim/openspec/changes/2026-09-06-adk-gemini-deep-research-control-plane-v1`

`Affected repos: gemini_hackathon`
```
