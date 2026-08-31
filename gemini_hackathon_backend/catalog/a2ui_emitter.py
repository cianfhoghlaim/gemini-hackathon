"""gemini_hackathon_backend/catalog/a2ui_emitter.py — A2UI v0.9 surface emitter.

The helper module the NCCA agent's tools call to produce AG-UI `Raw` events
that carry A2UI v0.9 surface operations. The frontend's
`@copilotkit/a2ui-renderer` decodes the Raw events through its
`a2ui_operations` activity payload and streams the JSONL → React.

Per the A2UI v0.9 spec (https://a2ui.org/specification/v0_9-a2ui/) each
surface is described by 3 JSONL messages — a `createSurface` declaring the
catalogId + surfaceId, an `updateComponents` declaring the component tree,
and an optional `updateDataModel` that binds data values to the component
props via JSON-Pointer paths.

The function signatures are the canonical contract Lane B owns; the agent
tools import them and append their output to
`tool_context.state["a2ui_raw_events"]`. The session-end helper
`_flush_a2ui_surfaces(tool_context)` reads that buffer and yields the
events in the order they were recorded.
"""
from __future__ import annotations

from typing import Any

# The catalogId MUST match `web/src/a2ui/catalog.tsx:createCatalog(..., {catalogId: ...})`
# — the a2ui-renderer matches incoming catalogId strings against this value
# to confirm the client supports the components the server is emitting.
DEFAULT_CATALOG_ID = "https://gemini-hackathon.cianfhoghlaim.ie/a2ui/catalogs/ncca-v1.json"


# Module-level registry of every surface emitted by this process. Used by
# the agent's debug logger + by tests that want to assert "the agent emitted
# at least one surface this turn". Append-only — never reset, so it
# doubles as a session-scoped log.
EMITTED_SURFACES: list[str] = []


def make_a2ui_envelope(
    surface_id: str,
    components: list[dict],
    data: dict | None = None,
    *,
    catalog_id: str = DEFAULT_CATALOG_ID,
) -> dict[str, Any]:
    """Build a single A2UI v0.9 envelope as a list of 3 (or 2) operations.

    The envelope is a dict with a single `operations` key, matching the
    shape `web/node_modules/@copilotkit/react-core/dist/copilotkit-*.mjs:
    A2UISurfaceContentSchema` expects (`a2ui_operations: z.array(z.any())`).

    Each operation follows the v0.9 spec:
      - createSurface  { surfaceId, catalogId }
      - updateComponents { surfaceId, components: [...] }
      - updateDataModel  { surfaceId, path, value }   (when `data` is set)

    Args:
        surface_id: The stable surface identifier (e.g. "ncca-overview").
        components: A list of component definitions (each is a dict with
            at minimum `id` + `component` + the props for that component).
        data: Optional data-model root (`{"pdfs": [...]}` or similar). When
            provided, an `updateDataModel` operation is appended that
            binds the data to the surface's JSON-Pointer root (`/`).
        catalog_id: Override the catalogId; defaults to NCCA v1.

    Returns:
        A dict `{"operations": [createSurface, updateComponents, ...]}`.
    """
    ops: list[dict[str, Any]] = [
        {"createSurface": {"surfaceId": surface_id, "catalogId": catalog_id}},
        {"updateComponents": {"surfaceId": surface_id, "components": components}},
    ]
    if data is not None:
        ops.append({"updateDataModel": {"surfaceId": surface_id, "path": "/", "value": data}})

    if surface_id not in EMITTED_SURFACES:
        EMITTED_SURFACES.append(surface_id)
    return {"operations": ops}


def wrap_a2ui_in_raw_event(surface_id: str, components: list[dict], data: dict | None = None) -> dict[str, Any]:
    """Wrap an A2UI envelope in the AG-UI `Raw` event shape for the CopilotKit runtime.

    The AG-UI protocol (per CopilotKit's a2ui middleware) ships A2UI
    operations inside a `Raw` event so the client can route them to the
    a2ui-renderer without colliding with built-in event types.

    Args:
        surface_id: The stable surface identifier.
        components: The component tree (see `make_a2ui_envelope`).
        data: Optional data-model root.

    Returns:
        A dict shaped `{type: "RAW", ...}` — the AG-UI transport envelope.
    """
    envelope = make_a2ui_envelope(surface_id, components, data)
    return {
        "type": "RAW",
        "source": "ncca_panel",
        # The a2ui middleware on the CopilotKit side looks for an
        # `a2ui_operations` key (sibling of `RAW` payload) — we surface
        # the operations list alongside the Raw event for the runtime's
        # convenience.
        "raw": envelope,
        "a2ui_operations": envelope["operations"],
    }


def flush_a2ui_surfaces(tool_context) -> list[dict[str, Any]]:
    """Read the accumulated A2UI Raw events from `tool_context.state` and clear the buffer.

    The session-end helper the NCCA agent calls after a turn completes. It
    pulls every event that `cite_pdf` / `list_ncca_pdfs` accumulated in
    `tool_context.state["a2ui_raw_events"]` and returns them as a single
    list (the runtime streams them in order).

    Args:
        tool_context: The ADK `ToolContext` injected by the agent runner.

    Returns:
        A list of AG-UI `Raw` events (each one wraps a single A2UI surface).
        Returns `[]` when no surfaces were emitted during the turn.
    """
    state = getattr(tool_context, "state", None)
    if state is None:
        return []
    raw_events = list(state.get("a2ui_raw_events", []) or [])
    # Clear so the next turn starts with a fresh buffer.
    state["a2ui_raw_events"] = []
    return raw_events


def record_a2ui_raw_event(tool_context, raw_event: dict[str, Any]) -> None:
    """Append a single AG-UI `Raw` event to the tool_context buffer.

    The `cite_pdf` / `list_ncca_pdfs` tools call this after building their
    surface so the session-end `flush_a2ui_surfaces` helper can ship them
    all at once.

    Args:
        tool_context: The ADK `ToolContext` injected by the agent runner.
        raw_event: The dict produced by `wrap_a2ui_in_raw_event`.
    """
    state = getattr(tool_context, "state", None)
    if state is None:
        return
    buffer = state.get("a2ui_raw_events")
    if buffer is None:
        buffer = []
        state["a2ui_raw_events"] = buffer
    buffer.append(raw_event)


__all__ = [
    "DEFAULT_CATALOG_ID",
    "EMITTED_SURFACES",
    "flush_a2ui_surfaces",
    "make_a2ui_envelope",
    "record_a2ui_raw_event",
    "wrap_a2ui_in_raw_event",
]