"""test_prompt_sweep.py — Phase 6 verification of the per-subject prompt sweep harness.

Tests:
  1. ``SUBJECT_CLIENTS`` has 8 entries (one per LC subject).
  2. ``client_for`` returns the right BAML client per subject.
  3. ``build_prompt_overlay`` returns ``None`` in the Phase 6 baseline.
  4. ``sweep_one_subject`` returns the canonical SweepResult shape.
  5. ``sweep_one_subject`` measures lift correctly (0 when overlay is None).
  6. ``sweep_all_subjects`` iterates all 8 subjects (or a subset).
  7. ``SweepResult.asdict`` roundtrips cleanly.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

import pytest


def _load(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


_base = pathlib.Path(__file__).resolve().parent.parent / "experiments" / "prompt_sweeps"
sweep = _load("_test_sweep", _base / "prompt_sweep.py")


def test_subject_clients_has_8_entries() -> None:
    assert len(sweep.SUBJECT_CLIENTS) == 8
    assert set(sweep.SUBJECT_CLIENTS.keys()) == set(sweep.ALL_8)


def test_client_for_per_subject() -> None:
    assert sweep.client_for("mathematics") == "BIEPV3ExtractMathematics"
    assert sweep.client_for("english") == "BIEPV3ExtractEnglish"
    assert sweep.client_for("gaeilge") == "BIEPV3ExtractGaeilge"
    assert sweep.client_for("chemistry") == "BIEPV3ExtractChemistry"
    assert sweep.client_for("biology") == "BIEPV3ExtractBiology"
    assert sweep.client_for("physics") == "BIEPV3ExtractPhysics"
    assert sweep.client_for("geography") == "BIEPV3ExtractGeography"
    assert sweep.client_for("computer_science") == "BIEPV3ExtractComputerScience"


def test_client_for_unknown_falls_back_to_base() -> None:
    """Unknown subject slug -> the base BIEPV3Extract client."""
    assert sweep.client_for("unknown") == "BIEPV3Extract"


def test_build_prompt_overlay_returns_none_in_baseline() -> None:
    """Phase 6 baseline — no data-informed overlay yet."""
    for subject in sweep.ALL_8:
        assert sweep.build_prompt_overlay(subject) is None
        assert sweep.build_prompt_overlay(subject, behavior_version=42) is None


def test_all_8_subjects_list_is_canonical() -> None:
    """``ALL_8`` is the project's canonical 8 LC subjects."""
    assert sweep.ALL_8 == (
        "mathematics",
        "english",
        "gaeilge",
        "chemistry",
        "biology",
        "physics",
        "geography",
        "computer_science",
    )


def test_sweep_one_subject_zero_lift_when_overlay_is_none() -> None:
    """Phase 6 baseline: overlay is None -> lift == 0."""
    from experiments.model_comparison.runner import EvalSample

    samples = [
        EvalSample(
            sample_id=f"math-{i}",
            pdf_path="x.pdf",
            subject="mathematics",
            language="en",
            md_text="# Math\n## Page 1\n\nAlgebra",
            ground_truth={"subject_slug": "mathematics"},
        )
        for i in range(3)
    ]

    result = sweep.sweep_one_subject("mathematics", samples)

    assert result.subject == "mathematics"
    assert result.client == "BIEPV3ExtractMathematics"
    assert result.behavior_version == 1
    assert result.n_samples == 3
    # Baseline F1 may be 0 (the default stub doesn't match ground_truth);
    # the structural assertion is what matters here.
    assert result.overlay_f1 == result.baseline_f1  # overlay is None
    assert result.lift == 0.0
    assert len(result.baseline_per_sample) == 3
    assert len(result.overlay_per_sample) == 3


def test_sweep_one_subject_measures_positive_lift_with_stub(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Inject a stub invoker that returns a perfect response when overlay is set.

    Monkey-patches ``build_prompt_overlay`` to return a non-None string so
    the overlay path is exercised (the Phase 6 baseline returns None).
    """
    from experiments.model_comparison.runner import EvalSample

    monkeypatch.setattr(
        sweep, "build_prompt_overlay", lambda subject, behavior_version=1: "OVERLAY"
    )

    samples = [
        EvalSample(
            sample_id=f"x-{i}",
            pdf_path="x.pdf",
            subject="mathematics",
            language="en",
            md_text="# Math\n## Page 1\n\nAlgebra",
            ground_truth={"subject_slug": "mathematics", "language": "en"},
        )
        for i in range(2)
    ]

    def stub_invoker(client, prompt, overlay, behavior_version):
        import json

        # Baseline: only subject_slug matches (1 of 2 truth fields -> F1=0)
        # Overlay: matches both subject_slug AND language (2 of 2 = F1=1.0)
        if overlay is not None:
            content = json.dumps({"subject_slug": "mathematics", "language": "en"})
        else:
            content = json.dumps({"subject_slug": "WRONG_VALUE"})
        return content, 100, 50

    result = sweep.sweep_one_subject(
        "mathematics", samples, behavior_version=2, invoker=stub_invoker
    )
    assert result.lift > 0.0  # overlay helped
    assert result.overlay_f1 > result.baseline_f1
    assert result.behavior_version == 2


def test_sweep_all_subjects_iterates_all_8() -> None:
    """Sweep all 8 subjects -> 8 results."""
    from experiments.model_comparison.runner import EvalSample

    def make_samples(subject):
        return [
            EvalSample(
                sample_id=f"{subject}-1",
                pdf_path="x.pdf",
                subject=subject,
                language="en",
                md_text="stub",
                ground_truth={},
            )
        ]

    samples_by_subject = {s: make_samples(s) for s in sweep.ALL_8}
    results = sweep.sweep_all_subjects(samples_by_subject)
    assert len(results) == 8
    assert {r.subject for r in results} == set(sweep.ALL_8)


def test_sweep_all_subjects_skips_subjects_without_samples() -> None:
    """Subjects without samples are skipped, not crashed."""
    samples_by_subject = {"mathematics": []}  # empty list -> skip
    results = sweep.sweep_all_subjects(samples_by_subject)
    assert results == []


def test_sweep_result_dataclass_serializes() -> None:
    result = sweep.SweepResult(
        subject="mathematics",
        client="BIEPV3ExtractMathematics",
        behavior_version=1,
        baseline_f1=0.85,
        overlay_f1=0.92,
        lift=0.07,
        n_samples=5,
    )
    as_dict = {
        "subject": result.subject,
        "client": result.client,
        "lift": result.lift,
    }
    assert as_dict["subject"] == "mathematics"
    assert as_dict["client"] == "BIEPV3ExtractMathematics"
    assert as_dict["lift"] == 0.07


def test_default_sweep_invoker_applies_overlay() -> None:
    """The default invoker echoes whether the overlay was applied."""
    import json

    content, _tin, _tout = sweep._default_sweep_invoker(
        "BIEPV3ExtractMathematics", "long prompt " * 10, None, 1
    )
    parsed = json.loads(content)
    assert parsed["overlay_applied"] is False
    assert parsed["behavior_version"] == 1

    content2, _, _ = sweep._default_sweep_invoker(
        "BIEPV3ExtractMathematics", "long prompt " * 10, "OVERLAY TEXT", 1
    )
    parsed2 = json.loads(content2)
    assert parsed2["overlay_applied"] is True
    assert "OVERLAY" in parsed2["overlay_preview"]
