"""app.py — Level 1 standalone Gradio launcher (per Way Back Home pattern)."""

from __future__ import annotations

import json

try:
    import gradio as gr  # type: ignore[import-not-found]

    GRADIO_AVAILABLE = True
except ImportError:
    gr = None  # type: ignore[assignment]
    GRADIO_AVAILABLE = False

from gemini_hackathon.journey.level_1_syllabus_extraction import run_level_1


def _run_pipeline(
    subnation: str,
    subject: str,
    language: str,
) -> tuple[str, str, str, str]:
    """Run Level 1 synchronously; return (syllabus_json, chunks_json, upserted_count, backend)."""
    result = run_level_1(subnation=subnation, subject=subject, language=language)
    return (
        json.dumps(result.syllabus, indent=2, default=str)[:6000],
        json.dumps(
            [{"chunk_id": c["chunk_id"], "text_preview": c["text"][:200]} for c in result.chunks],
            indent=2,
        )[:3000],
        str(result.upserted_count),
        result.vector_backend,
    )


def build_app():
    if not GRADIO_AVAILABLE:
        return None
    with gr.Blocks(title="British Isles Journey · Level 1: Syllabus extraction") as demo:
        gr.Markdown(
            "# Level 1: Extract the syllabus\n"
            "BAML `ExtractCurriculumSyllabus` -> Vertex AI embeddings -> Firestore "
            "`FindNearest`. The 4-node Workflow runs end-to-end and writes the "
            "subject's learning outcomes into your Vector Search index."
        )
        with gr.Row():
            subnation = gr.Dropdown(
                label="Subnation",
                choices=[
                    "ireland",
                    "england",
                    "northern_ireland",
                    "scotland",
                    "wales",
                    "jersey",
                    "guernsey",
                    "isle_of_man",
                ],
                value="ireland",
            )
            subject = gr.Dropdown(
                label="Subject",
                choices=[
                    "mathematics",
                    "applied_mathematics",
                    "chemistry",
                    "physics",
                    "biology",
                    "geography",
                    "english",
                    "gaeilge",
                    "french",
                    "history",
                    "business",
                    "accounting",
                    "art",
                    "music",
                    "computer_science",
                ],
                value="mathematics",
            )
            language = gr.Radio(["en", "ga"], value="en", label="Language")
        submit = gr.Button("Extract + embed + upsert")
        with gr.Tab("Syllabus (BAML)"):
            syllabus_out = gr.Code(label="LCSyllabusDocument JSON", language="json")
        with gr.Tab("Embedded chunks"):
            chunks_out = gr.Code(label="VectorTarget rows", language="json")
        with gr.Tab("Upsert summary"):
            count_out = gr.Textbox(label="rows written")
            backend_out = gr.Textbox(label="Vector backend")

        submit.click(
            fn=_run_pipeline,
            inputs=[subnation, subject, language],
            outputs=[syllabus_out, chunks_out, count_out, backend_out],
        )
    return demo


def main():
    app = build_app()
    if app is None:
        return 1
    app.launch(server_name="0.0.0.0", server_port=7861)
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
