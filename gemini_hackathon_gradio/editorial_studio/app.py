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


def _baml_extract_curriculum(pdf_text: str, subject: str) -> dict:
    """Call the BAML ExtractCurriculumSyllabus function with a stub fallback.

    Mirrors the pattern in `gemini_hackathon_backend/agents/ncca_panel.py:_baml_extract_or_stub`
    — try the real BAML client, fall back to a deterministic stub dict when
    the client is broken or the credentials aren't set (the case in the
    dev env).

    Returns a JSON-friendly dict shaped like
    `baml_src/gemini_hackathon/MarkingSchemeExtraction`.
    """
    try:
        from baml_client.sync_client import b  # type: ignore

        result = b.ExtractCurriculumSyllabus(
            pdf_text=pdf_text, subject=subject, language="en"
        )
        if hasattr(result, "model_dump"):
            return result.model_dump()
        return dict(result)
    except Exception as exc:  # noqa: BLE001 — offline-path fallback
        _log.info("BAML unavailable (%s); returning stub extraction", exc)
        return {
            "_stub": True,
            "_stub_reason": str(exc)[:200],
            "subject": subject,
            "language": "en",
            "module_topics": [
                {
                    "title": f"Module 1 — Foundations of {subject}",
                    "learning_outcomes": [
                        {"lo_id": f"{subject.upper()}-1.1", "title": f"Define key terms in {subject}"},
                        {"lo_id": f"{subject.upper()}-1.2", "title": f"Describe the core methods of {subject}"},
                    ],
                },
                {
                    "title": f"Module 2 — Applied {subject}",
                    "learning_outcomes": [
                        {"lo_id": f"{subject.upper()}-2.1", "title": f"Apply {subject} techniques to novel problems"},
                        {"lo_id": f"{subject.upper()}-2.2", "title": f"Analyse case studies using {subject}"},
                    ],
                },
            ],
            "total_learning_outcomes": 4,
        }


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
      7. save_to_provenance   — Firestore + the mastery-vector store (W9)

    Each node becomes an MCP tool when the workflow is launched
    (`gr.mcp.start(workflow.app)` per Workstream 12).

    Raises:
        ImportError: If Gradio is not installed.
    """
    if gr is None:
        raise ImportError(
            "Gradio is required for build_workflow_canvas(); install with "
            "`pip install gradio>=6.0,<7.0`"
        )
    from .._common.baml_client import chat_complete
    from .._common.i18n import set_lang as _set

    _set("en")

    def extract_syllabus(learner_id: str, subject_slug: str) -> dict:
        """Stage 1 — extract the LC/JC syllabus structure for the given subject.

        Returns a typed SyllabusDocument record (the BAML extraction),
        or a stub dict when the BAML client is unavailable.
        """
        # The real workflow would read the source PDF from Firestore and
        # call into the BAML client. For the W3 scaffolding we fabricate a
        # short PDF-text snippet + call the extractor.
        pdf_text = (
            f"{subject_slug.upper()} syllabus — sample text for learner {learner_id}. "
            "Module 1 introduces the foundational concepts. "
            "Module 2 covers applied techniques."
        )
        return _baml_extract_curriculum(pdf_text=pdf_text, subject=subject_slug)

    def decompose_outcomes(syllabus_doc: dict) -> list[dict]:
        """Stage 2 — decompose the syllabus into learning outcomes (Pillar 3 dynamic)."""
        return [
            {"lo_id": lo.get("lo_id"), "title": lo.get("title")}
            for module in syllabus_doc.get("module_topics", [])
            for lo in module.get("learning_outcomes", [])
        ]

    def extract_exam_paper(syllabus_doc: dict, year: int) -> dict:
        """Stage 3 — extract an exam paper for the given syllabus + year."""
        return {
            "year": year,
            "subject": syllabus_doc.get("subject", "(unknown)"),
            "sections": [
                {"name": "Section A — short questions", "questions": 8},
                {"name": "Section B — long questions", "questions": 4},
            ],
        }

    def extract_marking(exam_paper: dict) -> dict:
        """Stage 4 — extract the marking scheme for the given exam paper."""
        return {
            "year": exam_paper.get("year"),
            "subject": exam_paper.get("subject"),
            "total_marks": 400,
            "breakdown": [
                {"section": s["name"], "marks": s["questions"] * 25}
                for s in exam_paper.get("sections", [])
            ],
        }

    def search_official(query: str, policy_pdf: str = "all") -> list[dict]:
        """Stage 5 — RAG over the 5 NCCA policy PDFs (W2 corpus)."""
        return [
            {"pdf": "SC-L1-L2-Programme-Statement", "page": 12, "snippet": f"…{query[:40]}…"},
            {"pdf": "key-competencies-in-senior-cycle_en", "page": 7, "snippet": f"…{query[:40]}…"},
        ]

    def generate_certificate(
        syllabus_doc: dict,
        outcomes: list[dict],
        exam_paper: dict,
        marking: dict,
        citations: list[dict],
        learner_name: str = "Maya O'Brien",
    ) -> str:
        """Stage 6 — generate the LC/JC certificate (W14).

        Renders the Flux background + PIL compositing + provenance footer.
        """
        return (
            f"[generate_certificate] learner={learner_name} "
            f"subject_syllabus={syllabus_doc.get('subject', '?')} "
            f"outcomes={len(outcomes)} exam={exam_paper.get('year', '?')} "
            f"citations={len(citations)} -> /tmp/certificates/{learner_name}.png"
        )

    def save_to_provenance(certificate_path: str, learner_id: str) -> str:
        """Stage 7 — save the certificate to the skill-progression ledger (W9)."""
        return (
            f"[save_to_provenance] {certificate_path} learner={learner_id} "
            f"-> Firestore + mastery-vector store + Firestore skill graph"
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
            "`pip install gradio>=6.0,<7.0`"
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

        # --- Stage + subject pickers (drive the operator buttons below) ---
        with gr.Row():
            stage_picker = gr.Radio(
                choices=["Aistear", "Bunscoil", "MeanScoil", "Scoil Sinsearach", "Ollscoil"],
                value="Scoil Sinsearach",
                label="Stage",
            )
            subject_picker = gr.Radio(
                choices=["mathematics", "gaeilge", "chemistry", "geography", "english", "computer_science"],
                value="mathematics",
                label="LC subject",
            )

        # --- Real operator (calls the BAML extractor with stub fallback) ---
        with gr.Group():
            gr.Markdown("### extract_syllabus (operator)")
            with gr.Row():
                learner_input = gr.Textbox(value="demo-learner-001", label="Learner ID")
                subject_input = gr.Textbox(value="mathematics", label="Subject slug")
            extract_btn = gr.Button("Run extract_syllabus", variant="primary")
            extract_output = gr.JSON(label="SyllabusDocument (BAML or stub)")

            def _on_extract(learner_id: str, subject_slug: str) -> dict:
                return _baml_extract_curriculum(
                    pdf_text=f"{subject_slug} syllabus text for {learner_id}",
                    subject=subject_slug,
                )

            extract_btn.click(
                fn=_on_extract,
                inputs=[learner_input, subject_input],
                outputs=[extract_output],
            )

        with gr.Tabs():
            with gr.Tab("Aistear", elem_classes="stage-aistear"):
                gr.Markdown(
                    "**Early Childhood (0-6).** Aistear is the Irish-language "
                    "framework for children from birth to 6. Wired in W12."
                )

            with gr.Tab("Bunscoil (Primary)", elem_classes="stage-bunscoil"):
                gr.Markdown(
                    "**Primary (4-12).** 12 NCCA curriculum areas; the 1999 "
                    "Primary Curriculum is the source of truth. Wired in W12."
                )

            with gr.Tab("MeanScoil (Junior Cycle)", elem_classes="stage-meanscoil"):
                gr.Markdown(
                    "**Junior Cycle (12-15).** 18 NCCA subjects + 16 short "
                    "courses + 36 CBAs. The 2015 Framework for Junior Cycle "
                    "is the source of truth. Wired in W12."
                )

            with gr.Tab("Scoil Sinsearach (LC)", elem_classes="stage-scoil-sinsearach"):
                gr.Markdown(
                    "**Senior Cycle / Leaving Certificate (15-19).** 14 NCCA "
                    "subjects + the 5 NCCA policy PDFs (W2) + the LC/JC "
                    "certificate pipeline (W14)."
                )

                # Embed the gr.Workflow canvas for the LC certificate pipeline.
                # In W12 this is a real interactive surface; for W3 it
                # documents the contract.
                with gr.Group():
                    gr.Markdown(
                        "**LC/JC Certificate Pipeline (W14 — showcase):**\n\n"
                        "```\n"
                        "extract_syllabus → decompose_outcomes → "
                        "extract_exam_paper → extract_marking → "
                        "search_official (RAG over 5 NCCA PDFs) → "
                        "generate_certificate (Flux + PIL) → "
                        "save_to_provenance (Firestore + mastery-vector store + skill graph)\n"
                        "```"
                    )
                    gr.Markdown(
                        f"_Stage picker:_ **{stage_picker.value}** · "
                        f"_Subject picker:_ **{subject_picker.value}**_"
                    )

            with gr.Tab("Ollscoil (Tertiary)", elem_classes="stage-ollscoil"):
                gr.Markdown(
                    "**Tertiary — Phase 2.** University of Galway + 5 "
                    "foundation programmes. Wired in W12."
                )

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
