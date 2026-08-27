# Tasks

## Status: closed

## Workstream: W4b

- [x] **Why**: /dev/tuatha has the canonical 14-subject wiring + the per-subject ADK agent scaffolds that gemini_hackathon needs for its stage coordinators.
- [x] **Scope**: Lifted routing.py → gemini_hackathon/agents/registry.py (the SUBJECT_WIRING_REGISTRY + ROUTING_KEYWORDS + SubjectAgentWiring dataclass). Lifted agents/adk/celtic_tutor.py → gemini_hackathon/agents/spe...
- [x] **Acceptance**: 14 subjects registered; routing keywords classify 10/10 typical learner questions correctly; build_specialist_agent raises ValueError on invalid input.