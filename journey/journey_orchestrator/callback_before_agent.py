"""callback_before_agent.py — the canonical ADK 2 `before_agent_callback`.

Per `adk2-tutorial/L0_first_agent/` + `docs/adk-examples/way-back-home/
level_1/agent/agent.py`'s `before_agent_callback` pattern: every time
the Journey orchestrator runs an agent (one of the 6 level agents),
ADK calls this function BEFORE the agent's instruction is templated.
Our job is to hydrate `ctx.state` with the per-participant Firestore
values so `{learner_id}` / `{subnation}` / `{subject}` resolve
inside the agent's `instruction="..."` template.

This is the single integration point between Firestore (per-learner state)
and the ADK 2 Workflow (per-event orchestration). If this callback
returns without setting a required key, the downstream agent's
template fails fast — a deliberate fail-loud.

Usage (called by the orchestrator's `Workflow`, not directly):

    workflow = JourneyWorkflow(
        before_agent_callback=hydrate_participant_state,
    )

Or wired into every level's `Agent` directly via the ADK 2 constructor:

    Agent(
        name="level_1_extraction",
        model="gemini-3.5-flash",
        instruction="...{subnation} {subject}...",
        before_agent_callback=hydrate_participant_state,
    )
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ParticipantState:
    """The per-participant state that `hydrate_participant_state` puts into
    `ctx.state`. Every level's agent template references these keys via
    `{learner_id}` / `{subnation}` / `{subject}` / `{event_code}`."""

    learner_id: str
    subnation: str
    subject: str
    event_code: str
    display_name: str = ""
    journey_event_code: str = ""


def _read_state_from_context(ctx: Any) -> dict[str, Any]:
    """Best-effort extraction of state from whatever ADK 2 `ctx` shape this version uses.

    ADK 2 has shipped multiple `CallbackContext` shapes across its
    pre-2.7 / 2.7 / 2.7+ series. We don't pin to a specific shape; we
    pull whichever of the canonical keys exist. If none do (the
    participant invoked the level's standalone `app.py` without going
    through the orchestrator), we fall back to env vars + a sensible
    default for `subnation`.
    """
    state = None
    for attr in ("state", "_state"):
        if hasattr(ctx, attr):
            try:
                state = getattr(ctx, attr)
                if state is not None:
                    break
            except Exception:
                pass
    if state is None and hasattr(ctx, "to_dict"):
        try:
            return dict(ctx.to_dict() or {})
        except Exception:
            pass
    return dict(state or {})


def _fetch_participant_doc(learner_id: str, event_code: str) -> dict[str, Any] | None:
    """Read the participant's Firestore doc (`journeys/{event_code}/participants/{uid}`).

    Returns None in offline mode (no GCP credentials) — the callback
    then returns a ParticipantState derived purely from env vars so the
    workshop still runs without a backend.
    """
    if not learner_id:
        return None
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    if not project_id:
        return None
    try:
        from google.cloud import firestore
    except ImportError:
        return None

    database = os.environ.get("JOURNEY_FIRESTORE_DATABASE", "(default)")
    client = firestore.Client(project=project_id, database=database)
    doc_ref = (
        client.collection("journeys")
        .document(event_code)
        .collection("participants")
        .document(learner_id)
    )
    snap = doc_ref.get()
    if not snap.exists:
        return None
    return snap.to_dict()


def hydrate_participant_state(ctx: Any) -> dict[str, Any]:
    """The canonical `before_agent_callback`.

    Reads the participant's Firestore doc (if available), falls back to env
    vars (offline mode), and ALWAYS returns the canonical `ParticipantState`
    fields as a flat dict that ADK 2 whitelists into `ctx.state`.

    Returns the dict it wrote — useful for tests + the orchestrator's
    observability layer (the dict is also logged via `gemini_hackathon.
    observability.trace_agent`).
    """
    raw_state = _read_state_from_context(ctx)

    # Three ways to discover the participant's identity, in priority order:
    learner_id = (
        raw_state.get("learner_id")
        or getattr(ctx, "user_id", None)
        or os.environ.get("JOURNEY_DEFAULT_LEARNER_ID", "")
    )
    event_code = (
        raw_state.get("event_code")
        or raw_state.get("journey_event_code")
        or os.environ.get("JOURNEY_EVENT_CODE", "biep-demo")
    )

    doc = _fetch_participant_doc(learner_id, event_code)

    if doc is not None:
        subnation = doc.get("subnation") or raw_state.get("subnation") or "ireland"
        subject = doc.get("active_subject") or raw_state.get("subject") or "mathematics"
        display_name = doc.get("display_name", "")
    else:
        subnation = raw_state.get("subnation") or os.environ.get(
            "JOURNEY_DEFAULT_SUBNATION", "ireland"
        )
        subject = raw_state.get("subject") or os.environ.get(
            "JOURNEY_DEFAULT_SUBJECT", "mathematics"
        )
        display_name = raw_state.get("display_name", "")

    # Whitelist the 4 keys every downstream level's `instruction="..."`
    # template references. Adding extras is fine; ADK 2's state template
    # is permissive about extra keys.
    hydrated = {
        "learner_id": learner_id,
        "subnation": subnation,
        "subject": subject,
        "event_code": event_code,
        "journey_event_code": event_code,  # alias for older templates
        "display_name": display_name,
    }

    # Persist into ctx.state (best-effort — different ADK 2 versions expose
    # this as `.state`, `._state`, or a method).
    for attr in ("state", "_state"):
        if hasattr(ctx, attr):
            try:
                target = getattr(ctx, attr)
                if target is None:
                    continue
                if hasattr(target, "update"):
                    target.update(hydrated)
                elif hasattr(target, "__setitem__"):
                    for k, v in hydrated.items():
                        target[k] = v
                break
            except Exception:
                logger.debug("ctx.%s not assignable on this ADK 2 version", attr)

    logger.debug(
        "hydrate_participant_state: learner_id=%s subnation=%s subject=%s event_code=%s",
        learner_id,
        subnation,
        subject,
        event_code,
    )
    return hydrated


__all__ = [
    "ParticipantState",
    "hydrate_participant_state",
]
