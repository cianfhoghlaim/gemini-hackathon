"""gemini_hackathon.agents — the autonomous ADK agent fleet.

The Google Agent Development Kit (ADK) is the mandatory Google framework
per the All Things Agentic Hackathon rules. The agents in this package
expose the 5 idea-agent capabilities (Marking Grader, Adaptive Tutor,
Equivalency Generator, Curriculum Change Sensor, plus the new
FindSimilarResources cross-national resource-discovery agent) as
`LlmAgent` instances with tools.

The agents compose the active session's (subnation, role, subjects,
cycle, palette, safeguarding policy) into every system prompt, so the
responses feel like they came from the user's home awarding body.

Re-exports the 7 Fleet primitives (Phase 1.8 lift from cianfhoghlaim/packages/fleet/)
+ the StitchClient (Phase 3.3 lift from stitch-skills MCP server).

Reference:
    cianfhoghlaim/agents/adk/   - the upstream ADK agent registry
    cianfhoghlaim/agents/fleet/ - the original "Fleet primitives" pattern
    https://google.github.io/adk-docs
"""

from .stitch_client import StitchClient, default_stitch_client

__all__ = [
    "StitchClient",
    "default_stitch_client",
]
