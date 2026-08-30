"""gemini_hackathon_gradio.an_learning_graph.generate_tab — upload PDF → BAML extract.

The Show Your Work surface — upload a syllabus PDF, run the per-subject
BAML extractor, and preview the generated row × column grid. The
extraction delegates to ``baml_extracts.learning_graph`` (the 6
per-subject functions in the canonical BAML contract).

When BAML isn't installed (offline dev / CI), the tab degrades to a
"structure preview" placeholder — the PDF is still parsed via
``cocoindex_flows.pdf._shared.extract_markdown`` so users can see the
text that would be sent to the LLM.
"""

from __future__ import annotations

import json
import logging
import pathlib
from typing import Any

try:
    import gradio as gr
except ImportError:
    gr = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


REPO_ROOT: pathlib.Path = pathlib.Path(__file__).resolve().parent.parent.parent.parent
EXTRACTED_GRAPHS_ROOT: pathlib.Path = REPO_ROOT / "data" / "bi_ep" / "learning_graphs"

EXTRACTOR_CHOICES: tuple[str, ...] = (
    "ExtractCSLearningGraph",
    "ExtractMathsLearningGraph",
    "ExtractEnglishLearningGraph",
    "ExtractGaeilgeLearningGraph",
    "ExtractChemistryLearningGraph",
    "ExtractGeographyLearningGraph",
)


def _baml_available() -> bool:
    try:
        from baml_client import b as _b  # type: ignore[import-not-found]  # noqa: F401
        return True
    except ImportError:
        return False


def _extract_pdf_text(file_path: str) -> str:
    """Read a PDF via the canonical Phase 2b pypdfium2 extractor."""
    try:
        from cocoindex_flows.pdf._shared import extract_markdown
        p = pathlib.Path(file_path)
        return extract_markdown(p.read_bytes())
    except Exception as exc:  # noqa: BLE001
        logger.warning("generate_tab: extract_markdown failed for %s: %s", file_path, exc)
        return ""


def _persist_extracted_graph(
    *,
    slug: str,
    extractor: str,
    payload: dict[str, Any],
) -> pathlib.Path:
    """Save the extracted graph payload to the canonical JSON path."""
    EXTRACTED_GRAPHS_ROOT.mkdir(parents=True, exist_ok=True)
    out = EXTRACTED_GRAPHS_ROOT / f"{slug}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def _on_generate(
    file_obj: Any,
    extractor: str,
    year_level: int,
) -> tuple[str, str, str]:
    """Gradio handler — upload PDF, run the extractor, return (markdown, preview, meta)."""
    if file_obj is None:
        return (
            "**No file uploaded.** Please upload a syllabus PDF.",
            "",
            "",
        )
    try:
        file_path = file_obj.name if hasattr(file_obj, "name") else str(file_obj)
    except Exception:
        file_path = str(file_obj)

    pdf_text = _extract_pdf_text(file_path)
    if not pdf_text:
        return (
            f"**PDF parse failed.** Check that `pypdfium2` is installed and the "
            f"file at `{file_path}` is a valid PDF.",
            "",
            "",
        )

    slug = f"upload_{extractor.lower()}_y{year_level}"

    if not _baml_available():
        # Offline / CI path — write a preview payload showing what would be sent.
        payload = {
            "id": slug,
            "extractor": extractor,
            "year_level": year_level,
            "source_pdf": file_path,
            "pdf_text_preview": pdf_text[:2000],
            "extracted_via": "stub_baml_unavailable",
            "generated_at": pathlib.Path(file_path).stat().st_mtime,
        }
        out = _persist_extracted_graph(slug=slug, extractor=extractor, payload=payload)
        return (
            f"### PDF text preview (first 2000 chars)\n\n```\n{pdf_text[:2000]}\n```",
            "_BAML client not available — falling back to text preview._\n\n"
            "Run `mise run baml:generate` and re-upload to trigger a real extraction.",
            f"**Saved stub to** `{out}` (BAML client unavailable).",
        )

    # Real BAML path
    try:
        from baml_client import b as _b
        if extractor == "ExtractCSLearningGraph":
            result = _b.ExtractCSLearningGraph(pdf_text=pdf_text, year_level=year_level)
        elif extractor == "ExtractMathsLearningGraph":
            result = _b.ExtractMathsLearningGraph(pdf_text=pdf_text, year_level=year_level)
        elif extractor == "ExtractEnglishLearningGraph":
            result = _b.ExtractEnglishLearningGraph(pdf_text=pdf_text, year_level=year_level)
        elif extractor == "ExtractGaeilgeLearningGraph":
            result = _b.ExtractGaeilgeLearningGraph(
                pdf_text=pdf_text, year_level=year_level, language="EN",
            )
        elif extractor == "ExtractChemistryLearningGraph":
            result = _b.ExtractChemistryLearningGraph(pdf_text=pdf_text, year_level=year_level)
        elif extractor == "ExtractGeographyLearningGraph":
            result = _b.ExtractGeographyLearningGraph(pdf_text=pdf_text, year_level=year_level)
        else:
            return (f"Unknown extractor: {extractor}", "", "")
        # result is a Pydantic BaseModel — dump to JSON-friendly dict
        try:
            payload = result.model_dump()
        except AttributeError:
            payload = result.dict()
        payload.setdefault("source_pdf", file_path)
        payload.setdefault("generated_at", "now")
        out = _persist_extracted_graph(slug=slug, extractor=extractor, payload=payload)
        preview_md = (
            f"### Extracted `{extractor}` graph\n\n"
            f"- rows: {len(payload.get('base', payload).get('rows', []))}\n"
            f"- columns: {len(payload.get('base', payload).get('columns', []))}\n"
            f"- cells: {len(payload.get('base', payload).get('cells', []))}\n"
        )
        return (
            f"### Raw JSON\n\n```json\n{json.dumps(payload, indent=2)[:2000]}\n```",
            preview_md,
            f"**Saved to** `{out}`.",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("generate_tab: BAML extract failed: %s", exc)
        return (
            f"**BAML extraction failed:** `{exc}`\n\n"
            "The PDF text is shown below for manual inspection.",
            f"```\n{pdf_text[:2000]}\n```",
            "",
        )


def build_generate_tab() -> None:
    """Build the Generate-from-PDF tab."""
    if gr is None:
        return

    gr.Markdown(
        "### Upload a syllabus PDF → run the per-subject BAML extractor\n\n"
        "Pick an extractor + a year level, upload a syllabus PDF, and the "
        "canonical `ExtractXLearningGraph` function will produce a structured "
        "row × column grid. When the BAML client isn't installed, the tab "
        "falls back to a text preview of the PDF."
    )
    with gr.Row():
        file_input = gr.File(
            label="Syllabus PDF (or .txt)",
            file_types=[".pdf", ".txt"],
            type="filepath",
        )
        extractor_dd = gr.Dropdown(
            label="Extractor (per-subject BAML function)",
            choices=list(EXTRACTOR_CHOICES),
            value="ExtractCSLearningGraph",
        )
        year_dd = gr.Dropdown(
            label="Year level",
            choices=[6, 7, 8, 9, 10, 11],
            value=8,
        )
    generate_btn = gr.Button("Run extractor", variant="primary")
    raw_out = gr.Markdown(label="Raw BAML output (JSON)")
    preview_out = gr.Markdown(label="Preview")
    meta_out = gr.Markdown(label="Status")
    generate_btn.click(
        fn=_on_generate,
        inputs=[file_input, extractor_dd, year_dd],
        outputs=[raw_out, preview_out, meta_out],
    )


__all__ = ["build_generate_tab"]
