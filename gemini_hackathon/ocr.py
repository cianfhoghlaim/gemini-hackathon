"""gemini_hackathon.ocr — capability-dispatched OCR/HTR/VLM pipeline.

Ported from cianfhoghlaim/bonneagar/stacks/ocr-router (the FastAPI
service that ships in that monorepo). Here we ship the router in-process
so the hackathon demo does not depend on that container being up.

Capability dispatch (single decision table):

    Capability          | Backend       | Default model
    --------------------|---------------|--------------------
    forms               | paddleocr     | paddleocr-vl-1.6
    layout              | mlx-omni      | qwen3-vl-8b
    tables+latex        | olmocr        | olmocr
    doctags             | docling-serve | docling-tags
    gaelic              | llama-swap    | gemma-4-26b-a4b
    english             | llama-swap    | qwen3-vl-8b
    tesseract-fallback  | dots-ocr      | paddleocr-vl-1.6
"""

from __future__ import annotations

import base64
import enum
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class Capability(str, enum.Enum):
    FORMS = "forms"
    LAYOUT = "layout"
    TABLES_LATEX = "tables+latex"
    DOCTAGS = "doctags"
    GAELIC = "gaelic"
    ENGLISH = "english"
    TESSERACT_FALLBACK = "tesseract-fallback"


class Backend(str, enum.Enum):
    PADDLEOCR = "paddleocr"
    MLX_OMNI = "mlx-omni"
    OLMOCR = "olmocr"
    DOCLING_SERVE = "docling-serve"
    LLAMA_SWAP = "llama-swap"
    DOTS_OCR = "dots-ocr"


class CapabilityUnavailableError(RuntimeError):
    """Raised when the requested capability's backend is not deployed."""


@dataclass(frozen=True)
class OcrResult:
    """A single OCR/VLM extraction result."""

    capability: Capability
    backend: Backend
    model: str
    text: str
    duration_ms: int
    pages_processed: int = 0
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OcrRequest:
    """The request envelope."""

    capability: Capability
    image_path: str
    base_url: str | None = None
    model: str | None = None
    language_hint: str | None = None
    timeout_seconds: float = 30.0


_DISPATCH_TABLE: dict[Capability, tuple[Backend, str, str]] = {
    Capability.FORMS:             (Backend.PADDLEOCR,     "paddleocr-vl-1.6", "LLAMA_SWAP_BASE_URL"),
    Capability.LAYOUT:            (Backend.MLX_OMNI,      "qwen3-vl-8b",      "LLAMA_SWAP_BASE_URL"),
    Capability.TABLES_LATEX:      (Backend.OLMOCR,        "olmocr",           "OLMOCR_BASE_URL"),
    Capability.DOCTAGS:           (Backend.DOCLING_SERVE, "docling-tags",     "DOCLING_SERVE_BASE_URL"),
    Capability.GAELIC:            (Backend.LLAMA_SWAP,    "gemma-4-26b-a4b",  "LLAMA_SWAP_BASE_URL"),
    Capability.ENGLISH:           (Backend.LLAMA_SWAP,    "qwen3-vl-8b",      "LLAMA_SWAP_BASE_URL"),
    Capability.TESSERACT_FALLBACK:(Backend.DOTS_OCR,      "paddleocr-vl-1.6", "LLAMA_SWAP_BASE_URL"),
}


def _resolve_base_url(capability: Capability, override: str | None) -> str:
    if override:
        return override
    _, _, env_var = _DISPATCH_TABLE[capability]
    url = os.environ.get(env_var)
    if not url:
        raise CapabilityUnavailableError(
            f"Capability {capability.value} requires {env_var} but it is not set"
        )
    return url


def is_backend_available(base_url: str, timeout: float = 2.0) -> bool:
    try:
        r = httpx.get(f"{base_url.rstrip('/')}/models", timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False


def _encode_image_for_chat_completion(image_path: str) -> dict[str, Any]:
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    ext = image_path.rsplit(".", 1)[-1].lower() if "." in image_path else ""
    mime = {
        "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "gif": "image/gif", "webp": "image/webp",
    }.get(ext, "application/pdf" if ext == "pdf" else "application/octet-stream")
    return {
        "type": "image_url",
        "image_url": {"url": f"data:{mime};base64,{b64}"},
    }


def _prompt_for(capability: Capability, language_hint: str | None) -> str:
    base = {
        Capability.FORMS: "Extract the text content from this form or worksheet. Preserve field labels exactly. Output plain text only.",
        Capability.LAYOUT: "Extract the layout of this document page. Preserve section headings, paragraphs, and reading order. Output plain text only.",
        Capability.TABLES_LATEX: "Extract every table and mathematical formula. For formulas, emit LaTeX inside $...$. For tables, use markdown pipe syntax.",
        Capability.DOCTAGS: "Convert this page to IBM DocTags JSON. Include every block type, bbox, and reading order.",
        Capability.GAELIC: "Extract the Irish-language text from this document. Preserve every fada, every séimhiú. Output plain text only.",
        Capability.ENGLISH: "Extract the English-language text from this document page. Output plain text only.",
        Capability.TESSERACT_FALLBACK: "Tesseract-style OCR fallback. Extract whatever text you can from this image. Output plain text only.",
    }.get(capability, "Extract the text content. Output plain text only.")
    if language_hint:
        base += f" Language hint: {language_hint}."
    return base


def ocr(request: OcrRequest) -> OcrResult:
    backend, default_model, env_var = _DISPATCH_TABLE[request.capability]
    base_url = _resolve_base_url(request.capability, request.base_url)
    model = request.model or default_model

    start = time.monotonic()
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": _prompt_for(request.capability, request.language_hint)},
                _encode_image_for_chat_completion(request.image_path),
            ],
        }
    ]

    url = f"{base_url.rstrip('/')}/chat/completions"
    api_key = os.environ.get("LLAMASWAP_API_KEY") or os.environ.get("OPENAI_API_KEY") or "not-required"
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 4096,
    }

    with httpx.Client(timeout=request.timeout_seconds) as client:
        resp = client.post(url, json=payload, headers={"Authorization": f"Bearer {api_key}"})

    duration_ms = int((time.monotonic() - start) * 1000)
    if resp.status_code >= 400:
        raise CapabilityUnavailableError(
            f"Backend {backend.value} returned {resp.status_code} for capability "
            f"{request.capability.value}: {resp.text[:200]}"
        )

    body = resp.json()
    text = body["choices"][0]["message"]["content"]
    return OcrResult(
        capability=request.capability,
        backend=backend,
        model=model,
        text=text,
        duration_ms=duration_ms,
        pages_processed=1,
        extras={"status_code": resp.status_code, "usage": body.get("usage", {})},
    )


def auto_capability(pdf_path: str) -> Capability:
    """Best-effort capability heuristic for a PDF path."""
    name = pdf_path.lower()
    if any(token in name for token in ("gaeilge", "irish", "gaelic", "cymraeg", "welsh", "gaidhlig")):
        return Capability.GAELIC
    return Capability.ENGLISH


__all__ = [
    "Backend",
    "Capability",
    "CapabilityUnavailableError",
    "OcrRequest",
    "OcrResult",
    "_DISPATCH_TABLE",
    "auto_capability",
    "is_backend_available",
    "ocr",
]
