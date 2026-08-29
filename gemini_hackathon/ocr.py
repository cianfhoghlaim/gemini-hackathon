"""gemini_hackathon.ocr — capability-dispatched OCR/HTR/VLM pipeline.

Phase 5 of the GCP-first refactor. Previously dispatched to 6 self-hosted
HTTP containers (paddleocr / mlx-omni / olmocr / docling-serve /
llama-swap / dots-ocr) — none of which exist in a Cloud Run deployment,
so `extract_pdf_text()` could never actually run in the demo path this
repo ships. Rewritten to dispatch to 4 GCP-native backends instead; same
public API (`Capability`, `OcrRequest`, `OcrResult`, `ocr()`,
`extract_pdf_text()`), so existing call sites are unaffected.

Capability dispatch (single decision table):

    Capability          | Backend              | Why
    --------------------|----------------------|--------------------------
    forms                | document_ai          | Layout Parser handles form fields well
    layout                | document_ai          | Layout Parser's native purpose
    tables+latex          | gemini_vision        | Document AI doesn't emit LaTeX; Gemini's
                          |                      | native multimodal reasoning does
    doctags                | document_ai          | closest GCP analogue to IBM DocTags —
                          |                      | Document AI's structured block JSON
                          |                      | (NOT byte-identical to DocTags; see
                          |                      | `_call_document_ai`'s docstring)
    gaelic                 | gemini_vision        | Gemini 3.5 Flash's multilingual EN/GA
                          |                      | support beats a locally-hosted model,
                          |                      | with no endpoint provisioning needed
    english                | gemini_vision        | same reasoning as gaelic
    tesseract-fallback     | pypdfium2_textlayer  | pure-Python embedded-text-layer
                          |                      | extraction — no OCR call at all when
                          |                      | the PDF already has a text layer
                          |                      | (the actual "cheap last resort" this
                          |                      | capability was always meant to be)

`gemma_vertex` (Gemma 4 on Vertex AI Model Garden) is available as an
explicit backend override for the `gaelic`/`english` capabilities — it is
NOT the default because it requires a deployed prediction endpoint
(`GEMMA_VERTEX_ENDPOINT_ID`), unlike `gemini_vision` which needs no
provisioning beyond API access. See `_call_gemma_vertex`.
"""

from __future__ import annotations

import enum
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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
    DOCUMENT_AI = "document_ai"
    GEMINI_VISION = "gemini_vision"
    GEMMA_VERTEX = "gemma_vertex"
    PYPDFIUM2_TEXTLAYER = "pypdfium2_textlayer"


class CapabilityUnavailableError(RuntimeError):
    """Raised when the requested capability's backend is not deployed/configured."""


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


#: capability -> (backend, default model/processor-type)
_DISPATCH_TABLE: dict[Capability, tuple[Backend, str]] = {
    Capability.FORMS: (Backend.DOCUMENT_AI, "FORM_PARSER_PROCESSOR"),
    Capability.LAYOUT: (Backend.DOCUMENT_AI, "LAYOUT_PARSER_PROCESSOR"),
    Capability.TABLES_LATEX: (Backend.GEMINI_VISION, "gemini-3.5-flash"),
    Capability.DOCTAGS: (Backend.DOCUMENT_AI, "LAYOUT_PARSER_PROCESSOR"),
    Capability.GAELIC: (Backend.GEMINI_VISION, "gemini-3.5-flash"),
    Capability.ENGLISH: (Backend.GEMINI_VISION, "gemini-3.5-flash"),
    Capability.TESSERACT_FALLBACK: (Backend.PYPDFIUM2_TEXTLAYER, "textlayer"),
}


def _prompt_for(capability: Capability, language_hint: str | None) -> str:
    base = {
        Capability.FORMS: "Extract the text content from this form or worksheet. Preserve field labels exactly. Output plain text only.",
        Capability.LAYOUT: "Extract the layout of this document page. Preserve section headings, paragraphs, and reading order. Output plain text only.",
        Capability.TABLES_LATEX: "Extract every table and mathematical formula. For formulas, emit LaTeX inside $...$. For tables, use markdown pipe syntax.",
        Capability.DOCTAGS: "Convert this page to a structured block-level JSON description. Include every block type, its bounding box, and reading order.",
        Capability.GAELIC: "Extract the Irish-language text from this document. Preserve every fada, every séimhiú. Output plain text only.",
        Capability.ENGLISH: "Extract the English-language text from this document page. Output plain text only.",
        Capability.TESSERACT_FALLBACK: "Extract whatever text you can from this image. Output plain text only.",
    }.get(capability, "Extract the text content. Output plain text only.")
    if language_hint:
        base += f" Language hint: {language_hint}."
    return base


def is_backend_available(backend: Backend) -> bool:
    """Return True if `backend`'s required env vars / client library are
    present. Cheap, offline check — does not make a network call (unlike
    the pre-refactor version, which pinged a `/models` endpoint; GCP APIs
    don't have an equivalent cheap health-check without cost).
    """
    if backend == Backend.PYPDFIUM2_TEXTLAYER:
        try:
            import pypdfium2  # noqa: F401,PLC0415

            return True
        except ImportError:
            return False
    if backend == Backend.DOCUMENT_AI:
        try:
            import google.cloud.documentai  # noqa: F401,PLC0415
        except ImportError:
            return False
        return bool(os.environ.get("GCP_PROJECT_ID")) and bool(
            os.environ.get("DOCUMENT_AI_PROCESSOR_ID")
        )
    if backend in (Backend.GEMINI_VISION, Backend.GEMMA_VERTEX):
        try:
            import vertexai  # noqa: F401,PLC0415
        except ImportError:
            return False
        if not os.environ.get("GCP_PROJECT_ID"):
            return False
        if backend == Backend.GEMMA_VERTEX:
            return bool(os.environ.get("GEMMA_VERTEX_ENDPOINT_ID"))
        return True
    return False


# ---------------------------------------------------------------------------
# Backend implementations
# ---------------------------------------------------------------------------


def _call_document_ai(image_path: str, processor_type: str, timeout_seconds: float) -> tuple[str, dict[str, Any]]:
    """Call Document AI's `process_document` (synchronous, single-page).

    Uses the Layout Parser processor for both `layout` and `doctags`
    capabilities (Document AI does not have a byte-identical IBM DocTags
    output mode — its structured JSON is the closest GCP analogue) and the
    Form Parser processor for `forms`. The processor must be pre-created in
    the GCP console/Terraform (`DOCUMENT_AI_PROCESSOR_ID` env var — one
    processor ID; swapping processor *type* per capability requires either
    2 processor IDs or routing all 3 capabilities through one Layout
    Parser processor, which is what this function does by default).
    """
    from google.cloud import documentai  # noqa: PLC0415

    project_id = os.environ.get("GCP_PROJECT_ID")
    location = os.environ.get("DOCUMENT_AI_LOCATION", "us")
    processor_id = os.environ.get("DOCUMENT_AI_PROCESSOR_ID")
    if not (project_id and processor_id):
        raise CapabilityUnavailableError(
            "Document AI requires GCP_PROJECT_ID and DOCUMENT_AI_PROCESSOR_ID"
        )

    client = documentai.DocumentProcessorServiceClient(
        client_options={"api_endpoint": f"{location}-documentai.googleapis.com"}
    )
    name = client.processor_path(project_id, location, processor_id)

    mime_type = "application/pdf" if image_path.lower().endswith(".pdf") else "image/png"
    with open(image_path, "rb") as f:
        content = f.read()

    request = documentai.ProcessRequest(
        name=name,
        raw_document=documentai.RawDocument(content=content, mime_type=mime_type),
    )
    result = client.process_document(request=request, timeout=timeout_seconds)
    document = result.document
    extras = {
        "page_count": len(document.pages),
        "processor_type": processor_type,
    }
    return document.text, extras


def _call_gemini_vision(
    image_path: str, prompt: str, model: str, timeout_seconds: float
) -> tuple[str, dict[str, Any]]:
    """Call Gemini via Vertex AI's `GenerativeModel` with an inline image part."""
    import vertexai  # noqa: PLC0415
    from vertexai.generative_models import GenerationConfig, GenerativeModel, Part  # noqa: PLC0415

    project_id = os.environ.get("GCP_PROJECT_ID")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    if not project_id:
        raise CapabilityUnavailableError("Gemini Vision requires GCP_PROJECT_ID")

    vertexai.init(project=project_id, location=location)
    generative_model = GenerativeModel(model)

    mime_type = "application/pdf" if image_path.lower().endswith(".pdf") else "image/png"
    with open(image_path, "rb") as f:
        content_bytes = f.read()

    image_part = Part.from_data(data=content_bytes, mime_type=mime_type)
    response = generative_model.generate_content(
        [image_part, prompt],
        generation_config=GenerationConfig(temperature=0.1, max_output_tokens=4096),
    )
    text = response.text
    usage = getattr(response, "usage_metadata", None)
    extras = {
        "prompt_tokens": getattr(usage, "prompt_token_count", None),
        "candidates_tokens": getattr(usage, "candidates_token_count", None),
    }
    return text, extras


def _call_gemma_vertex(
    image_path: str, prompt: str, timeout_seconds: float
) -> tuple[str, dict[str, Any]]:
    """Call a Gemma 4 model deployed to a Vertex AI Model Garden prediction
    endpoint. Requires `GEMMA_VERTEX_ENDPOINT_ID` (the deployed endpoint,
    not the model — Gemma is served via a prediction endpoint, not the
    `GenerativeModel` Gemini API surface).
    """
    from google.cloud import aiplatform  # noqa: PLC0415

    project_id = os.environ.get("GCP_PROJECT_ID")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    endpoint_id = os.environ.get("GEMMA_VERTEX_ENDPOINT_ID")
    if not (project_id and endpoint_id):
        raise CapabilityUnavailableError(
            "Gemma Vertex requires GCP_PROJECT_ID and GEMMA_VERTEX_ENDPOINT_ID "
            "(the deployed Model Garden prediction endpoint)"
        )

    aiplatform.init(project=project_id, location=location)
    endpoint = aiplatform.Endpoint(endpoint_id)

    import base64  # noqa: PLC0415

    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")

    instances = [{"prompt": prompt, "image": {"bytesBase64Encoded": b64}, "max_tokens": 4096}]
    response = endpoint.predict(instances=instances, timeout=timeout_seconds)
    prediction = response.predictions[0] if response.predictions else ""
    text = prediction if isinstance(prediction, str) else prediction.get("text", "")
    return text, {}


def _call_pypdfium2_textlayer(pdf_path: str) -> tuple[str, dict[str, Any]]:
    """Extract the embedded text layer directly (no OCR/VLM call at all —
    the actual "cheap last resort" this capability was always meant to be:
    if a PDF already has a text layer, OCRing its rendered pages is wasted
    work).
    """
    import pypdfium2 as pdfium  # noqa: PLC0415

    pdf = pdfium.PdfDocument(pdf_path)
    page_texts = []
    for page in pdf:
        textpage = page.get_textpage()
        page_texts.append(textpage.get_text_range())
    return "\n\n".join(page_texts), {"page_count": len(pdf)}


def run_backend(
    backend: Backend,
    image_path: str,
    *,
    prompt: str = "Extract the text content from this document. Output plain text only.",
    model: str | None = None,
    timeout_seconds: float = 30.0,
) -> tuple[str, dict[str, Any]]:
    """Call `backend` directly, bypassing the capability dispatch table.

    Used by `gemini_hackathon.ocr_ensemble` (Phase 5's 4-path consensus
    extractor), which needs to run all 4 backends against the SAME page —
    something the 1:1 capability->backend `_DISPATCH_TABLE` can't express.
    Raises `CapabilityUnavailableError` if the backend is unconfigured.
    """
    default_models = {
        Backend.DOCUMENT_AI: "LAYOUT_PARSER_PROCESSOR",
        Backend.GEMINI_VISION: "gemini-3.5-flash",
        Backend.GEMMA_VERTEX: "gemma-4-26b-a4b",
        Backend.PYPDFIUM2_TEXTLAYER: "textlayer",
    }
    resolved_model = model or default_models[backend]

    if backend == Backend.DOCUMENT_AI:
        return _call_document_ai(image_path, resolved_model, timeout_seconds)
    if backend == Backend.GEMINI_VISION:
        return _call_gemini_vision(image_path, prompt, resolved_model, timeout_seconds)
    if backend == Backend.GEMMA_VERTEX:
        return _call_gemma_vertex(image_path, prompt, timeout_seconds)
    if backend == Backend.PYPDFIUM2_TEXTLAYER:
        return _call_pypdfium2_textlayer(image_path)
    raise CapabilityUnavailableError(f"Unknown backend {backend}")  # pragma: no cover - exhaustive


def ocr(request: OcrRequest) -> OcrResult:
    """Dispatch `request` to its capability's GCP-native backend."""
    backend, default_model = _DISPATCH_TABLE[request.capability]
    model = request.model or default_model
    prompt = _prompt_for(request.capability, request.language_hint)

    start = time.monotonic()
    if backend == Backend.DOCUMENT_AI:
        text, extras = _call_document_ai(request.image_path, model, request.timeout_seconds)
    elif backend == Backend.GEMINI_VISION:
        text, extras = _call_gemini_vision(request.image_path, prompt, model, request.timeout_seconds)
    elif backend == Backend.GEMMA_VERTEX:
        text, extras = _call_gemma_vertex(request.image_path, prompt, request.timeout_seconds)
    elif backend == Backend.PYPDFIUM2_TEXTLAYER:
        text, extras = _call_pypdfium2_textlayer(request.image_path)
    else:  # pragma: no cover - exhaustive over Backend
        raise CapabilityUnavailableError(f"Unknown backend {backend}")
    duration_ms = int((time.monotonic() - start) * 1000)

    return OcrResult(
        capability=request.capability,
        backend=backend,
        model=model,
        text=text,
        duration_ms=duration_ms,
        pages_processed=1,
        extras=extras,
    )


def auto_capability(pdf_path: str) -> Capability:
    """Best-effort capability heuristic for a PDF path."""
    name = pdf_path.lower()
    if any(token in name for token in ("gaeilge", "irish", "gaelic", "cymraeg", "welsh", "gaidhlig")):
        return Capability.GAELIC
    return Capability.ENGLISH


__all__ = [
    "_DISPATCH_TABLE",
    "Backend",
    "Capability",
    "CapabilityUnavailableError",
    "OcrRequest",
    "OcrResult",
    "_render_pdf_pages_to_pngs",
    "auto_capability",
    "extract_pdf_text",
    "is_backend_available",
    "ocr",
    "run_backend",
]


# ---------------------------------------------------------------------------
# PDF text extraction (renders each page, then OCRs each via the router —
# except PYPDFIUM2_TEXTLAYER, which reads the PDF's embedded text layer
# directly and skips rendering entirely).
# ---------------------------------------------------------------------------


def _render_pdf_pages_to_pngs(
    pdf_path: str, output_dir: str | None = None, dpi: int = 150,
    max_pages: int = 200,
) -> list[str]:
    """Render each page of a PDF to a PNG. Returns the list of PNG paths.

    Uses pypdfium2 (preferred, MIT licensed) and falls back to pymupdf.
    Files are written to <output_dir> or a tempdir.
    """
    Path(pdf_path).resolve()  # sanity check
    import tempfile
    out_dir = Path(output_dir) if output_dir else Path(tempfile.mkdtemp(prefix="ocr-pages-"))
    out_dir.mkdir(parents=True, exist_ok=True)

    # Try pypdfium2 first.
    try:
        import pypdfium2 as pdfium  # type: ignore[import-not-found]
        pdf = pdfium.PdfDocument(pdf_path)
        scale = dpi / 72.0
        png_paths: list[str] = []
        total = len(pdf)
        cap = min(total, max_pages) if max_pages and max_pages > 0 else total
        for i in range(cap):
            page = pdf[i]
            img = page.render(scale=scale).to_pil()
            p = out_dir / f"page-{i+1:04d}.png"
            img.save(p, format="PNG")
            png_paths.append(str(p))
        return png_paths
    except ImportError:
        pass

    # Fallback: pymupdf.
    try:
        import fitz  # type: ignore[import-not-found]
        doc = fitz.open(pdf_path)
        png_paths = []
        total = doc.page_count
        cap = min(total, max_pages) if max_pages and max_pages > 0 else total
        for i in range(cap):
            page = doc[i]
            pix = page.get_pixmap(dpi=dpi)
            p = out_dir / f"page-{i+1:04d}.png"
            pix.save(str(p))
            png_paths.append(str(p))
        return png_paths
    except ImportError as exc:
        raise RuntimeError(
            "Need pypdfium2 or pymupdf installed to render PDFs to PNGs. "
            "Add one to requirements.txt."
        ) from exc


def extract_pdf_text(
    pdf_path: str,
    *,
    capability: Capability | None = None,
    base_url: str | None = None,
    timeout_seconds: float = 60.0,
    max_pages: int = 200,
) -> dict[str, Any]:
    """Extract text from a PDF via its capability's GCP-native backend.

    Returns a dict with keys: text (concatenated), page_count,
    duration_ms, backend, model, capability. Raises
    CapabilityUnavailableError if the backend is unconfigured.

    `base_url` is accepted for backward API compatibility with the
    pre-refactor signature but is unused (no GCP backend here takes a
    base URL override).

    Args:
        pdf_path: Source PDF.
        capability: Override the auto-detected capability.
        base_url: Unused (kept for signature compatibility).
        timeout_seconds: Per-call timeout.
        max_pages: Hard cap on pages processed.
    """
    del base_url  # unused — kept for backward-compatible call sites
    cap = capability or auto_capability(pdf_path)
    backend, default_model = _DISPATCH_TABLE[cap]

    start = time.monotonic()

    # Document AI + pypdfium2-textlayer both operate on the whole PDF
    # directly (no per-page rendering needed) — Document AI natively
    # accepts multi-page PDFs, and the text layer extractor reads the
    # embedded text without any image rendering at all.
    if backend == Backend.DOCUMENT_AI:
        text, extras = _call_document_ai(pdf_path, default_model, timeout_seconds)
        return {
            "text": text,
            "page_count": extras.get("page_count", 1),
            "duration_ms": int((time.monotonic() - start) * 1000),
            "backend": backend.value,
            "model": default_model,
            "capability": cap.value,
        }
    if backend == Backend.PYPDFIUM2_TEXTLAYER:
        text, extras = _call_pypdfium2_textlayer(pdf_path)
        return {
            "text": text,
            "page_count": extras.get("page_count", 1),
            "duration_ms": int((time.monotonic() - start) * 1000),
            "backend": backend.value,
            "model": default_model,
            "capability": cap.value,
        }

    # GEMINI_VISION / GEMMA_VERTEX: render each page to a PNG, OCR each.
    png_paths = _render_pdf_pages_to_pngs(pdf_path)
    if len(png_paths) > max_pages:
        png_paths = png_paths[:max_pages]

    page_texts: list[str] = []
    backend_used = ""
    model_used = ""
    for i, png in enumerate(png_paths):
        result = ocr(OcrRequest(
            capability=cap,
            image_path=png,
            timeout_seconds=timeout_seconds,
        ))
        page_texts.append(f"\n\n[Page {i+1}]\n{result.text}")
        backend_used = result.backend.value
        model_used = result.model

    return {
        "text": "".join(page_texts),
        "page_count": len(png_paths),
        "duration_ms": int((time.monotonic() - start) * 1000),
        "backend": backend_used,
        "model": model_used,
        "capability": cap.value,
    }
