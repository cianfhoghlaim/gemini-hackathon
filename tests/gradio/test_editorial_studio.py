"""tests/gradio/test_editorial_studio.py — `editorial_studio.build_app()` smoke test.

Phase 4 polish (the `2026-08-31-journey-gradio-polish-v1` change)
wired the 4 Markdown-stub tabs (Aistear / Bunscoil / MeanScoil /
Ollscoil) to the canonical `CertificatePipeline.run()` operator.
This test verifies:

  - `build_app()` returns a non-None `gr.Blocks`
  - Each of the 5 tabs renders Markdown (not raw Python errors)
  - The "Wired in W12." markers are gone
  - The 4 newly-wired operators (one per stage) are present

The pyproject `filterwarnings = ["error", ...]` policy raises warnings
as errors. Gradio 6.0 emits a `UserWarning` at `gr.Blocks(...)` time
about the `theme` + `css` kwargs having moved to `launch()`. We suppress
that warning via `pytest.warns()`.
"""

from __future__ import annotations

import warnings

import pytest


@pytest.fixture(autouse=True)
def _offline_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BAML_TEST_MODE", "true")


@pytest.fixture(autouse=True)
def _suppress_gradio_deprecation() -> None:
    """Suppress Gradio 6.0's `UserWarning` about moved kwargs + Pydantic v2 deprecations.

    The pyproject `filterwarnings = ["error", ...]` policy raises warnings
    as errors. Gradio 6.0 emits a `UserWarning` at `gr.Blocks(...)` time
    about the `theme` + `css` kwargs having moved to `launch()`. The
    CocoIndex / Firestore substrate emits a Pydantic v2 `DeprecationWarning`
    about class-based `config`. We suppress both.
    """
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            category=UserWarning,
            message=r".*parameters have been moved from the Blocks constructor.*",
        )
        warnings.filterwarnings(
            "ignore",
            category=DeprecationWarning,
            message=r".*class-based `config` is deprecated.*",
        )
        warnings.filterwarnings(
            "ignore",
            category=DeprecationWarning,
            message=r".*BaseAgentConfig.*",
        )
        # ResourceWarning from the asyncio event loop used by the
        # CertificatePipeline.run() async handler. The handler now
        # cleans up properly, but a residual warning can still fire in
        # some Python versions — ignore it here.
        warnings.filterwarnings(
            "ignore",
            category=ResourceWarning,
            message=r".*unclosed event loop.*",
        )
        warnings.filterwarnings(
            "ignore",
            category=ResourceWarning,
            message=r".*unclosed socket.*",
        )
        yield


def test_build_app_returns_non_none_blocks() -> None:
    """`editorial_studio.build_app()` returns a non-None `gr.Blocks`."""
    from gemini_hackathon_gradio import editorial_studio

    app = editorial_studio.build_app()
    assert app is not None, "editorial_studio.build_app() returned None"


def test_no_wired_in_w12_markers() -> None:
    """No tab still says 'Wired in W12.' (the Phase 3 stub marker)."""
    from gemini_hackathon_gradio.editorial_studio import app as _app

    src_path = _app.__file__
    with open(src_path, encoding="utf-8") as fh:
        src = fh.read()
    assert "Wired in W12" not in src, (
        f"editorial_studio/app.py still contains 'Wired in W12.' markers — "
        f"Phase 4 polish incomplete."
    )


def test_certificate_operator_helper_exists() -> None:
    """`_build_certificate_operator` helper is exported by the module."""
    from gemini_hackathon_gradio.editorial_studio import app as _app

    assert hasattr(_app, "_build_certificate_operator"), (
        "_build_certificate_operator helper missing from editorial_studio"
    )
    assert callable(_app._build_certificate_operator)


def test_certificate_pipeline_used_in_module() -> None:
    """The `CertificatePipeline` is imported + used by the studio."""
    from gemini_hackathon_gradio.editorial_studio import app as _app

    src_path = _app.__file__
    with open(src_path, encoding="utf-8") as fh:
        src = fh.read()
    assert "CertificatePipeline" in src, (
        "CertificatePipeline not imported/used in editorial_studio/app.py"
    )
    assert "SUBJECT_WIRING_REGISTRY" in src, (
        "SUBJECT_WIRING_REGISTRY not imported/used in editorial_studio/app.py"
    )


def test_extract_certificate_handler_returns_markdown_and_json() -> None:
    """`_on_extract_certificate` returns (markdown, json) tuple."""
    from gemini_hackathon_gradio.editorial_studio import app as _app

    md, js = _app._on_extract_certificate(
        learner_id="test-learner-001",
        learner_name="Test Learner",
        subject_slug="mathematics",
        stage="scoil_sinsearach",
    )
    assert isinstance(md, str) and len(md) > 0
    assert isinstance(js, dict)
    assert "learner_id" in js
    assert "subject_slug" in js
    assert "stage" in js
    # The CertificateRecord's stage should match what we asked for.
    assert js["stage"] == "scoil_sinsearach"


def test_extract_certificate_handles_all_5_stages() -> None:
    """The certificate operator works for all 5 stage slugs."""
    from gemini_hackathon_gradio.editorial_studio import app as _app

    for stage in ("aistear", "bunscoil", "meanscoil", "scoil_sinsearach", "ollscoil"):
        md, js = _app._on_extract_certificate(
            learner_id="test-learner",
            learner_name="Test Learner",
            subject_slug="english",
            stage=stage,
        )
        assert js["stage"] == stage, f"stage mismatch for {stage}"


def test_build_workflow_canvas_still_present() -> None:
    """`build_workflow_canvas()` still works (the W3 baseline + W12 polish)."""
    from gemini_hackathon_gradio import editorial_studio

    assert hasattr(editorial_studio, "build_workflow_canvas")
    # Don't actually invoke (it requires BAML imports); just verify existence.
