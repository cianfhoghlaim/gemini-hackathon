"""Build a stub HF Space for a given stage.

Each HF Space directory under `hf_spaces/gemini_hackathon_<stage>/`
contains:
  - app.py          — the Gradio app source (this script generates it)
  - README.md       — the HF Space frontmatter (this script generates it)
  - requirements.txt — the pinned dependencies

This generator produces them consistently. Running this script after
edits to the studio ensures the deployed Spaces are in sync with the
canonical gemini_hackathon_gradio package.
"""

from __future__ import annotations

import argparse
import textwrap
from pathlib import Path


# The 5 HF Spaces — (name, stage, title, emoji, color_from, color_to, sdk_version)
HF_SPACES: list[dict] = [
    {
        "name": "gemini_hackathon_aistear",
        "stage": "aistear",
        "title": "Aistear — Early Years (0-6)",
        "emoji": "👶",
        "color_from": "orange",
        "color_to": "amber",
        "description": "Aistear framework for ages 0-6 — play-based learning, 4 themes (wellbeing / identity / communicating / exploring).",
    },
    {
        "name": "gemini_hackathon_bunscoil",
        "stage": "bunscoil",
        "title": "Bunscoil — Primary (4-12)",
        "emoji": "📚",
        "color_from": "blue",
        "color_to": "indigo",
        "description": "Bunscoil (Primary) curriculum — 12 NCCA areas, friendly typography, the canonical heatmap studio.",
    },
    {
        "name": "gemini_hackathon_junior_cycle",
        "stage": "junior_cycle",
        "title": "MeanScoil — Junior Cycle (12-15)",
        "emoji": "🏫",
        "color_from": "green",
        "color_to": "emerald",
        "description": "MeanScoil (Junior Cycle) — 18 NCCA subjects + 16 short courses + 36 CBAs. The formative exit-card studio + CBA descriptors.",
    },
    {
        "name": "gemini_hackathon_leaving_certificate",
        "stage": "leaving_certificate",
        "title": "Scoil Sinsearach — Leaving Certificate (15-19)",
        "emoji": "🎓",
        "color_from": "orange",
        "color_to": "yellow",
        "description": "Scoil Sinsearach (Senior Cycle / Leaving Certificate) — the headline stage. 14 NCCA LC subjects, the LC certificate pipeline, the levy of formative assessment exit cards + the 5 NCCA Key Competencies fan-out.",
    },
    {
        "name": "gemini_hackathon_editorial_studio",
        "stage": "editorial_studio",
        "title": "Editorial Studio — British Isles Education Workflow Canvas",
        "emoji": "🧑‍🎓",
        "color_from": "indigo",
        "color_to": "purple",
        "description": "The full editorial studio — the LC/JC certificate pipeline as a drag-and-drop workflow canvas. The showcase of the gemini_hackathon platform.",
    },
]


REQUIREMENTS = textwrap.dedent("""\
    gradio>=5.28.0,<6.0
    google-adk>=2.7.1,<3.0
    pydantic>=2.0
    huggingface_hub>=0.30
""").strip()


def build_app_py(space: dict) -> str:
    """Generate the app.py for a given Space."""
    return textwrap.dedent(f'''\
        """
        {space["title"]} — the gemini_hackathon HF Space.

        Headline surface for the {space["stage"]} stage of the
        British Isles Education Platform. The full editorial studio
        runs on Cloud Run (see `gemini_hackathon_gradio/editorial_studio/deploy.py`)
        — this Space is the smaller, shareable entry point.
        """

        from __future__ import annotations

        import logging
        import os

        import gradio as gr

        _log = logging.getLogger(__name__)


        def build_app():
            """Build the {space["stage"]} Gradio app."""
            return gr.Blocks(
                title="{space["title"]}",
                theme=gr.themes.Soft(primary_hue="{space["color_from"]}", secondary_hue="{space["color_to"]}"),
            ) as demo:
                gr.Markdown("# {space["title"]}")
                gr.Markdown("{space["description"]}")
                # The actual implementation lives in
                # `gemini_hackathon_gradio/editorial_studio/app.py`
                # (the canonical editorial canvas). This Space re-exports
                # the relevant tab for the {space["stage"]} stage.
                # Lazy-import to avoid forcing the dependency on the
                # full gemini_hackathon_gradio package at startup.
                try:
                    from gemini_hackathon_gradio import build_editorial_studio_app
                    editor = build_editorial_studio_app()
                    gr.Markdown("## Editorial Studio preview")
                    gr.Markdown(editor.__doc__ or "Editorial Studio (preview).")
                except ImportError as e:
                    _log.warning("Could not load full editorial studio: %s", e)
                    gr.Markdown("(Install gemini_hackathon_gradio to enable the full editorial canvas.)")

                return demo


        if __name__ == "__main__":
            app = build_app()
            app.launch(server_name="0.0.0.0", server_port=7860)
    ''').strip()


def build_readme_md(space: dict) -> str:
    """Generate the README.md (HF frontmatter + description)."""
    return textwrap.dedent(f'''\
        ---
        title: "{space["title"]}"
        emoji: "{space["emoji"]}"
        colorFrom: "{space["color_from"]}"
        colorTo: "{space["color_to"]}"
        sdk: gradio
        sdk_version: 5.28.0
        app_file: app.py
        pinned: false
        license: mit
        short_description: "{space["description"][:120]}"
        ---

        # {space["title"]}

        > **gemini_hackathon** — the British Isles Education Platform.
        > One of the 5 editorial studios that ship for the All Things
        > Agentic 2026 hackathon (the headline surfaces are the 5 HF Spaces).

        See [`gemini_hackathon_gradio/editorial_studio/`](https://github.com/cianfhoghlaim/gemini_hackathon)
        for the full editorial canvas.

        The 5 Spaces:
          1. `gemini_hackathon_aistear` (Aistear, 0-6)
          2. `gemini_hackathon_bunscoil` (Bunscoil, 4-12)
          3. `gemini_hackathon_junior_cycle` (MeanScoil, 12-15)
          4. `gemini_hackathon_leaving_certificate` (Scoil Sinsearach, 15-19) ← the headline
          5. `gemini_hackathon_editorial_studio` (the big canvas)

        Stage: **{space["stage"]}**.
        Title: **{space["title"]}**.
    ''').strip()


def build_space(space: dict, hf_spaces_dir: Path) -> None:
    """Generate one HF Space directory."""
    space_dir = hf_spaces_dir / space["name"]
    space_dir.mkdir(parents=True, exist_ok=True)

    (space_dir / "app.py").write_text(build_app_py(space), encoding="utf-8")
    (space_dir / "README.md").write_text(build_readme_md(space), encoding="utf-8")
    (space_dir / "requirements.txt").write_text(REQUIREMENTS, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Generate gemini_hackathon HF Spaces")
    parser.add_argument("--hf-spaces-dir", default="hf_spaces", help="Root directory for the 5 Spaces")
    args = parser.parse_args()

    hf_spaces_dir = Path(args.hf_spaces_dir).resolve()
    hf_spaces_dir.mkdir(parents=True, exist_ok=True)

    for space in HF_SPACES:
        build_space(space, hf_spaces_dir)
        print(f"  built {space['name']}/")

    print(f"\nBuilt {len(HF_SPACES)} Spaces in {hf_spaces_dir}/")


if __name__ == "__main__":
    main()
