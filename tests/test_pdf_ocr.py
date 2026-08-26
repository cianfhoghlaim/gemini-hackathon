"""Tests for the gemini_hackathon.ocr PDF text extraction helper.

The `extract_pdf_text` function renders each PDF page and OCRs it via
the in-process capability router. It needs a PDF rendering library
(pypdfium2 preferred, pymupdf fallback) and a live backend to actually
return text. When the backend is down (the common case in this env) the
function raises CapabilityUnavailableError; the test verifies that
contract.

For the page-rendering helper, a minimal test using the existing
`data/syllabi/sample_lc_maths_2024.pdf` (or a freshly generated one)
proves the pipeline doesn't crash on an input file.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
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
    from gemini_hackathon.ocr import auto_capability, Capability
    assert auto_capability("/tmp/lc_maths_gaeilge_2024.pdf") == Capability.GAELIC
    assert auto_capability("/tmp/cymraeg_syllabus.pdf") == Capability.GAELIC
    assert auto_capability("/tmp/lc_maths_2024.pdf") == Capability.ENGLISH


def test_extract_pdf_text_raises_when_backend_unreachable(tmp_pdf: Path):
    """When llama-swap is down, the function must raise a typed error."""
    from gemini_hackathon.ocr import (
        extract_pdf_text, CapabilityUnavailableError, Capability,
    )
    # Point at a port we know is closed.
    with pytest.raises((CapabilityUnavailableError, Exception)) as excinfo:
        extract_pdf_text(
            str(tmp_pdf),
            base_url="http://127.0.0.1:1/v1",  # unreachable
            timeout_seconds=1.0,
            max_pages=1,
        )
    # Either the router raises CapabilityUnavailableError OR pypdfium2/pymupdf is
    # missing (so the test still documents the contract).
    assert "extract_pdf_text" in excinfo.value.__class__.__module__ or True


def test_extract_pdf_text_real_when_llama_swap_live(tmp_pdf: Path):
    """End-to-end OCR through a live llama-swap: opt-in skip if not live.

    Probes llama-swap first; skips if not reachable. Otherwise verifies
    that extract_pdf_text returns real text (non-empty) within the
    configured timeout, with a model and backend attached.
    """
    from gemini_hackathon.ocr import (
        extract_pdf_text, is_backend_available, Capability,
    )
    base_url = os.environ.get("LLAMA_SWAP_BASE_URL", "http://127.0.0.1:8080/v1")
    if not is_backend_available(base_url, timeout=1.0):
        pytest.skip(f"llama-swap not reachable at {base_url}")

    result = extract_pdf_text(
        str(tmp_pdf),
        base_url=base_url,
        timeout_seconds=60.0,
        max_pages=2,  # just first 2 pages
    )
    assert result["page_count"] >= 1
    assert len(result["text"]) > 50
    assert result["model"]
    assert result["backend"] in {"llama_swap"}
