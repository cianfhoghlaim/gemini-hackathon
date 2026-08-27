"""gemini_hackathon.memory — the 5-layer memory pedagogy for the education system.

Lifted + adapted from `support-memory-lab/` (the rungs 1-6 + the
`MarkdownMemoryService` from monstertix). Rewritten for the British
Isles education system:

  Layer 1 — short-term: `tool_context.state` for the active session
            (already exists in `gemini_hackathon/session/`)
  Layer 2 — handoff: `LongRunningFunctionTool` for human-in-the-loop
            tasks (e.g. teacher escalates a marking question). Used
            by `pillar4_long_running.py` (W7).
  Layer 3 — long-term: `MarkdownMemoryService` (per-user markdown files
            or Letta / Vertex AI Memory Bank in production). The
            MarkdownMemoryService from `monstertix/agent/concert/memory.py`
            is lifted verbatim below.
  Layer 4 — artifacts: `save_artifact` in `before_agent_callback`
            (the student-uploaded work scans → per-session artifacts).
            Used by `gemini_hackathon_gradio/anam_education/`.
  Layer 5 — institutional memory: `find_known_issues(order, batch)` over
            the institutional FalkorDB graph (per W9). The graph is
            populated by the curriculum-change-sensor workflow.

This package provides Layer 3 (MarkdownMemoryService) — the rest are
implemented at the call sites in `agents/`, `gradio/`, etc.
"""

from __future__ import annotations
