"""Tests for the gemini_hackathon.ocr PDF text extraction helper.

Phase 5 of the GCP-first refactor: `extract_pdf_text` now dispatches to
Document AI / Gemini Vision / pypdfium2's text layer (see
`gemini_hackathon/ocr.py`'s module docstring) instead of a self-hosted
llama-swap container. Without `GCP_PROJECT_ID` set, the function raises
`CapabilityUnavailableError`; the live end-to-end test is opt-in (gated on
`RUN_LIVE_GCP_TESTS=1` in addition to `GCP_PROJECT_ID`) so a bare `pytest`
run never makes a billed Vertex AI call.

For the page-rendering helper, a minimal test using the existing
`data/syllabi/sample_lc_maths_2024.pdf` (or a freshly generated one)
proves the pipeline doesn't crash on an input file.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_PDF = REPO_ROOT / "data" / "syllabi" / "sample_lc_maths_2024.pdf"


@pytest.fixture
def tmp_pdf(tmp_path: Path) -> Path:
    """Provide the canonical sample PDF or skip."""
    if not SAMPLE_PDF.exists():
        pytest.skip(f"sample PDF not present: {SAMPLE_PDF}")
    return SAMPLE_PDF


# ---------------------------------------------------------------------------
# _render_pdf_pages_to_pngs
# ---------------------------------------------------------------------------


def test_render_pdf_pages_to_pngs_produces_one_png_per_page(tmp_pdf: Path):
    """The page renderer emits one PNG per page in the PDF."""
    from gemini_hackathon.ocr import _render_pdf_pages_to_pngs

    pngs = _render_pdf_pages_to_pngs(str(tmp_pdf))
    assert len(pngs) >= 1
    for p in pngs:
        assert Path(p).exists()
        assert Path(p).suffix == ".png"


def test_render_pdf_pages_respects_max_pages(tmp_pdf: Path):
    """max_pages caps the output count."""
    from gemini_hackathon.ocr import _render_pdf_pages_to_pngs

    pngs = _render_pdf_pages_to_pngs(str(tmp_pdf), max_pages=1)
    assert len(pngs) == 1


# ---------------------------------------------------------------------------
# auto_capability + extract_pdf_text
# ---------------------------------------------------------------------------


def test_auto_capability_returns_gaelic_for_irish_path():
    from gemini_hackathon.ocr import Capability, auto_capability

    assert auto_capability("/tmp/lc_maths_gaeilge_2024.pdf") == Capability.GAELIC
    assert auto_capability("/tmp/cymraeg_syllabus.pdf") == Capability.GAELIC
    assert auto_capability("/tmp/lc_maths_2024.pdf") == Capability.ENGLISH


def test_extract_pdf_text_raises_when_gcp_project_unset(tmp_pdf: Path, monkeypatch):
    """Without GCP_PROJECT_ID, the Gemini Vision backend must raise a typed error."""
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
    pytest.importorskip("vertexai")
    from gemini_hackathon.ocr import (
        Capability,
        CapabilityUnavailableError,
        extract_pdf_text,
    )

    with pytest.raises(CapabilityUnavailableError):
        extract_pdf_text(
            str(tmp_pdf),
            capability=Capability.ENGLISH,
            timeout_seconds=1.0,
            max_pages=1,
        )


def test_extract_pdf_text_via_pypdfium2_textlayer_needs_no_gcp(tmp_pdf: Path, monkeypatch):
    """The TESSERACT_FALLBACK capability reads the embedded text layer
    directly — no GCP credentials required at all, so this is the one
    `extract_pdf_text` path that always runs in CI.
    """
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
    from gemini_hackathon.ocr import Capability, extract_pdf_text

    result = extract_pdf_text(
        str(tmp_pdf),
        capability=Capability.TESSERACT_FALLBACK,
        max_pages=2,
    )
    assert result["backend"] == "pypdfium2_textlayer"
    assert result["page_count"] >= 1


@pytest.mark.skipif(
    not (os.environ.get("GCP_PROJECT_ID") and os.environ.get("RUN_LIVE_GCP_TESTS") == "1"),
    reason="opt-in: set GCP_PROJECT_ID + RUN_LIVE_GCP_TESTS=1 to run a real (billed) Vertex AI call",
)
def test_extract_pdf_text_real_via_live_gemini_vision(tmp_pdf: Path):
    """End-to-end OCR through a real Vertex AI Gemini call. Opt-in only —
    see the skipif reason; this makes a billed API call.
    """
    from gemini_hackathon.ocr import Capability, extract_pdf_text

    result = extract_pdf_text(
        str(tmp_pdf),
        capability=Capability.ENGLISH,
        timeout_seconds=60.0,
        max_pages=2,
    )
    assert result["page_count"] >= 1
    assert len(result["text"]) > 50
    assert result["model"]
    assert result["backend"] == "gemini_vision"
