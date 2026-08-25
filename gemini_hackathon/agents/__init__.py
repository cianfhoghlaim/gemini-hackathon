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

Reference:
    cianfhoghlaim/agents/adk/   - the upstream ADK agent registry
    cianfhoghlaim/agents/fleet/ - the original "Fleet primitives" pattern
    https://google.github.io/adk-docs
"""
