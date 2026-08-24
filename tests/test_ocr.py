"""Tests for the gemini_hackathon.ocr capability router."""

from __future__ import annotations

import json

import httpx
import pytest

from gemini_hackathon.ocr import (
    Backend,
    Capability,
    CapabilityUnavailableError,
    OcrRequest,
    _DISPATCH_TABLE,
    auto_capability,
    is_backend_available,
    ocr,
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


def test_dispatch_gaelic_uses_gemma_4_26b():
    backend, model, _ = _DISPATCH_TABLE[Capability.GAELIC]
    assert backend == Backend.LLAMA_SWAP
    assert "gemma-4-26b" in model


def test_dispatch_english_uses_qwen3_vl():
    backend, model, _ = _DISPATCH_TABLE[Capability.ENGLISH]
    assert backend == Backend.LLAMA_SWAP
    assert model == "qwen3-vl-8b"


def test_dispatch_forms_uses_paddleocr_vl():
    backend, model, _ = _DISPATCH_TABLE[Capability.FORMS]
    assert model == "paddleocr-vl-1.6"


# ---------------------------------------------------------------------------
# Env-var resolution
# ---------------------------------------------------------------------------


def test_resolve_uses_override_when_provided(monkeypatch):
    monkeypatch.delenv("LLAMA_SWAP_BASE_URL", raising=False)
    from gemini_hackathon.ocr import _resolve_base_url
    assert _resolve_base_url(Capability.ENGLISH, "http://override:9090/v1") == "http://override:9090/v1"


def test_resolve_raises_when_env_unset(monkeypatch):
    monkeypatch.delenv("LLAMA_SWAP_BASE_URL", raising=False)
    monkeypatch.delenv("OLMOCR_BASE_URL", raising=False)
    monkeypatch.delenv("DOCLING_SERVE_BASE_URL", raising=False)
    from gemini_hackathon.ocr import _resolve_base_url
    with pytest.raises(CapabilityUnavailableError):
        _resolve_base_url(Capability.ENGLISH, None)


# ---------------------------------------------------------------------------
# auto_capability heuristic
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
# is_backend_available
# ---------------------------------------------------------------------------


def test_is_backend_available_false_for_unreachable():
    assert is_backend_available("http://127.0.0.1:1/v1", timeout=0.5) is False


def test_is_backend_available_true_for_live_llama_swap():
    """Skip if llama-swap isn't running locally."""
    try:
        result = is_backend_available("http://127.0.0.1:8080/v1", timeout=1.0)
    except Exception:
        pytest.skip("llama-swap not running on this machine")
    assert result is True


# ---------------------------------------------------------------------------
# Prompt content per capability
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
# OCR round-trip with a mocked httpx.Client.post
# ---------------------------------------------------------------------------


def test_ocr_returns_extracted_text(tmp_path, monkeypatch):
    """The OCR dispatcher encodes the image and posts to llama-swap."""
    from gemini_hackathon import ocr as ocr_module

    png_bytes = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
        "0000000a49444154789c6300010000000500010d0a2db40000000049454e44ae426082"
    )
    image = tmp_path / "page1.png"
    image.write_bytes(png_bytes)

    captured = {}

    def fake_post(self, url, json, headers):
        captured["url"] = url
        captured["model"] = json.get("model")
        captured["content_type"] = json.get("messages", [{}])[0].get("content")
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "Extracted: hello world"}}],
                "usage": {"prompt_tokens": 128, "completion_tokens": 32},
            },
        )

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    result = ocr(OcrRequest(
        capability=Capability.ENGLISH,
        image_path=str(image),
        base_url="http://127.0.0.1:8080/v1",
        model="qwen3-vl-8b",
    ))
    assert result.text == "Extracted: hello world"
    assert result.backend == Backend.LLAMA_SWAP
    assert result.model == "qwen3-vl-8b"
    assert result.duration_ms >= 0
    assert captured["model"] == "qwen3-vl-8b"
    assert any(item.get("type") == "image_url" for item in (captured.get("content_type") or []))
