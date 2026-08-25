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

# ─────────────────────────────────────────────────────────────────────
# TIER 1 lift shim (per the 2026-08-25-lift-fleet-to-t1-v1 change).
# When the parent cianfhoghlaim-fleet package is installed, this
# shim REPLACES the wholesale-copied symbols with the lifted TIER 1
# implementation. The wholesale imports above remain in effect when
# the parent package is NOT installed (e.g. for offline testing).
# Mirrors the model-registry shim pattern
# (2026-08-25-lift-model-registry-to-t1-v1).
# ─────────────────────────────────────────────────────────────────────
try:
    from cianfhoghlaim.fleet import (  # noqa: F401
        AGUIEvent as _TIER1_AGUIEvent,
        AGUIEventType as _TIER1_AGUIEventType,
        FleetAGUIBridge as _TIER1_FleetAGUIBridge,
        FleetGateway as _TIER1_FleetGateway,
        FleetIdentity as _TIER1_FleetIdentity,
        FleetMemory as _TIER1_FleetMemory,
        ModelArmor as _TIER1_ModelArmor,
        Observability as _TIER1_Observability,
        MCPCurriculumServer as _TIER1_MCPCurriculumServer,
    )
    # Replace the wholesale-copied symbols with the lifted TIER 1
    AGUIEvent = _TIER1_AGUIEvent
    AGUIEventType = _TIER1_AGUIEventType
    FleetAGUIBridge = _TIER1_FleetAGUIBridge
    FleetGateway = _TIER1_FleetGateway
    FleetIdentity = _TIER1_FleetIdentity
    FleetMemory = _TIER1_FleetMemory
    ModelArmor = _TIER1_ModelArmor
    Observability = _TIER1_Observability
    MCPCurriculumServer = _TIER1_MCPCurriculumServer
    _FLEET_TIER_1_LIFT_ACTIVE = True
except ImportError:
    # Parent package not installed; the wholesale copies above
    # remain in effect.
    _FLEET_TIER_1_LIFT_ACTIVE = False

# ─────────────────────────────────────────────────────────────────────
# TIER 1 lift shim (per the 2026-08-26-lift-observability-to-t1-v1).
# Mirrors the 4 prior TIER 1 lift shims.
# ─────────────────────────────────────────────────────────────────────
try:
    from cianfhoghlaim.observability import (  # noqa: F401
        Observability as _TIER1_OBS_Observability,
        TraceContext as _TIER1_OBS_TraceContext,
        InvocationRecord as _TIER1_OBS_InvocationRecord,
        configure_structlog as _TIER1_OBS_configure_structlog,
        hash_prompt as _TIER1_OBS_hash_prompt,
    )
    # The wholesale observability symbols are REPLACED with the lifted
    # TIER 1 symbols. The wholesale observability.py at
    # gemini_hackathon/gemini_hackathon/observability.py is the
    # standalone fallback.
    Observability = _TIER1_OBS_Observability
    TraceContext = _TIER1_OBS_TraceContext
    InvocationRecord = _TIER1_OBS_InvocationRecord
    configure_structlog = _TIER1_OBS_configure_structlog
    hash_prompt = _TIER1_OBS_hash_prompt
    _OBSERVABILITY_TIER_1_LIFT_ACTIVE = True
except ImportError:
    _OBSERVABILITY_TIER_1_LIFT_ACTIVE = False

# ─────────────────────────────────────────────────────────────────────
# TIER 1 lift shim (per the 2026-08-25-lift-agui-bridge-to-t1-v1).
# Overrides the wholesale FleetAGUIBridge with the lifted
# cianfhoghlaim.agui_bridge.FleetAGUIBridge when the parent
# agui-bridge package is installed.
# Note: this is a SECOND try/except nested under the fleet try/except
# so the lift is layered: fleet first, then agui-bridge.
# ─────────────────────────────────────────────────────────────────────
try:
    from cianfhoghlaim.agui_bridge import (  # noqa: F401
        AGUIEvent as _TIER1_AGUI_AGUIEvent,
        AGUIEventType as _TIER1_AGUI_AGUIEventType,
        FleetAGUIBridge as _TIER1_AGUI_FleetAGUIBridge,
    )
    AGUIEvent = _TIER1_AGUI_AGUIEvent
    AGUIEventType = _TIER1_AGUI_AGUIEventType
    FleetAGUIBridge = _TIER1_AGUI_FleetAGUIBridge
    _AGUI_BRIDGE_TIER_1_LIFT_ACTIVE = True
except ImportError:
    _AGUI_BRIDGE_TIER_1_LIFT_ACTIVE = False

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
    # TIER 1 lift markers (exposed for downstream consumers + tests)
    "_FLEET_TIER_1_LIFT_ACTIVE",
    "_AGUI_BRIDGE_TIER_1_LIFT_ACTIVE",
    "_OBSERVABILITY_TIER_1_LIFT_ACTIVE",
]
