"""gemini_hackathon.agents.fleet — the 7 Fleet primitives.

Wholesale port of the Cianfhoghlaim agent fleet orchestration
primitives (per the ``wholesale-copy-convention``), adapted to the
gemini_hackathon context (the 3-tier model policy + the 8 BI
jurisdictions + the 4 idea agents).

The 7 Fleet primitives exposed here:

1. :mod:`gemini_hackathon.agents.fleet.fleet_gateway` — single
   entrypoint that routes a user request to the right agent
   based on the LiteLLM routing keywords.
2. :mod:`gemini_hackathon.agents.fleet.fleet_identity` —
   authentication + identity context (BetterAuth / JWT /
   anonymous fallback).
3. :mod:`gemini_hackathon.agents.fleet.fleet_model_armor` —
   input/output validation, prompt-injection defense, jailbreak
   detection, PII redaction.
4. :mod:`gemini_hackathon.agents.fleet.fleet_observability` —
   Langfuse + MLflow + structlog tracing.
5. :mod:`gemini_hackathon.agents.fleet.fleet_memory` — Letta
   long-term memory layer (with an in-memory fallback for tests).
6. :mod:`gemini_hackathon.agents.fleet.fleet_agui` — AG-UI
   protocol bridge (16-event stream to CopilotKit).
7. :mod:`gemini_hackathon.agents.fleet.fleet_mcp_curriculum` —
   MCP curriculum server (the lookup tool exposed to all 4 idea
   agents).
"""

from __future__ import annotations

from .fleet_agui import AGUIEvent, AGUIEventType, FleetAGUIBridge
from .fleet_gateway import (
    AGENT_NAMES,
    AGENT_PERMISSIONS,
    AgentInvocation,
    AgentResponse,
    FleetGateway,
    KEYWORD_TO_AGENT,
    agent_for_query,
    is_administrative_query,
    list_known_keywords,
)
from .fleet_identity import (
    AuthenticationError,
    AuthorisationError,
    FleetIdentity,
    IdentityContext,
    IdentityError,
    PERMISSIONS,
    ROLES,
    make_token,
    roles_with_permission,
)
from .fleet_mcp_curriculum import (
    ActiveSource,
    EquivalentTopicHit,
    MCPCurriculumServer,
    TopicLookup,
)
from .fleet_memory import (
    FleetMemory,
    MemoryEntry,
    MemoryHit,
    MemoryNotFoundError,
    MemoryQuery,
    namespace_for_agent,
)
from .fleet_model_armor import (
    ArmorError,
    CompletionTooLongError,
    INJECTION_PATTERNS,
    JAILBREAK_PATTERNS,
    JailbreakError,
    ModelArmor,
    PII_PATTERNS,
    PromptInjectionError,
    PromptTooLongError,
    SanitisedCompletion,
    SanitisedPrompt,
)
from .fleet_observability import (
    InvocationRecord,
    Observability,
    TraceContext,
    configure_structlog,
    hash_prompt,
)

__all__ = [
    # Gateway
    "AGENT_NAMES",
    "AGENT_PERMISSIONS",
    "AgentInvocation",
    "AgentResponse",
    "FleetGateway",
    "KEYWORD_TO_AGENT",
    "agent_for_query",
    "is_administrative_query",
    "list_known_keywords",
    # Identity
    "AuthenticationError",
    "AuthorisationError",
    "FleetIdentity",
    "IdentityContext",
    "IdentityError",
    "PERMISSIONS",
    "ROLES",
    "make_token",
    "roles_with_permission",
    # ModelArmor
    "ArmorError",
    "CompletionTooLongError",
    "INJECTION_PATTERNS",
    "JAILBREAK_PATTERNS",
    "JailbreakError",
    "ModelArmor",
    "PII_PATTERNS",
    "PromptInjectionError",
    "PromptTooLongError",
    "SanitisedCompletion",
    "SanitisedPrompt",
    # Observability
    "InvocationRecord",
    "Observability",
    "TraceContext",
    "configure_structlog",
    "hash_prompt",
    # Memory
    "FleetMemory",
    "MemoryEntry",
    "MemoryHit",
    "MemoryNotFoundError",
    "MemoryQuery",
    "namespace_for_agent",
    # AG-UI bridge
    "AGUIEvent",
    "AGUIEventType",
    "FleetAGUIBridge",
    # MCP curriculum
    "ActiveSource",
    "EquivalentTopicHit",
    "MCPCurriculumServer",
    "TopicLookup",
]
