# Mirror: gemini_hackathon ADK + Gemini Deep Research

Per the parent openspec change
`2026-09-06-adk-gemini-deep-research-control-plane-v1`. Brings the
gemini_hackathon backend into feature parity with the parent's
browser-stack backends (Firecrawl + Crawl4AI + Stagehand + Skyvern
+ Browserbase + Z.AI vision).

## Requirements

### Requirement: Gemini Deep Research tool in Cloud Run ADK service
The `gemini_hackathon_backend/agents/` package SHALL expose a
`deep_research(query)` function that calls the Gemini Deep
Research API. The function SHALL be registered as an ADK
`FunctionTool` on the canonical `ncca_panel_agent`.

#### Scenario: Cloud Run ADK invokes deep_research
- **WHEN** the Cloud Run ADK service receives a request with `domain=research` AND `query.research_kind=deep`
- **THEN** `ncca_panel_agent` MUST call `deep_research(query)`
- **AND** MUST stream the response to AG-UI consumers

### Requirement: AG-UI streaming of interactions
The `stream_interactions(query)` async generator SHALL yield
per-step Deep Research events that the Cloud Run service can
forward as AG-UI `EVENT_TOOL_CALL_ARGS` events.

#### Scenario: Stream events
- **WHEN** a CopilotKit consumer subscribes to the SSE endpoint
- **THEN** the consumer MUST receive 1+ `EVENT_TOOL_CALL_ARGS` events
- **AND** MUST receive 1 final `EVENT_MESSAGES_SNAPSHOT` event with the synthesized report

### Requirement: Google Secret Manager mount for GOOGLE_API_KEY
The Cloud Run service SHALL mount the `GOOGLE_API_KEY` secret via
Google Secret Manager (not a hard-coded env var). The 12th
Terraform module `cloud_run_deep_research` SHALL orchestrate the
mount.

#### Scenario: Secret Manager mount
- **WHEN** the Cloud Run service starts
- **THEN** `GOOGLE_API_KEY` MUST be mounted via Secret Manager
- **AND** the secret MUST NOT appear in the public environment variables
