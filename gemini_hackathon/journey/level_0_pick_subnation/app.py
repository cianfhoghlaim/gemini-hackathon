"""Level 0: Pick your subnation — the codelab body.

The structure mirrors `docs/adk-examples/way-back-home/level_0/create_identity.py`
(one entrypoint function with `#REPLACE-*` markers a workshop participant
fills in) but the implementation re-anchors on the gemini-hackathon
Firestore schema (Phase 6) + the existing `gemini_hackathon.theming`
palette registry.

The 3 `#REPLACE` markers a participant fills in:

    REPLACE-1: the Firestore `client.collection(...).document(uid).set(...)` call (1-3 lines)
    REPLACE-2: the gemini_hackathon.theming palette-application call (1 line)
    REPLACE-3: the participant's display_name string (1 line)

The codelab doc walks them through it: docs/journey/01_level_0_pick_subnation.md
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import sys
from typing import Any

try:
    import gradio as gr  # type: ignore[import-not-found]

    GRADIO_AVAILABLE = True
except ImportError:
    gr = None  # type: ignore[assignment]
    GRADIO_AVAILABLE = False

# Canonical subnation table — must stay in lockstep with
# gemini_hackathon/session/schema.py:ActiveSubnation.
SUBNATIONS: tuple[tuple[str, str, str], ...] = (
    # (slug, display_name, palette_file)
    ("ireland", "Ireland (NCCA)", "ncca_palette.json"),
    ("england", "England (AQA + OCR + Pearson)", "aqa_palette.json"),
    ("northern_ireland", "Northern Ireland (CCEA)", "northern_ireland_palette.json"),
    ("scotland", "Scotland (SQA)", "scotland_palette.json"),
    ("wales", "Wales (WJEC)", "wales_palette.json"),
    ("jersey", "Jersey (States of Jersey)", "jersey_palette.json"),
    ("guernsey", "Guernsey (States of Guernsey)", "guernsey_palette.json"),
    ("isle_of_man", "Isle of Man (DESC)", "isle_of_man_palette.json"),
)


def _now_iso() -> str:
    return _dt.datetime.now(tz=_dt.UTC).isoformat(timespec="seconds")


def _get_firestore_client():
    """Lazy Firestore client (returns None in offline mode — the participant
    still gets a successful message because the in-memory map is the source
    of truth in dev)."""
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    if not project_id:
        return None
    try:
        from google.cloud import firestore

        database = os.environ.get("JOURNEY_FIRESTORE_DATABASE", "(default)")
        return firestore.Client(project=project_id, database=database)
    except ImportError:
        return None


def _build_learner_doc(
    learner_id: str,
    display_name: str,
    subnation: str,
    palette_file: str,
) -> dict[str, Any]:
    """Build the canonical learners/{uid} doc shape (Level 0 output)."""
    return {
        "learner_id": learner_id,
        "display_name": display_name,
        "subnation": subnation,
        "palette_file": palette_file,
        "active_subject": "mathematics",  # sensible default — Level 1 can override
        "current_level": "0",
        "progress": "010000",  # 0x01 = Level 0 complete
        "created_at": _now_iso(),
        "last_updated": _now_iso(),
        # The journey orchestrator (Stream C.3) reads these on every level transition
        "journey_event_code": os.environ.get("JOURNEY_EVENT_CODE", "biep-demo"),
    }


def _apply_palette(subnation: str) -> dict[str, Any]:
    """Apply the matching subnation palette (CSS variables for the Gradio theme).

    REPLACE-2: replace this stub with the actual `gemini_hackathon.theming`
    palette-application call. The stub returns the palette CSS variable
    names + values so the participant can SEE the palette is being picked
    up before they wire the real one in.
    """
    # The stub returns the palette CSS-var dict for the participant's UI;
    # the real implementation is exactly one line:
    #
    #     from gemini_hackathon.theming import apply_palette_for_subnation
    #     return apply_palette_for_subnation(subnation)
    return {
        "applied": True,
        "subnation": subnation,
        "_stub_note": "this is the stub — replace with gemini_hackathon.theming.apply_palette_for_subnation(subnation)",
    }


def write_learner_profile(
    learner_id: str,
    display_name: str,
    subnation: str,
) -> dict[str, Any]:
    """Level 0's main write path — called when the participant submits the form.

    REPLACE-1: replace this stub with the Firestore write call. The stub
    uses an in-memory map so the workshop works offline; the real
    implementation is exactly three lines:

        client = _get_firestore_client()
        if client is not None:
            doc = _build_learner_doc(...)
            client.collection("journeys").document(event_code).collection("participants").document(learner_id).set(doc)
            return doc
        # else: fall through to the in-memory stub below

    The codelab doc walks through it.
    """
    palette_file = next((p for s, _, p in SUBNATIONS if s == subnation), "ncca_palette.json")
    doc = _build_learner_doc(learner_id, display_name, subnation, palette_file)

    # ─── STUB WRITE (offline-dev fallback) ──────────────────────────────────
    if not hasattr(write_learner_profile, "_in_memory"):
        write_learner_profile._in_memory = {}  # type: ignore[attr-defined]
    write_learner_profile._in_memory[learner_id] = doc  # type: ignore[attr-defined]
    # ────────────────────────────────────────────────────────────────────────

    palette = _apply_palette(subnation)
    return {
        "learner_id": learner_id,
        "subnation": subnation,
        "palette_file": palette_file,
        "palette_applied": palette,
        "doc": doc,
        "offline_stub": _get_firestore_client() is None,
    }


def build_app() -> Any:
    """The Level 0 Gradio app — pick a subnation, see your palette.

    Returns a `gr.Blocks` when Gradio is available; returns None when the
    participant runs the workshop without Gradio installed (rare — Gradio is
    in `pyproject.toml`'s `dependencies`) so the codelab's `--checklist`
    path still imports cleanly.
    """
    if not GRADIO_AVAILABLE:
        print(
            "Level 0: gradio is not installed in this environment. "
            "Run `uv sync` (or `pip install gradio>=5.28.0`) and try again.",
            file=sys.stderr,
        )
        return None
    with gr.Blocks(title="British Isles Journey · Level 0: Pick your subnation") as demo:
        gr.Markdown(
            "# British Isles Journey · Level 0\n"
            "## Pick your subnation\n\n"
            "Choose the jurisdiction you teach in / learn in. The matching "
            "NCCA / AQA / SQA / WJEC / CCEA / DESC palette is applied to "
            "every level you'll see from now on."
        )

        with gr.Row():
            learner_id_in = gr.Textbox(
                label="Your email (also your learner_id)",
                placeholder="alice@school.ie",
            )
            display_name_in = gr.Textbox(
                label="Display name",
                # REPLACE-3: replace this stub with your real codelab answer.
                # The real implementation is one line — replace this whole
                # assignment with whatever string the participant enters
                # in the codelab, OR read it from `display_name_in` directly.
                placeholder="(REPLACE-3: enter your display name)",
                value="(REPLACE-3)",
            )

        subnation_in = gr.Dropdown(
            label="Subnation (jurisdiction)",
            choices=[s[1] for s in SUBNATIONS],
            value="Ireland (NCCA)",
        )

        submit = gr.Button("Onboard me →", variant="primary")
        out = gr.JSON(label="Result (Firestore doc + palette)")

        subnation_lookup = {display: slug for slug, display, _ in SUBNATIONS}

        submit.click(
            fn=lambda lid, dn, sub_display: write_learner_profile(
                learner_id=lid,
                display_name=dn,
                subnation=subnation_lookup[sub_display],
            ),
            inputs=[learner_id_in, display_name_in, subnation_in],
            outputs=out,
        )

    return demo  # type: ignore[return-value]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--share", action="store_true", help="Generate a public HF Spaces URL")
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument(
        "--checklist",
        action="store_true",
        help="Print the 3 REPLACE markers + their context, then exit (for the codelab to scan)",
    )
    args = parser.parse_args()

    if args.checklist:
        # The codelab doc references these by name — keep them stable.
        print(
            "REPLACE-1: write_learner_profile() — the Firestore client.collection(...).document(...).set(...) call"
        )
        print(
            "REPLACE-2: _apply_palette() — the gemini_hackathon.theming.apply_palette_for_subnation(subnation) call"
        )
        print("REPLACE-3: display_name_in placeholder — your real display name")
        return 0

    app = build_app()
    if app is None:
        return 1
    app.launch(server_name="0.0.0.0", server_port=args.port, share=args.share)
    return 0


if __name__ == "__main__":
    sys.exit(main())
