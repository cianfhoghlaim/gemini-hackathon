"""gemini_hackathon_gradio.oideachais_pdf_review — human review of Stage-4 mismatches.

Lifted from `sruth/spaces/oideachais-pdf-review/`. The `@spaces.GPU`
pattern with Gemma 4 26B-A4B-it-GGUF is preserved verbatim. The
in-app LLM features use HuggingFace transformers directly (loaded
fresh on each `@spaces.GPU` call).

Phase 4 (the `2026-08-31-journey-gradio-polish-v1` openspec change)
restructured the studio from a single-column operator into a 3-tab
layout:

  1. **Upload** — `gr.File()` PDF upload + subject picker + "Review" button
  2. **Review** — the BAML extraction result (via the syllabus extractor)
  3. **Export** — the "Save to Firestore" button (placeholder for the
     W12 Firestore write — Phase 5)

The `@spaces.GPU` handler is registered when running on HF Spaces
(`SPACE_ID` env var is set); in non-Space mode the handler is a regular
function so the dev / CI path still works.
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

try:
    from gemini_hackathon.syllabus.baml_extractor import BAMLSyllabusExtractor
except ImportError as _baml_exc:
    # Phase 5 owns the baml_extracts / per_topic_schema wiring. Until
    # that's stable we tolerate the missing import and fall back to a
    # stub dict from `_baml_syllabus_extract()`.
    BAMLSyllabusExtractor = None  # type: ignore[assignment,misc]
    _BAML_IMPORT_ERROR = _baml_exc
else:
    _BAML_IMPORT_ERROR = None

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
_FIRESTORE_PLACEHOLDER = Path("/tmp/pdf_review_firestore.jsonl")

# HuggingFace Spaces sets `SPACE_ID` when the app runs in a Space.
# We use this to decide whether to register the `@spaces.GPU` handler.
_IS_HF_SPACE: bool = bool(os.getenv("SPACE_ID"))

# The `@spaces.GPU` import is conditional — the package is only
# available in the HF Space environment.
_spaces = None
if _IS_HF_SPACE:
    try:
        import spaces as _spaces  # type: ignore[import-not-found]
    except ImportError:
        _spaces = None


# Default Space env vars (overridden by HuggingFace Space settings).
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


def _baml_syllabus_extract(subject: str, language: str = "EN") -> dict:
    """Phase 4 polish — call the canonical `BAMLSyllabusExtractor`.

    Honours `BAML_TEST_MODE=true` for offline workshop demo. Falls back
    to a stub dict on any error (mirrors the `an_scrudu` pattern).
    """
    if BAMLSyllabusExtractor is None:
        return {
            "_stub": True,
            "_stub_reason": (
                f"BAML extractor import failed: {_BAML_IMPORT_ERROR}. "
                f"Phase 5 owns the baml_extracts / per_topic_schema wiring."
            ),
            "subject": subject,
            "language": language,
            "module_topics": [],
            "total_learning_outcomes": 0,
        }
    try:
        result = BAMLSyllabusExtractor().extract(
            subject=subject, level="scoil_sinsearach", language=language,
        )
    except Exception as exc:
        return {
            "_stub": True,
            "_stub_reason": f"extraction failed: {exc}",
            "subject": subject,
            "language": language,
            "module_topics": [],
            "total_learning_outcomes": 0,
        }
    if hasattr(result, "model_dump"):
        return result.model_dump()
    if hasattr(result, "__dict__"):
        d = dict(result.__dict__)
        return {
            "subject": d.get("subject"),
            "language": d.get("language"),
            "module_topics": d.get("module_topics", []),
            "total_learning_outcomes": d.get("total_learning_outcomes", 0),
            "extraction_method": getattr(result, "extraction_method", "baml"),
        }
    return {"_stub": True, "reason": f"unknown return type {type(result).__name__}"}


def _persist_review_event(
    pdf_name: str, approved: bool, suggestion: str, notes: str, log_path: Path = _REVIEW_LOG
) -> str:
    """Append one review event to `/tmp/pdf_review_log.jsonl` (Phase 4 polish).

    Args:
        pdf_name: The uploaded PDF's filename (or "(no pdf)").
        approved: Whether the reviewer approved the suggestion.
        suggestion: The extracted suggestion text (truncated to 500 chars).
        notes: The reviewer's notes (truncated to 500 chars).
        log_path: Override for the log path (default: `/tmp/pdf_review_log.jsonl`).

    Returns:
        The str path to the log file (so the UI can echo it back).
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "pdf_name": pdf_name,
        "approved": approved,
        "suggestion": suggestion[:500],
        "notes": notes[:500],
        "ts": "now",
    }
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    return str(log_path)


def _save_to_firestore_stub(
    pdf_name: str,
    extraction: dict,
    notes: str,
) -> str:
    """Phase 4 polish — the 'Save to Firestore' button handler.

    Writes the event to `/tmp/pdf_review_firestore.jsonl` (the real
    Firestore write lands in Phase 5). Returns the log path so the UI
    can echo it back to the reviewer.
    """
    _FIRESTORE_PLACEHOLDER.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "pdf_name": pdf_name,
        "extraction_summary": {
            "subject": extraction.get("subject"),
            "module_topic_count": len(extraction.get("module_topics", []) or []),
            "total_learning_outcomes": extraction.get("total_learning_outcomes", 0),
            "extraction_method": extraction.get("extraction_method", "baml"),
        },
        "notes": notes[:500],
        "ts": "now",
    }
    with _FIRESTORE_PLACEHOLDER.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    return str(_FIRESTORE_PLACEHOLDER)


def _gpu_handler_decorator():
    """Return the `@spaces.GPU` decorator when running on HF Spaces.

    Falls back to a no-op decorator in non-Space mode so the dev / CI
    path doesn't require the `spaces` package.
    """
    if _spaces is None:
        return lambda fn: fn
    return _spaces.GPU(duration=SUGGESTION_DURATION)


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


@_gpu_handler_decorator()
def _gpu_suggestion_handler(pdf_path: str | None, subject: str) -> str:
    """The `@spaces.GPU`-decorated handler (Phase 4 polish).

    In HF Spaces mode, this runs on the ZeroGPU backing card with the
    Gemma 4 26B-A4B-it-GGUF model. In non-Space mode, the decorator is
    a no-op (see `_gpu_handler_decorator`).
    """
    return _on_generate_suggestion(pdf_path, subject)


def build_app():
    """Build the Oideachais PDF Review Gradio app (3-tab layout).

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
3 tabs: **Upload** (PDF + subject picker) → **Review** (BAML extraction
via `BAMLSyllabusExtractor`) → **Export** (Save to Firestore).

The 2 in-app LLM features run on the ZeroGPU backing card via the
`@spaces.GPU(duration=N)` decorator pattern (from `sruth/spaces/oideachais-pdf-review/`).

**Models in use (Tier 1: LiteLLM; Tier 2/3: HuggingFace Inference Providers):**
- `SUGGESTION_MODEL`: `{SUGGESTION_MODEL}` (≤32B)
- `EXPLANATION_MODEL`: `{EXPLANATION_MODEL}` (≤32B)""",
            elem_classes="stage-meanscoil",
        )

        with gr.Tabs():
            # ---- Tab 1 — Upload ----
            with gr.Tab("Upload", elem_classes="stage-aistear"):
                gr.Markdown(
                    "**Upload a PDF + pick a subject.** The PDF is read "
                    "via `pypdf` (when installed) and the first 4000 chars "
                    "are passed to the BAML extractor."
                )
                pdf_upload = gr.File(
                    label="Upload PDF",
                    file_types=[".pdf"],
                    type="filepath",
                )
                subject_box = gr.Textbox(
                    value="mathematics",
                    label="Subject slug (used by the suggestion generator)",
                )
                notes_box = gr.Textbox(
                    value="",
                    label="Reviewer notes",
                    lines=4,
                    placeholder="Add anything the next reviewer should know…",
                )

            # ---- Tab 2 — Review ----
            with gr.Tab("Review", elem_classes="stage-scoil-sinsearach"):
                gr.Markdown(
                    "**Run the BAML syllabus extractor.** Honours "
                    "`BAML_TEST_MODE=true` so the workshop demo runs offline."
                )
                language_dropdown = gr.Dropdown(
                    choices=["EN", "GA"],
                    value="EN",
                    label="Language",
                )
                review_btn = gr.Button("Run BAML extraction", variant="primary")
                review_json = gr.JSON(label="ExtractedSyllabus (BAML or stub)")

                review_btn.click(
                    fn=_baml_syllabus_extract,
                    inputs=[subject_box, language_dropdown],
                    outputs=[review_json],
                )

            # ---- Tab 3 — Export ----
            with gr.Tab("Export", elem_classes="stage-ollscoil"):
                gr.Markdown(
                    "**Save the review event to Firestore.** Phase 4 ships "
                    "the placeholder JSONL write — the real Firestore "
                    "write lands in Phase 5."
                )
                approve_btn = gr.Button("Approve", variant="primary")
                save_btn = gr.Button("Save to Firestore", variant="secondary")
                log_path_box = gr.Textbox(
                    value=str(_REVIEW_LOG),
                    label="Review log path",
                    interactive=False,
                )
                firestore_path_box = gr.Textbox(
                    value=str(_FIRESTORE_PLACEHOLDER),
                    label="Firestore placeholder path",
                    interactive=False,
                )

                def _on_save_to_firestore(subject: str, notes: str) -> str:
                    extraction = _baml_syllabus_extract(subject=subject)
                    return _save_to_firestore_stub(
                        pdf_name=subject, extraction=extraction, notes=notes,
                    )

                approve_btn.click(
                    fn=lambda subj, notes: _on_approve(None, "", notes),
                    inputs=[subject_box, notes_box],
                    outputs=[log_path_box],
                )
                save_btn.click(
                    fn=_on_save_to_firestore,
                    inputs=[subject_box, notes_box],
                    outputs=[firestore_path_box],
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
