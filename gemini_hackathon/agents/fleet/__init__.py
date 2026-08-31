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
    KEYWORD_TO_AGENT,
    AgentInvocation,
    AgentResponse,
    FleetGateway,
    agent_for_query,
    is_administrative_query,
    list_known_keywords,
)
from .fleet_identity import (
    PERMISSIONS,
    ROLES,
    AuthenticationError,
    AuthorisationError,
    FleetIdentity,
    IdentityContext,
    IdentityError,
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
    INJECTION_PATTERNS,
    JAILBREAK_PATTERNS,
    PII_PATTERNS,
    ArmorError,
    CompletionTooLongError,
    JailbreakError,
    ModelArmor,
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
    from cianfhoghlaim.fleet import (
        AGUIEvent as _TIER1_AGUIEvent,
    )
    from cianfhoghlaim.fleet import (
        AGUIEventType as _TIER1_AGUIEventType,
    )
    from cianfhoghlaim.fleet import (
        FleetAGUIBridge as _TIER1_FleetAGUIBridge,
    )
    from cianfhoghlaim.fleet import (
        FleetGateway as _TIER1_FleetGateway,
    )
    from cianfhoghlaim.fleet import (
        FleetIdentity as _TIER1_FleetIdentity,
    )
    from cianfhoghlaim.fleet import (
        FleetMemory as _TIER1_FleetMemory,
    )
    from cianfhoghlaim.fleet import (
        MCPCurriculumServer as _TIER1_MCPCurriculumServer,
    )
    from cianfhoghlaim.fleet import (
        ModelArmor as _TIER1_ModelArmor,
    )
    from cianfhoghlaim.fleet import (
        Observability as _TIER1_Observability,
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
    from cianfhoghlaim.observability import (
        InvocationRecord as _TIER1_OBS_InvocationRecord,
    )
    from cianfhoghlaim.observability import (
        Observability as _TIER1_OBS_Observability,
    )
    from cianfhoghlaim.observability import (
        TraceContext as _TIER1_OBS_TraceContext,
    )
    from cianfhoghlaim.observability import (
        configure_structlog as _TIER1_OBS_configure_structlog,
    )
    from cianfhoghlaim.observability import (
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
    from cianfhoghlaim.agui_bridge import (
        AGUIEvent as _TIER1_AGUI_AGUIEvent,
    )
    from cianfhoghlaim.agui_bridge import (
        AGUIEventType as _TIER1_AGUI_AGUIEventType,
    )
    from cianfhoghlaim.agui_bridge import (
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
    "INJECTION_PATTERNS",
    "JAILBREAK_PATTERNS",
    "KEYWORD_TO_AGENT",
    "PERMISSIONS",
    "PII_PATTERNS",
    "ROLES",
    "_AGUI_BRIDGE_TIER_1_LIFT_ACTIVE",
    # TIER 1 lift markers (exposed for downstream consumers + tests)
    "_FLEET_TIER_1_LIFT_ACTIVE",
    "_OBSERVABILITY_TIER_1_LIFT_ACTIVE",
    # AG-UI bridge
    "AGUIEvent",
    "AGUIEventType",
    # MCP curriculum
    "ActiveSource",
    "AgentInvocation",
    "AgentResponse",
    # ModelArmor
    "ArmorError",
    # Identity
    "AuthenticationError",
    "AuthorisationError",
    "CompletionTooLongError",
    "EquivalentTopicHit",
    "FleetAGUIBridge",
    "FleetGateway",
    "FleetIdentity",
    # Memory
    "FleetMemory",
    "IdentityContext",
    "IdentityError",
    # Observability
    "InvocationRecord",
    "JailbreakError",
    "MCPCurriculumServer",
    "MemoryEntry",
    "MemoryHit",
    "MemoryNotFoundError",
    "MemoryQuery",
    "ModelArmor",
    "Observability",
    "PromptInjectionError",
    "PromptTooLongError",
    "SanitisedCompletion",
    "SanitisedPrompt",
    "TopicLookup",
    "TraceContext",
    "agent_for_query",
    "configure_structlog",
    "hash_prompt",
    "is_administrative_query",
    "list_known_keywords",
    "make_token",
    "namespace_for_agent",
    "roles_with_permission",
]
