"""Level 2 Gradio app entrypoint (top-level workshop host)."""
from __future__ import annotations

import json

try:
    import gradio as gr  # type: ignore[import-not-found]
    GRADIO_AVAILABLE = True
except ImportError:
    gr = None  # type: ignore[assignment]
    GRADIO_AVAILABLE = False

from gemini_hackathon.journey.level_2_past_paper_ocr import run_level_2


def _run(pdf_path: str):
    import asyncio
    r = asyncio.run(run_level_2(pdf_path=pdf_path))
    return (
        json.dumps([{"path": p["path"], "len": len(p.get("text", "")), "error": p.get("error")} for p in r.paths], indent=2),
        f"{r.voted_path}  (consensus: {r.consensus_score:.2f})" if r.voted_path else "(no consensus — all paths failed)",
        r.voted_text[:6000],
        "\n".join(r.ncca_policy_citations) or "(none — every path returned empty)",
    )


def build_app():
    if not GRADIO_AVAILABLE:
        return None
    with gr.Blocks(title="British Isles Journey · Level 2: Past-paper OCR") as demo:
        gr.Markdown(
            "# Level 2: Past-paper OCR\n"
            "4-path GCP-native ensemble (Document AI + Gemini Vision + Gemma Vertex + "
            "pypdfium2) runs in parallel; pairwise-Jaccard consensus vote picks the winner. "
            "Leave the input empty in offline mode."
        )
        pdf_in = gr.Textbox(label="PDF path (or empty for offline stub)", value="")
        run = gr.Button("Run the 4-path ensemble")
        with gr.Tab("Path results"):
            paths_out = gr.Code(label="Per-path output lengths", language="json")
        with gr.Tab("Consensus vote"):
            vote_out = gr.Textbox(label="Winning path + consensus score")
            citations_out = gr.Textbox(label="NCCA policy citations (or page refs)")
        with gr.Tab("Winning text"):
            text_out = gr.Markdown()
        run.click(fn=_run, inputs=pdf_in, outputs=[paths_out, vote_out, text_out, citations_out])
    return demo


def main():
    app = build_app()
    if app is None:
        return 1
    app.launch(server_name="0.0.0.0", server_port=7862)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
