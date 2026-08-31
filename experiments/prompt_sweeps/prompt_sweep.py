"""experiments.prompt_sweeps — sweep runner for the per-subject BAML prompt overlays.

Phase 6 of the multi-stage plan (see AGENTS.md). Compares the
``field_level_f1`` accuracy of the 5 LC6 extractions with and without
the ``prompt_overlay`` parameter, per subject. The overlay is
intentionally ``None`` today (the default-prompt baseline); the
sweep harness exists so when data-informed overlays land (Phase 6
follow-up + Phase 3 PDF pipeline output), we can measure the lift.

Public API:
  ``SUBJECT_CLIENTS`` — canonical (subject_slug, baml_client) table
  ``build_prompt_overlay(subject_slug, behavior_version) -> str | None``
  ``sweep_one_subject(subject_slug, samples, invoker=...) -> SweepResult``
  ``sweep_all_subjects(samples, subjects=ALL_8, invoker=...) -> list[SweepResult]``
"""

from __future__ import annotations

import logging
import statistics
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

from experiments.model_comparison.metrics import field_level_f1
from experiments.model_comparison.runner import EvalSample

logger = logging.getLogger(__name__)


#: The 8 LC subjects per the project's spec.
ALL_8: tuple[str, ...] = (
    "mathematics",
    "english",
    "gaeilge",
    "chemistry",
    "biology",
    "physics",
    "geography",
    "computer_science",
)

#: Canonical subject → BAML client routing table (the Phase 6 deliverable).
SUBJECT_CLIENTS: dict[str, str] = {
    "mathematics": "BIEPV3ExtractMathematics",
    "english": "BIEPV3ExtractEnglish",
    "gaeilge": "BIEPV3ExtractGaeilge",
    "chemistry": "BIEPV3ExtractChemistry",
    "biology": "BIEPV3ExtractBiology",
    "physics": "BIEPV3ExtractPhysics",
    "geography": "BIEPV3ExtractGeography",
    "computer_science": "BIEPV3ExtractComputerScience",
}


def client_for(subject_slug: str) -> str:
    """Return the BAML client name for a subject slug."""
    return SUBJECT_CLIENTS.get(subject_slug, "BIEPV3Extract")


# ---------------------------------------------------------------------------
# Sweep data classes
# ---------------------------------------------------------------------------


@dataclass
class SweepResult:
    """Result of sweeping one subject with + without the prompt overlay."""

    subject: str
    client: str
    behavior_version: int
    baseline_f1: float  # F1 without overlay (prompt_overlay=None)
    overlay_f1: float  # F1 with overlay
    lift: float  # overlay_f1 - baseline_f1 (negative when overlay hurts)
    n_samples: int
    baseline_per_sample: list[float] = field(default_factory=list)
    overlay_per_sample: list[float] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Overlay generator (Phase 6 baseline — intentionally a no-op stub).
# The real data-informed overlay lands in the Phase 6 follow-up commit
# once the PDF pipeline output is rich enough to drive it.
# ---------------------------------------------------------------------------


def build_prompt_overlay(
    subject_slug: str,
    behavior_version: int = 1,
) -> str | None:
    """Return the data-informed prompt overlay for a subject.

    Phase 6 baseline (this commit): returns ``None`` — the default
    prompts are the canonical baseline. Phase 6 follow-up commit will
    populate this from the chunk-index lookup.

    The ``behavior_version`` arg lets callers bump the overlay's cache
    key (matches BAML's ``prompt_behavior_version`` parameter so the
    BAML client cache invalidates correctly when the overlay text
    changes).
    """
    # The baseline: no overlay. Future versions will return a
    # canonical subject-specific vocabulary + common-error-patterns
    # string from the chunk index.
    return None


# ---------------------------------------------------------------------------
# Sweep harness
# ---------------------------------------------------------------------------

SweepInvoker = Callable[[str, str, str | None, int], tuple[str, int, int]]
"""
A SweepInvoker has signature (client, prompt, prompt_overlay, behavior_version)
-> (content, tokens_in, tokens_out). Tests inject a stub; production uses
the canonical Phase 3 lc6_extraction_app path.
"""


def sweep_one_subject(
    subject_slug: str,
    samples: list[EvalSample],
    *,
    behavior_version: int = 1,
    invoker: SweepInvoker | None = None,
) -> SweepResult:
    """Sweep one subject: run every sample with + without the overlay.

    Returns one SweepResult with baseline_f1, overlay_f1, and lift.
    When the overlay is None, overlay_f1 == baseline_f1 (no lift).
    """
    inv = invoker or _default_sweep_invoker
    overlay = build_prompt_overlay(subject_slug, behavior_version=behavior_version)
    client = client_for(subject_slug)

    baseline_f1s: list[float] = []
    overlay_f1s: list[float] = []
    for sample in samples:
        baseline = inv(client, sample.md_text, None, behavior_version)
        baseline_parsed = _try_parse(baseline[0])
        baseline_f1s.append(field_level_f1(baseline_parsed or {}, sample.ground_truth))
        overlay_out = inv(client, sample.md_text, overlay, behavior_version)
        overlay_parsed = _try_parse(overlay_out[0])
        overlay_f1s.append(field_level_f1(overlay_parsed or {}, sample.ground_truth))

    base_avg = statistics.mean(baseline_f1s) if baseline_f1s else 0.0
    over_avg = statistics.mean(overlay_f1s) if overlay_f1s else 0.0
    return SweepResult(
        subject=subject_slug,
        client=client,
        behavior_version=behavior_version,
        baseline_f1=base_avg,
        overlay_f1=over_avg,
        lift=over_avg - base_avg,
        n_samples=len(samples),
        baseline_per_sample=baseline_f1s,
        overlay_per_sample=overlay_f1s,
    )


def sweep_all_subjects(
    samples_by_subject: dict[str, list[EvalSample]],
    *,
    subjects: Iterable[str] = ALL_8,
    behavior_version: int = 1,
    invoker: SweepInvoker | None = None,
) -> list[SweepResult]:
    """Sweep every subject in ``subjects``.

    Args:
        samples_by_subject: dict mapping subject_slug -> list of EvalSamples.
        subjects: iterable of subject slugs (default = all 8 LC subjects).
    """
    results: list[SweepResult] = []
    for subject in subjects:
        samples = samples_by_subject.get(subject, [])
        if not samples:
            logger.warning("sweep.no_samples subject=%s", subject)
            continue
        results.append(
            sweep_one_subject(
                subject,
                samples_by_subject[subject],
                behavior_version=behavior_version,
                invoker=invoker,
            )
        )
    return results


# ---------------------------------------------------------------------------
# Default sweep invoker — delegates to the Phase 3 lc6_extraction_app path
# ---------------------------------------------------------------------------


def _default_sweep_invoker(
    client: str,
    prompt: str,
    prompt_overlay: str | None,
    behavior_version: int,
) -> tuple[str, int, int]:
    """Default invoker — deterministic stub for dev; production wires to BAML.

    Returns a minimal valid JSON with the ``prompt_overlay`` echoed (so
    callers can see whether the overlay was applied). Real production
    wires this to ``baml.b.ExtractCurriculumSyllabus(pdf_text, subject,
    language, prompt_overlay, prompt_behavior_version)``.
    """
    import json

    payload = {
        "stub": True,
        "client": client,
        "behavior_version": behavior_version,
        "overlay_applied": prompt_overlay is not None,
    }
    if prompt_overlay:
        payload["overlay_preview"] = prompt_overlay[:80]
    return json.dumps(payload), len(prompt) // 4, 100


def _try_parse(content: str) -> dict[str, Any] | None:
    """Best-effort JSON parse (delegates to runner._try_parse when available)."""
    try:
        from experiments.model_comparison.runner import _try_parse as runner_parse

        return runner_parse(content)
    except ImportError:
        import json

        try:
            parsed = json.loads(content)
        except (TypeError, json.JSONDecodeError):
            return None
        return parsed if isinstance(parsed, dict) else None


__all__ = [
    "ALL_8",
    "SUBJECT_CLIENTS",
    "SweepInvoker",
    "SweepResult",
    "build_prompt_overlay",
    "client_for",
    "sweep_all_subjects",
    "sweep_one_subject",
]
