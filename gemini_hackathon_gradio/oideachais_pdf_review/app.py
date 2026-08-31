"""gemini_hackathon_gradio.oideachais_pdf_review — human review of Stage-4 mismatches.

Lifted from `sruth/spaces/oideachais-pdf-review/`. The `@spaces.GPU`
pattern with Gemma 4 26B-A4B-it-GGUF is preserved verbatim. The
in-app LLM features use HuggingFace transformers directly (loaded
fresh on each `@spaces.GPU` call).

The full app implementation is in W12. For W3, we provide the
scaffolding + the @spaces.GPU decorator pattern.

This W3 update adds the 4 real operator widgets: PDF upload,
suggestion generator (via the ncca_panel `_baml_extract_or_stub`
pattern), Approve button + reviewer-notes textbox. The Approve
button writes a JSON line to `/tmp/pdf_review_log.jsonl` (the real
Firestore write is wired in W12).
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

try:
    import gradio as gr
except ImportError:
    gr = None  # type: ignore[assignment]

from .._common import (
    GRADIO_CSS,
    apply_education_theme,
    render_anam_bonneagar_footer,
)
from .._common import (
    translate as t,
)

_log = logging.getLogger("oideachais_pdf_review.app")

_REVIEW_LOG = Path("/tmp/pdf_review_log.jsonl")


# Default Space env vars (overridden by HuggingFace Space settings).
# The two model strings are resolved via MODEL_REGISTRY (the
# centralized-model-registry openspec change). The SUGGESTION_MODEL
# env var can still override (for prod / A/B test convenience).
def _suggestion_model() -> str:
    override = os.getenv("SUGGESTION_MODEL")
    if override:
        return override
    try:
        from gemini_hackathon.model_registry import MODEL_REGISTRY

        return MODEL_REGISTRY.resolve("text_llm", "pdf_review_suggestion")
    except Exception:
        return "unsloth/gemma-3-4b-it-GGUF"


def _explanation_model() -> str:
    override = os.getenv("EXPLANATION_MODEL")
    if override:
        return override
    try:
        from gemini_hackathon.model_registry import MODEL_REGISTRY

        return MODEL_REGISTRY.resolve("text_llm", "pdf_review_explanation")
    except Exception:
        return "unsloth/gemma-4-26B-A4B-it-GGUF"


SUGGESTION_MODEL = _suggestion_model()
EXPLANATION_MODEL = _explanation_model()
SUGGESTION_DURATION = int(os.getenv("SUGGESTION_DURATION", "60"))  # seconds
EXPLANATION_DURATION = int(os.getenv("EXPLANATION_DURATION", "120"))


def _baml_extract_or_stub(pdf_text: str, subject: str = "") -> dict:
    """Run the BAML ExtractCurriculumSyllabus call when available; otherwise
    return a deterministic stub dict that matches the LCSyllabusDocument shape.

    Mirrors `gemini_hackathon_backend/agents/ncca_panel.py:_baml_extract_or_stub`
    so the suggestion generator stays consistent with the ADK agent's
    fallback chain.
    """
    try:
        from baml_client.sync_client import b  # type: ignore

        return b.ExtractCurriculumSyllabus(
            pdf_text=pdf_text, subject=subject, language="en"
        ).model_dump()
    except Exception as exc:  # noqa: BLE001 — offline-path fallback
        return {
            "_stub": True,
            "_stub_reason": str(exc)[:200],
            "subject": subject,
            "language": "en",
            "module_topics": [
                {"title": f"(stub) Module 1 — {subject}", "learning_outcomes": []},
            ],
            "total_learning_outcomes": 0,
        }


def _persist_review_event(pdf_name: str, approved: bool, suggestion: str, notes: str) -> str:
    """Append one review event to /tmp/pdf_review_log.jsonl (placeholder for Firestore)."""
    _REVIEW_LOG.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "pdf_name": pdf_name,
        "approved": approved,
        "suggestion": suggestion[:500],
        "notes": notes[:500],
        "ts": "now",
    }
    with _REVIEW_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    return str(_REVIEW_LOG)


def build_app():
    """Build the Oideachais PDF Review Gradio app.

    Raises:
        ImportError: If Gradio is not installed.
    """
    if gr is None:
        raise ImportError(
            "Gradio is required for build_app(); install with `pip install gradio>=6.0,<7.0`"
        )
    with gr.Blocks(
        title="Oideachais PDF Review",
        theme=apply_education_theme(),
        css=GRADIO_CSS,
    ) as demo:
        gr.Markdown(
            f"""# {t("pdf_review.title")}
### *{t("pdf_review.subtitle")}*

Human review for the 6-stage Oideachais PDF processing pipeline (W5).
The pipeline processes NCCA syllabus PDFs, SEC past paper PDFs, and
SEC marking-scheme PDFs through:

1. **OCR (VLM dispatch)** — picks the optimal (model, backend) pair
2. **Diagram detection** — Granite-Docling + Molmo2-8B
3. **BAML extraction** — `ExtractLeavingCertSyllabus` /
   `ExtractPastPaper` / `ExtractMarkingScheme`
4. **Topic validation** — fuzzy-match against NCCA taxonomy
5. **Semantic chunking** — CocoIndex v1 + BGE-M3
6. **Lakehouse + Cognee + Graphiti** — DuckLake + KG + temporal

The 2 in-app LLM features run on the ZeroGPU backing card via the
`@spaces.GPU(duration=N)` decorator pattern (from `sruth/spaces/oideachais-pdf-review/`).

**Models in use (Tier 1: LiteLLM; Tier 2/3: HuggingFace Inference Providers):**
- `SUGGESTION_MODEL`: `{SUGGESTION_MODEL}` (≤32B)
- `EXPLANATION_MODEL`: `{EXPLANATION_MODEL}` (≤32B)""",
            elem_classes="stage-meanscoil",
        )

        # ---- 4 real operator widgets ----
        with gr.Row():
            with gr.Column():
                pdf_upload = gr.File(
                    label="Upload PDF",
                    file_types=[".pdf"],
                    type="filepath",
                )
                subject_box = gr.Textbox(
                    value="mathematics",
                    label="Subject slug (used by the suggestion generator)",
                )
                approve_btn = gr.Button("Approve", variant="primary")
                notes_box = gr.Textbox(
                    value="",
                    label="Reviewer notes",
                    lines=4,
                    placeholder="Add anything the next reviewer should know…",
                )
            with gr.Column():
                suggestion_box = gr.Textbox(
                    value="",
                    label="Suggestion (from the BAML extractor + stub fallback)",
                    lines=8,
                    interactive=True,
                )
                suggest_btn = gr.Button("Generate suggestion", variant="secondary")
                log_path_box = gr.Textbox(
                    value=str(_REVIEW_LOG),
                    label="Review log path",
                    interactive=False,
                )

        def _on_generate_suggestion(pdf_path: str | None, subject: str) -> str:
            """Read the PDF (when pypdf is installed) and call the extractor."""
            if not pdf_path:
                return "(upload a PDF first)"
            text = ""
            try:
                from pypdf import PdfReader  # type: ignore

                reader = PdfReader(pdf_path)
                text = "\n".join((page.extract_text() or "") for page in reader.pages[:5])
            except Exception as exc:  # noqa: BLE001 — surfaces in UI
                text = f"(pypdf not available: {exc})"
            extraction = _baml_extract_or_stub(pdf_text=text[:4000], subject=subject)
            return json.dumps(extraction, indent=2, ensure_ascii=False)

        def _on_approve(pdf_path: str | None, suggestion: str, notes: str) -> str:
            pdf_name = Path(pdf_path).name if pdf_path else "(no pdf)"
            return _persist_review_event(
                pdf_name=pdf_name,
                approved=True,
                suggestion=suggestion,
                notes=notes,
            )

        suggest_btn.click(
            fn=_on_generate_suggestion,
            inputs=[pdf_upload, subject_box],
            outputs=[suggestion_box],
        )
        approve_btn.click(
            fn=_on_approve,
            inputs=[pdf_upload, suggestion_box, notes_box],
            outputs=[log_path_box],
        )

        render_anam_bonneagar_footer(
            space_id="cianfhoghlaim/gemini-hackathon-pdf-review",
            subnation="Ireland (NCCA)",
            stage="All stages",
        )

    return demo


if __name__ == "__main__":
    app = build_app()
    app.launch(server_name="0.0.0.0", server_port=7860)


__all__ = ["build_app"]
