"""gemini_hackathon_gradio.oideachais_pdf_review — human review of Stage-4 mismatches.

Lifted from `sruth/spaces/oideachais-pdf-review/`. The `@spaces.GPU`
pattern with Gemma 4 26B-A4B-it-GGUF is preserved verbatim. The
in-app LLM features use HuggingFace transformers directly (loaded
fresh on each `@spaces.GPU` call).

The full app implementation is in W12. For W3, we provide the
scaffolding + the @spaces.GPU decorator pattern.
"""

from __future__ import annotations

import logging
import os

try:
    import gradio as gr
except ImportError:
    gr = None  # type: ignore[assignment]

from .._common import (
    GRADIO_CSS,
    apply_education_theme,
    render_anam_bonneagar_footer,
    translate as t,
)


_log = logging.getLogger("oideachais_pdf_review.app")


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


def build_app():
    """Build the Oideachais PDF Review Gradio app.

    Raises:
        ImportError: If Gradio is not installed.
    """
    if gr is None:
        raise ImportError(
            "Gradio is required for build_app(); install with `pip install gradio>=5.28.0,<6.0`"
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

        # Stub UI: real implementation is in W12.
        gr.Markdown(
            "_W3 scaffolding only. The full review interface (Approve / "
            "Reject / Correct / Notes / Export) lands in W12._"
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
