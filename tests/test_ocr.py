"""Tests for the gemini_hackathon.ocr capability router.

Phase 5 of the GCP-first refactor: rewritten for the 4 GCP-native backends
(Document AI / Gemini Vision / Gemma Vertex / pypdfium2 text-layer) that
replaced the 6 self-hosted containers (paddleocr / mlx-omni / olmocr /
docling-serve / llama-swap / dots-ocr). The old
`test_is_backend_available_true_for_live_llama_swap` (flagged in
docs/KNOWN_ISSUES.md as asserting a live local backend) no longer applies
— there is no local backend to be live; `is_backend_available()` is now a
pure env-var/library-presence check, so it's deterministic and doesn't
need a skip-if-unreachable guard.
"""

from __future__ import annotations

import pytest

from gemini_hackathon.ocr import (
    _DISPATCH_TABLE,
    Backend,
    Capability,
    CapabilityUnavailableError,
    OcrRequest,
    auto_capability,
    is_backend_available,
)

# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------


def test_dispatch_table_has_seven_capabilities():
    assert len(_DISPATCH_TABLE) == 7
    assert {c.value for c in _DISPATCH_TABLE} == {
        "forms", "layout", "tables+latex", "doctags",
        "gaelic", "english", "tesseract-fallback",
    }


def test_dispatch_gaelic_uses_gemini_vision():
    backend, model = _DISPATCH_TABLE[Capability.GAELIC]
    assert backend == Backend.GEMINI_VISION
    assert "gemini" in model


def test_dispatch_english_uses_gemini_vision():
    backend, model = _DISPATCH_TABLE[Capability.ENGLISH]
    assert backend == Backend.GEMINI_VISION
    assert "gemini" in model


def test_dispatch_forms_uses_document_ai():
    backend, _ = _DISPATCH_TABLE[Capability.FORMS]
    assert backend == Backend.DOCUMENT_AI


def test_dispatch_tesseract_fallback_uses_pypdfium2_textlayer():
    """The cheapest capability now does no OCR call at all — it reads the
    PDF's embedded text layer directly."""
    backend, _ = _DISPATCH_TABLE[Capability.TESSERACT_FALLBACK]
    assert backend == Backend.PYPDFIUM2_TEXTLAYER


# ---------------------------------------------------------------------------
# auto_capability heuristic (unchanged by the refactor)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path,expected", [
    ("/tmp/lc_maths_2024.pdf",       Capability.ENGLISH),
    ("/tmp/aqa_gcse_chemistry.pdf",  Capability.ENGLISH),
    ("/tmp/sqa_higher_maths.pdf",    Capability.ENGLISH),
    ("/tmp/gaeilge_paper_1.pdf",     Capability.GAELIC),
    ("/tmp/irish_history.pdf",       Capability.GAELIC),
    ("/tmp/cymraeg_syllabus.pdf",    Capability.GAELIC),
    ("/tmp/welsh-medium.pdf",        Capability.GAELIC),
    ("/tmp/gaidhlig_national_5.pdf", Capability.GAELIC),
])
def test_auto_capability_heuristic(path, expected):
    assert auto_capability(path) == expected


# ---------------------------------------------------------------------------
# is_backend_available — now a pure env-var/library-presence check, no
# network call, so it's deterministic in CI with no live-backend skip.
# ---------------------------------------------------------------------------


def test_is_backend_available_false_without_gcp_project_id(monkeypatch):
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
    assert is_backend_available(Backend.GEMINI_VISION) is False


def test_is_backend_available_false_for_document_ai_without_processor_id(monkeypatch):
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
    monkeypatch.delenv("DOCUMENT_AI_PROCESSOR_ID", raising=False)
    assert is_backend_available(Backend.DOCUMENT_AI) is False


def test_is_backend_available_false_for_gemma_vertex_without_endpoint_id(monkeypatch):
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
    monkeypatch.delenv("GEMMA_VERTEX_ENDPOINT_ID", raising=False)
    assert is_backend_available(Backend.GEMMA_VERTEX) is False


def test_is_backend_available_true_for_pypdfium2_textlayer():
    """pypdfium2 has no GCP dependency — always available if installed
    (a hard requirement of this repo, per pyproject.toml)."""
    assert is_backend_available(Backend.PYPDFIUM2_TEXTLAYER) is True


# ---------------------------------------------------------------------------
# Prompt content per capability (unchanged by the refactor)
# ---------------------------------------------------------------------------


def test_gaelic_prompt_preserves_fada():
    from gemini_hackathon.ocr import _prompt_for
    prompt = _prompt_for(Capability.GAELIC, language_hint=None)
    assert "fada" in prompt
    assert "séimhiú" in prompt


def test_english_prompt_is_plain():
    from gemini_hackathon.ocr import _prompt_for
    prompt = _prompt_for(Capability.ENGLISH, language_hint=None)
    assert "English" in prompt
    assert "plain text" in prompt


def test_prompt_includes_language_hint_when_provided():
    from gemini_hackathon.ocr import _prompt_for
    prompt = _prompt_for(Capability.GAELIC, language_hint="Munster")
    assert "Munster" in prompt


# ---------------------------------------------------------------------------
# OCR round-trip with a mocked Vertex AI GenerativeModel
# ---------------------------------------------------------------------------


def test_ocr_returns_extracted_text_via_gemini_vision(tmp_path, monkeypatch):
    """The OCR dispatcher builds an image Part and calls Gemini via Vertex AI."""
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project")

    png_bytes = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
        "0000000a49444154789c6300010000000500010d0a2db40000000049454e44ae426082"
    )
    image = tmp_path / "page1.png"
    image.write_bytes(png_bytes)

    vertexai = pytest.importorskip("vertexai")
    from vertexai.generative_models import GenerativeModel

    class _FakeUsage:
        prompt_token_count = 128
        candidates_token_count = 32

    class _FakeResponse:
        text = "Extracted: hello world"
        usage_metadata = _FakeUsage()

    captured = {}

    def fake_generate_content(self, contents, generation_config=None):
        captured["model"] = self._model_name if hasattr(self, "_model_name") else None
        captured["contents"] = contents
        return _FakeResponse()

    monkeypatch.setattr(vertexai, "init", lambda **kwargs: None)
    monkeypatch.setattr(GenerativeModel, "generate_content", fake_generate_content, raising=False)

    from gemini_hackathon.ocr import ocr

    result = ocr(OcrRequest(
        capability=Capability.ENGLISH,
        image_path=str(image),
    ))
    assert result.text == "Extracted: hello world"
    assert result.backend == Backend.GEMINI_VISION
    assert result.duration_ms >= 0
    assert result.extras["prompt_tokens"] == 128


def test_ocr_raises_capability_unavailable_without_gcp_project_id(tmp_path, monkeypatch):
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
    pytest.importorskip("vertexai")

    png_bytes = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
        "0000000a49444154789c6300010000000500010d0a2db40000000049454e44ae426082"
    )
    image = tmp_path / "page1.png"
    image.write_bytes(png_bytes)

    from gemini_hackathon.ocr import ocr

    with pytest.raises(CapabilityUnavailableError):
        ocr(OcrRequest(capability=Capability.ENGLISH, image_path=str(image)))
