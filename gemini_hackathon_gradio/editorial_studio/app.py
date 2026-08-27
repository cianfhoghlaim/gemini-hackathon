"""gemini_hackathon_gradio.editorial_studio — the big British Isles Education Editorial Studio.

The headline Gradio host — the platform's surface that judges interact
with. Two layers combined:

  1. Monolithic Gradio Blocks — the 5-stage + 7-feature surface.
     Each stage + feature is wired to its corresponding ADK 2 workflow
     (W7) + data pipeline (W5) + Gradio feature module (W12).

  2. gr.Workflow graph canvas — the editor can drag nodes to compose
     the LC/JC certificate pipeline (W14) end-to-end. Per the
     `blog/gradio-workflow-guide.md` pattern (Image Editor / Media
     Studio / Generative Art Lab / Data Detective).

The studio runs as a single Cloud Run service per Workstream 12.
The HF Spaces (`cianfhoghlaim/gemini_hackathon_<stage>`, W13) are
smaller, per-stage surfaces.

This W3 file provides the scaffolding (the big gr.Blocks layout + the
gr.Workflow canvas + the 5-stage navigation). The full per-stage + per-
feature wiring is in W12.
"""

from __future__ import annotations

import logging

try:
    import gradio as gr
except ImportError:
    gr = None  # type: ignore[assignment]

from .._common import (
    GRADIO_CSS,
    apply_education_theme,
    render_anam_bonneagar_footer,
    set_lang,
    translate as t,
)


_log = logging.getLogger("editorial_studio.app")
set_lang("en")


def build_workflow_canvas():
    """Build the gr.Workflow canvas for the LC/JC certificate pipeline.

    Mirrors the `blog/gradio-workflow-guide.md` Image Editor pattern.
    Nodes:

      1. extract_syllabus     — BAML → typed SyllabusDocument
      2. decompose_outcomes   — BAML → DecomposerOutput (Pillar 3 dynamic)
      3. extract_exam_paper   — BAML → ExamPaper, Question, QuestionSection
      4. extract_marking      — BAML → MarkingScheme, MarkAllocation
      5. search_official      — RAG over the 5 NCCA PDFs (W2)
      6. generate_certificate — Flux background + PIL compositing (W14)
      7. save_to_provenance   — LanceDB + Convex (W9)

    Each node becomes an MCP tool when the workflow is launched
    (`gr.mcp.start(workflow.app)` per Workstream 12).

    Raises:
        ImportError: If Gradio is not installed.
    """
    if gr is None:
        raise ImportError(
            "Gradio is required for build_workflow_canvas(); install with "
            "`pip install gradio>=5.28.0,<6.0`"
        )
    from .._common.baml_client import chat_complete
    from .._common.i18n import set_lang as _set

    _set("en")

    def extract_syllabus(learner_id: str, subject_slug: str) -> str:
        """Stage 1 — extract the LC/JC syllabus structure for the given subject.

        Returns a typed SyllabusDocument record (the BAML extraction).
        """
        return (
            f"[extract_syllabus] learner={learner_id} subject={subject_slug} "
            f"-> SyllabusDocument (BAML extraction deferred to W7)"
        )

    def decompose_outcomes(syllabus_doc: str) -> list[str]:
        """Stage 2 — decompose the syllabus into learning outcomes (Pillar 3 dynamic)."""
        return [f"[decompose_outcomes] {s[:60]}..." for s in [syllabus_doc][:3]]

    def extract_exam_paper(syllabus_doc: str, year: int) -> str:
        """Stage 3 — extract an exam paper for the given syllabus + year."""
        return f"[extract_exam_paper] {syllabus_doc[:40]} year={year} -> ExamPaper"

    def extract_marking(exam_paper: str) -> str:
        """Stage 4 — extract the marking scheme for the given exam paper."""
        return f"[extract_marking] {exam_paper[:40]} -> MarkingScheme"

    def search_official(query: str, policy_pdf: str = "all") -> list[str]:
        """Stage 5 — RAG over the 5 NCCA policy PDFs (W2 corpus)."""
        return [
            f"[search_official] query={query[:40]} pdf={policy_pdf} -> citation: SC-L1-L2, p.12",
            f"[search_official] query={query[:40]} pdf={policy_pdf} -> citation: key-competencies, p.7",
        ]

    def generate_certificate(
        syllabus_doc: str,
        outcomes: list[str],
        exam_paper: str,
        marking: str,
        citations: list[str],
        learner_name: str = "Maya O'Brien",
    ) -> str:
        """Stage 6 — generate the LC/JC certificate (W14).

        Renders the Flux background + PIL compositing + provenance footer.
        """
        return (
            f"[generate_certificate] learner={learner_name} "
            f"subject_syllabus={syllabus_doc[:30]} "
            f"outcomes={len(outcomes)} exam={exam_paper[:30]} "
            f"citations={len(citations)} -> /tmp/certificates/{learner_name}.png"
        )

    def save_to_provenance(certificate_path: str, learner_id: str) -> str:
        """Stage 7 — save the certificate to the skill-progression ledger (W9)."""
        return (
            f"[save_to_provenance] {certificate_path} learner={learner_id} "
            f"-> Convex + LanceDB mastery vector + FalkorDB skill graph"
        )

    return gr.Workflow(
        bind=[
            extract_syllabus,
            decompose_outcomes,
            extract_exam_paper,
            extract_marking,
            search_official,
            generate_certificate,
            save_to_provenance,
        ],
        title="LC/JC Certificate Pipeline",
        description=(
            "End-to-end LC/JC certificate generation: extract → decompose → "
            "extract exam → extract marking → RAG over 5 NCCA PDFs → generate → save."
        ),
    )


def build_app():
    """Build the editorial studio — the big Gradio host.

    Raises:
        ImportError: If Gradio is not installed.
    """
    if gr is None:
        raise ImportError(
            "Gradio is required for build_app(); install with "
            "`pip install gradio>=5.28.0,<6.0`"
        )
    with gr.Blocks(
        theme=apply_education_theme(),
        css=GRADIO_CSS,
        title="gemini_hackathon — Editorial Studio",
    ) as demo:
        gr.Markdown(
            f"""# {t("editorial_studio.title")}
### *{t("editorial_studio.subtitle")}*

The British Isles Education Platform. 5 stages (Aistear → Bunscoil →
MeanScoil → Scoil Sinsearach → Ollscoil) × 6 subnations (Ireland →
England → NI → Wales → Scotland → IoM, with the latter 4 as Phase 2) ×
the 7-feature integration studio.

The studio runs on Cloud Run (W12) with `gr.Workflow` canvases per
stage and `gr.mcp.start` exposing every operator as an MCP tool. The
LC/JC certificate pipeline (W14) is the showcase — drag nodes to
compose the certificate end-to-end.""",
            elem_classes="stage-scoil-sinsearach",
        )

        with gr.Tabs():
            with gr.Tab("Aistear", elem_classes="stage-aistear"):
                gr.Markdown("_Early Childhood (0-6). Wired in W12._")

            with gr.Tab("Bunscoil (Primary)", elem_classes="stage-bunscoil"):
                gr.Markdown("_Primary (4-12). 12 NCCA areas. Wired in W12._")

            with gr.Tab("MeanScoil (Junior Cycle)", elem_classes="stage-meanscoil"):
                gr.Markdown(
                    "_Junior Cycle (12-15). 18 NCCA subjects + 16 short "
                    "courses + 36 CBAs. Wired in W12._"
                )

            with gr.Tab("Scoil Sinsearach (LC)", elem_classes="stage-scoil-sinsearach"):
                gr.Markdown(
                    "_Senior Cycle / Leaving Certificate (15-19). 14 NCCA "
                    "subjects + the 5 NCCA policy PDFs (W2) + the LC/JC "
                    "certificate pipeline (W14)._"
                )

                # Embed the gr.Workflow canvas for the LC certificate pipeline.
                # In W12 this is a real interactive surface; for W3 it's a
                # placeholder that documents the contract.
                with gr.Group():
                    gr.Markdown(
                        "**LC/JC Certificate Pipeline (W14 — showcase):**\n\n"
                        "```\n"
                        "extract_syllabus → decompose_outcomes → "
                        "extract_exam_paper → extract_marking → "
                        "search_official (RAG over 5 NCCA PDFs) → "
                        "generate_certificate (Flux + PIL) → "
                        "save_to_provenance (Convex + LanceDB + FalkorDB)\n"
                        "```"
                    )

            with gr.Tab("Ollscoil (Tertiary)", elem_classes="stage-ollscoil"):
                gr.Markdown("_Tertiary — Phase 2 (UoG + 5 programmes)._")

        render_anam_bonneagar_footer(
            space_id="cianfhoghlaim/gemini-hackathon-editorial-studio",
            subnation="Ireland (NCCA)",
            stage="All stages",
        )

    return demo


if __name__ == "__main__":
    app = build_app()
    app.launch(server_name="0.0.0.0", server_port=7860)


__all__ = ["build_app", "build_workflow_canvas"]
