"""tools.py — the SourcingCopilot's ADK 2 tools.

Three tool functions that the copilot's three sub-agents (Status / Exclude /
Deploy) call. Each tool reads or writes the same Firestore collections
that the sourcing pipeline writes (so the copilot sees exactly what the
workshop host sees). All tools are best-effort and return None / empty
list on failure so the offline in-memory fallback path works end-to-end.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def _event_code() -> str:
    return os.environ.get("JOURNEY_EVENT_CODE", "biep-demo")


def _content_artefact_path() -> str:
    return f"journeys/{_event_code()}/content_artefacts"


def _sourcing_runs_path() -> str:
    return f"journeys/{_event_code()}/sourcing_runs"


def get_status() -> dict[str, Any]:
    """The same 9-row status table as `gemini_hackathon/journey/sourcing/pipeline.py:step_status`.

    The copilot's `StatusAgent` calls this on every conversation turn.
    """
    from gemini_hackathon.journey.sourcing.pipeline import step_status

    return step_status(project_id=os.environ.get("GOOGLE_CLOUD_PROJECT", "") or None)


def list_artefacts(
    excluded: bool | None = None,
    document_type: str | None = None,
    subject_slug: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """List content_artefacts (the copilot's "what docs do we have?" view).

    Args:
        excluded: None = all, True = only excluded, False = only not-excluded.
        document_type: optional filter (e.g. "syllabus_pdf")
        subject_slug: optional filter (e.g. "mathematics")
        limit: max results to return (default 20 — the copilot's context
              budget is the binding constraint, not Firestore's perf).
    """
    from gemini_hackathon.journey.sourcing.fs import get_firestore

    fs = get_firestore()
    col = fs.collection(_content_artefact_path())
    out: list[dict[str, Any]] = []
    for snap in col.stream():
        data = snap.to_dict() or {}
        data["sha256"] = data.get("sha256") or snap.id
        if excluded is not None and bool(data.get("excluded", False)) is not excluded:
            continue
        if document_type and data.get("document_type") != document_type:
            continue
        if subject_slug and data.get("subject_slug") != subject_slug:
            continue
        out.append(data)
        if len(out) >= limit:
            break
    return out


def mark_excluded(sha256: str, reason: str = "out_of_scope") -> dict[str, Any]:
    """Mark one content_artefact as excluded.

    Validates the reason against the closed vocabulary
    (gemini_hackathon/journey/sourcing/schemas.py:EXCLUDED_REASONS).
    Returns the updated doc (so the copilot's REPL can echo it back).

    Always shows the next 10 candidates after a successful exclusion (the
    copilot's REPL is the workshop host's exclusion tool).
    """
    from gemini_hackathon.journey.sourcing.fs import get_firestore
    from gemini_hackathon.journey.sourcing.pipeline import step_filtered

    if reason not in _LEGAL_REASONS:
        return {
            "ok": False,
            "error": f"invalid excluded_reason {reason!r}; must be one of {_LEGAL_REASONS}",
        }

    step_filtered(
        excluded_sha256s=[sha256],
        excluded_reasons={sha256: reason},
        project_id=os.environ.get("GOOGLE_CLOUD_PROJECT", "") or None,
    )

    get_firestore()
    candidates = [a for a in list_artefacts(excluded=False, limit=10) if a.get("sha256") != sha256]
    return {
        "ok": True,
        "excluded": sha256,
        "reason": reason,
        "next_candidates": [
            {
                "sha256": c.get("sha256"),
                "subject_slug": c.get("subject_slug"),
                "jurisdiction": c.get("jurisdiction"),
                "document_type": c.get("document_type"),
            }
            for c in candidates
        ],
    }


_LEGAL_REASONS = ("out_of_scope", "corrupted", "duplicate", "superseded", "language_unsupported")


def list_cloud_run_services() -> list[dict[str, Any]]:
    """The Cloud Run services the workshop host has deployed.

    In offline mode, returns the canonical 5-service stub (the editorial
    studio + the 4 Gradio studios + the journey service). In GCP mode,
    shells out to `gcloud run services list --format=json`.
    """
    if not os.environ.get("GOOGLE_CLOUD_PROJECT"):
        return [
            {
                "name": "gemini-hackathon-journey",
                "region": "europe-west1",
                "last_deployed": "<offline stub>",
            },
            {
                "name": "gemini-hackathon-editorial-studio",
                "region": "europe-west1",
                "last_deployed": "<offline stub>",
            },
            {
                "name": "gemini-hackathon-an-scrudu",
                "region": "europe-west1",
                "last_deployed": "<offline stub>",
            },
            {
                "name": "gemini-hackathon-anam-education",
                "region": "europe-west1",
                "last_deployed": "<offline stub>",
            },
            {
                "name": "gemini-hackathon-mission-control",
                "region": "europe-west1",
                "last_deployed": "<offline stub>",
            },
        ]
    try:
        import json
        import subprocess

        project_id = os.environ["GOOGLE_CLOUD_PROJECT"]
        out = subprocess.check_output(
            ["gcloud", "run", "services", "list", f"--project={project_id}", "--format=json"],
            text=True,
        )
        return json.loads(out) if out.strip() else []
    except Exception as exc:
        logger.warning("list_cloud_run_services: gcloud failed (%s)", exc)
        return []


def list_scheduled_jobs() -> list[dict[str, Any]]:
    """The Cloud Scheduler jobs that trigger the sourcing pipeline.

    In offline mode, returns the canonical stub. In GCP mode, shells out
    to `gcloud scheduler jobs list`.
    """
    if not os.environ.get("GOOGLE_CLOUD_PROJECT"):
        return [
            {"name": "biep-nightly-ingest", "schedule": "0 2 * * *", "last_run": "<offline stub>"},
        ]
    try:
        import json
        import subprocess

        project_id = os.environ["GOOGLE_CLOUD_PROJECT"]
        out = subprocess.check_output(
            ["gcloud", "scheduler", "jobs", "list", f"--project={project_id}", "--format=json"],
            text=True,
        )
        return json.loads(out) if out.strip() else []
    except Exception as exc:
        logger.warning("list_scheduled_jobs: gcloud failed (%s)", exc)
        return []


def trigger_step(step: str) -> dict[str, Any]:
    """Trigger one sourcing-pipeline step (delegates to the CLI's main()).

    Used by the copilot's `DeployAgent` when the host says "run the sourced
    step now" — the same code path the CLI uses.
    """
    from gemini_hackathon.journey.sourcing.pipeline import main as pipeline_main

    rc = pipeline_main(
        ["--step", step, "--project-id", os.environ.get("GOOGLE_CLOUD_PROJECT", "") or ""]
    )
    return {
        "ok": rc == 0,
        "returncode": rc,
        "step": step,
    }


def recommend_next_steps() -> dict[str, Any]:
    """The copilot's "what should I deploy next?" view.

    Reads the current status + the deployment state, then recommends the
    single next step that moves the workshop closest to "ready for Level 1".
    This is what the workshop host clicks in the REPL.
    """
    status = get_status()
    rec: dict[str, Any] = {"recommendation": None, "reasons": []}
    if status.get("sourced_ok", 0) == 0:
        rec["recommendation"] = "sourced"
        rec["reasons"].append(
            "No docs sourced yet — run `python -m gemini_hackathon.journey.sourcing.pipeline --step=sourced`"
        )
    elif (status.get("normalised") or 0) < (status.get("sourced_ok") or 0):
        rec["recommendation"] = "normalised"
        rec["reasons"].append(f"{status['normalised']}/{status['sourced_ok']} docs normalised")
    elif (status.get("baml_extracted") or 0) < (status.get("normalised") or 0):
        rec["recommendation"] = "extract-baml"
        rec["reasons"].append(
            f"{status['baml_extracted']}/{status['normalised']} docs BAML-extracted"
        )
    else:
        rec["recommendation"] = "journey:level_1"
        rec["reasons"].append(
            "All docs sourced + normalised + BAML-extracted — ready for the Journey orchestrator"
        )
    rec["status"] = status
    return rec


__all__ = [
    "get_status",
    "list_artefacts",
    "list_cloud_run_services",
    "list_scheduled_jobs",
    "mark_excluded",
    "recommend_next_steps",
    "trigger_step",
]
