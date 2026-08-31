"""gemini_hackathon_gradio.journey_studio — the unified 6-level Gradio studio.

Phase D.1 of the GCP-first British Isles Journey refactor. Surfaces all
6 levels of the Journey as one continuous Gradio app:
    Tab 1 (Level 0)  : Pick your subnation
    Tab 2 (Level 1)  : Extract the syllabus
    Tab 3 (Level 2)  : OCR a past paper (4-path consensus)
    Tab 4 (Level 3)  : Mark an answer (per-criterion graders)
    Tab 5 (Level 4)  : Update mastery ledger (4-backend fan-out)
    Tab 6 (Level 5)  : Generate an asset from a question (FIBO)
    + Admin tab      : workshop host's progress dashboard

Each tab calls directly into the corresponding `gemini_hackathon.journey.
level_N_*` module. The 6 levels run standalone; the unified studio here
is the convenience surface (per Way Back Home's `dashboard/frontend/`).

Run standalone:
    python -m gemini_hackathon_gradio.journey_studio.app
"""

from __future__ import annotations

import json

try:
    import gradio as gr  # type: ignore[import-not-found]

    GRADIO_AVAILABLE = True
except ImportError:
    gr = None  # type: ignore[assignment]
    GRADIO_AVAILABLE = False

from gemini_hackathon.journey.journey_orchestrator.workflow import run_full_journey
from gemini_hackathon.journey.level_0_pick_subnation.app import (
    SUBNATIONS as L0_SUBNATIONS,
)
from gemini_hackathon.journey.level_0_pick_subnation.app import (
    _apply_palette as l0_apply_palette,
)
from gemini_hackathon.journey.level_0_pick_subnation.app import (
    _build_learner_doc as l0_build_doc,
)
from gemini_hackathon.journey.level_0_pick_subnation.app import (
    write_learner_profile as l0_write,
)
from gemini_hackathon.journey.level_1_syllabus_extraction import run_level_1
from gemini_hackathon.journey.level_2_past_paper_ocr import run_level_2
from gemini_hackathon.journey.level_3_marking_scheme import run_level_3
from gemini_hackathon.journey.level_4_mastery_update import run_level_4
from gemini_hackathon.journey.level_5_asset_generation import run_level_5


def _pick_subnation(display_name: str) -> str:
    return next((slug for slug, display, _ in L0_SUBNATIONS if display == display_name), "ireland")


# ── Per-level sync wrappers (run the async levels in a fresh event loop)
def _sync(coro):
    """Run `coro` to completion in a fresh asyncio event loop.

    Gradio handlers run synchronously; the level entrypoints are async.
    `asyncio.run` from inside a running loop raises (`RuntimeError: cannot
    be called from a running event loop`); each handler creates its own
    loop instead — fine because Gradio's handler thread is its own thread.
    """
    import asyncio

    try:
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ── Tab 1: Level 0 ─────────────────────────────────────────────────────────
def level_0_submit(learner_id: str, display_name: str, subnation_display: str) -> dict:
    subnation = _pick_subnation(subnation_display)
    return l0_write(learner_id=learner_id, display_name=display_name, subnation=subnation)


# ── Tab 2: Level 1 ─────────────────────────────────────────────────────────
def level_1_run(subnation: str, subject: str, language: str) -> dict:
    r = _sync(run_level_1(subnation=subnation, subject=subject, language=language))
    return {
        "pdf_path": r.pdf_path,
        "total_learning_outcomes": r.syllabus.get("total_learning_outcomes"),
        "chunks_embedded": len(r.chunks),
        "vector_backend": r.vector_backend,
        "subject": subject,
    }


# ── Tab 3: Level 2 ─────────────────────────────────────────────────────────
def level_2_run(pdf_path: str) -> dict:
    r = _sync(run_level_2(pdf_path=pdf_path))
    return {
        "voted_path": r.voted_path,
        "consensus_score": r.consensus_score,
        "page_count": r.page_count,
        "ncca_policy_citations": r.ncca_policy_citations,
        "voted_text_preview": (r.voted_text or "")[:600],
    }


# ── Tab 4: Level 3 ─────────────────────────────────────────────────────────
def level_3_run(subject: str, question_id: str, student_answer: str) -> dict:
    r = _sync(run_level_3(subject=subject, question_id=question_id, student_answer=student_answer))
    return {
        "total_marks_awarded": r.total_marks_awarded,
        "total_max_marks": r.total_max_marks,
        "strategy_summary": r.strategy_summary,
        "ncca_policy_citations": r.ncca_policy_citations,
        "criterion_grades": [
            {
                "criterion_id": g["criterion_id"],
                "marks_awarded": g["marks_awarded"],
                "max_marks": g["max_marks"],
            }
            for g in r.criterion_grades
        ],
    }


# ── Tab 5: Level 4 ─────────────────────────────────────────────────────────
def level_4_run(
    learner_id: str, subject_slug: str, outcome_code: str, mastery_score: float
) -> dict:
    r = _sync(
        run_level_4(
            learner_id=learner_id,
            subject_slug=subject_slug,
            outcome_code=outcome_code,
            mastery_score=mastery_score,
        )
    )
    return {
        "per_backend_status": r.per_backend_status,
        "mastery_vector_dim": r.mastery_vector_dim,
        "skill_graph_edge_count": r.skill_graph_edge_count,
    }


# ── Tab 6: Level 5 ─────────────────────────────────────────────────────────
def level_5_run(user_question: str, subnation: str, subject: str) -> dict:
    r = _sync(run_level_5(user_question=user_question, subnation=subnation, subject=subject))
    return {
        "asset_local_path": r.asset_local_path,
        "storage_uri": r.storage_uri,
        "asset_bytes_size": r.asset_bytes_size,
        "generation_backend": r.generation_backend,
        "matched_outcomes": r.matched_outcomes,
    }


# ── "Run the whole journey" button ───────────────────────────────────────
def run_whole_journey(
    learner_id: str, subnation: str, subject: str, user_question: str, student_answer: str = ""
) -> dict:
    """One-click end-to-end: level 1 -> level 2 -> level 3 -> level 4 -> pause -> level 5."""
    state = {
        "learner_id": learner_id,
        "subnation": subnation,
        "subject": subject,
        "user_question": user_question,
        "student_answer": student_answer,
        "outcome_code": "MA-LC-MA-1.1",
        "mastery_score": 0.78,
    }

    class _FakeCtx:
        pass

    ctx = _FakeCtx()
    ctx.state = state
    out = _sync(run_full_journey(ctx))
    return {
        "level_1": out.level_1,
        "level_2": out.level_2,
        "level_3": out.level_3,
        "level_4": out.level_4,
        "request_human_confirmation": out.request_human_confirmation,
        "level_5": out.level_5,
        "all_ncca_citations": out.ncca_policy_citations,
        "asset_storage_uri": out.asset_storage_uri,
    }


# ── Gradio app ───────────────────────────────────────────────────────────


def _sync(coro):
    """Run an async coroutine to completion in a fresh event loop."""
    import asyncio

    try:
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _cop_status_md() -> str:
    """The SourcingCopilot's --status one-shot, rendered as Markdown."""
    import os

    os.environ.pop("GOOGLE_CLOUD_PROJECT", None)
    os.environ.pop("FIRESTORE_EMULATOR_HOST", None)
    from gemini_hackathon.journey.sourcing.pipeline import step_status

    counts = step_status(project_id=None)
    rows = "\n".join(
        f"| {k} | `{counts.get(k, '-')}` |"
        for k in [
            "catalog_rows_total",
            "sourced_ok",
            "sourced_fail",
            "excluded",
            "normalised",
            "baml_extracted",
            "ocr_consensus_done",
            "mastery_done",
            "asset_done",
            "ready",
        ]
    )
    body = f"### Sourcing pipeline status\n\n| key | count |\n|---|---|\n{rows}\n"
    # Recommendation
    s = counts.get("sourced_ok", 0) or 0
    n = counts.get("normalised", 0) or 0
    b = counts.get("baml_extracted", 0) or 0
    if s == 0:
        body += "\n**Recommendation:** run `python -m gemini_hackathon.journey.sourcing.pipeline --step=sourced`\n"
    elif n < s:
        body += f"\n**Recommendation:** run `--step=normalised` ({n}/{s} docs normalised)\n"
    elif b < n:
        body += f"\n**Recommendation:** run `--step=extract-baml` ({b}/{n} docs BAML-extracted)\n"
    else:
        body += "\n**Recommendation:** ready for Level 1 (the Journey orchestrator)\n"
    return body


def _cop_exclude_json(sha256: str, reason: str) -> dict:
    """The SourcingCopilot's --exclude one-shot, wrapped for the studio."""
    from gemini_hackathon.journey.sourcing_copilot.tools import mark_excluded

    return mark_excluded(sha256 or "no-sha-supplied", reason=reason)


def _cop_deploy_md() -> str:
    """The SourcingCopilot's recommendation + inventory, rendered as Markdown."""
    import os

    os.environ.pop("GOOGLE_CLOUD_PROJECT", None)
    os.environ.pop("FIRESTORE_EMULATOR_HOST", None)
    from gemini_hackathon.journey.sourcing_copilot.tools import (
        list_cloud_run_services,
        list_scheduled_jobs,
        recommend_next_steps,
    )

    rec = recommend_next_steps()
    body = f"### Recommended next step\n\n**{rec.get('recommendation', '?')}**\n\n"
    for r in rec.get("reasons", []):
        body += f"- {r}\n"
    body += "\n### Cloud Run services\n\n"
    for s in list_cloud_run_services():
        body += f"- `{s.get('metadata', {}).get('name', s.get('name', '?'))}` ({s.get('metadata', {}).get('region', s.get('region', '?'))})\n"
    body += "\n### Cloud Scheduler jobs\n\n"
    for j in list_scheduled_jobs():
        body += f"- `{j.get('name', '?')}` — `{j.get('schedule', '?')}`\n"
    return body


def build_app():
    if not GRADIO_AVAILABLE:
        return None
    with gr.Blocks(title="British Isles Journey · The Unified Studio") as demo:
        gr.Markdown(
            "# British Isles Journey\n"
            "## A 6-level immersive progressive educational experience\n\n"
            "Drive the official syllabus processing pipeline (BAML → Vertex "
            "embeddings → Document AI OCR → Firestore/Vector Search RAG → 4-path "
            "OCR consensus → MasteryLedger 4-backend fan-out → FIBO asset "
            "generation) across all 8 British Isles subnations."
        )

        with gr.Tab("Level 0 — Pick your subnation"):
            with gr.Row():
                l0_lid = gr.Textbox(label="learner_id (email)", placeholder="alice@school.ie")
                l0_dn = gr.Textbox(label="display_name")
                l0_sub = gr.Dropdown(
                    label="subnation",
                    choices=[d for _, d, _ in L0_SUBNATIONS],
                    value="Ireland (NCCA)",
                )
            l0_btn = gr.Button("Onboard")
            l0_out = gr.JSON(label="Result (Firestore doc + palette)")
            l0_btn.click(fn=level_0_submit, inputs=[l0_lid, l0_dn, l0_sub], outputs=l0_out)

        with gr.Tab("Level 1 — Syllabus extraction"):
            with gr.Row():
                l1_sub = gr.Dropdown(
                    label="subnation",
                    choices=[s for s, _, _ in L0_SUBNATIONS],
                    value="ireland",
                )
                l1_sbj = gr.Dropdown(
                    label="subject",
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
                l1_lang = gr.Radio(["en", "ga"], value="en", label="language")
            l1_btn = gr.Button("Extract + embed + upsert")
            l1_out = gr.JSON(label="Syllabus result")
            l1_btn.click(fn=level_1_run, inputs=[l1_sub, l1_sbj, l1_lang], outputs=l1_out)

        with gr.Tab("Level 2 — Past paper OCR"):
            l2_path = gr.Textbox(label="pdf_path (or empty for offline stub)", value="")
            l2_btn = gr.Button("Run the 4-path ensemble")
            l2_out = gr.JSON(label="Consensus result")
            l2_btn.click(fn=level_2_run, inputs=l2_path, outputs=l2_out)

        with gr.Tab("Level 3 — Mark an answer"):
            with gr.Row():
                l3_sbj = gr.Dropdown(
                    label="subject",
                    choices=["mathematics", "chemistry", "gaeilge", "english"],
                    value="mathematics",
                )
                l3_qid = gr.Textbox(label="question_id", value="Q5")
            l3_ans = gr.Textbox(
                label="student_answer",
                value="Using the sine rule: a/sin(A) = b/sin(B) = c/sin(C)",
                lines=4,
            )
            l3_btn = gr.Button("Mark")
            l3_out = gr.JSON(label="Grade result")
            l3_btn.click(fn=level_3_run, inputs=[l3_sbj, l3_qid, l3_ans], outputs=l3_out)

        with gr.Tab("Level 4 — Mastery update"):
            with gr.Row():
                l4_lid = gr.Textbox(label="learner_id", value="alice@school.ie")
                l4_sbj = gr.Dropdown(
                    label="subject_slug",
                    choices=["mathematics", "gaeilge", "english"],
                    value="mathematics",
                )
                l4_outc = gr.Textbox(label="outcome_code", value="MA-LC-MA-1.1")
            l4_score = gr.Slider(
                label="mastery_score", minimum=0.0, maximum=1.0, step=0.05, value=0.78
            )
            l4_btn = gr.Button("Update mastery")
            l4_out = gr.JSON(label="Per-backend status")
            l4_btn.click(fn=level_4_run, inputs=[l4_lid, l4_sbj, l4_outc, l4_score], outputs=l4_out)

        with gr.Tab("Level 5 — Asset generation"):
            l5_q = gr.Textbox(
                label="user_question (asset grounded in the syllabus)",
                value="Draw a labelled diagram of the sine rule for triangle ABC",
                lines=3,
            )
            with gr.Row():
                l5_sub = gr.Dropdown(
                    label="subnation", choices=[s for s, _, _ in L0_SUBNATIONS], value="ireland"
                )
                l5_sbj = gr.Dropdown(
                    label="subject",
                    choices=["mathematics", "chemistry", "gaeilge"],
                    value="mathematics",
                )
            l5_btn = gr.Button("Generate asset")
            l5_out = gr.JSON(label="Asset result")
            l5_img = gr.Image(label="Generated asset preview", visible=False)
            l5_btn.click(fn=level_5_run, inputs=[l5_q, l5_sub, l5_sbj], outputs=[l5_out, l5_img])

        # Stream S.6 — the SourcingCopilot tab. Same backends as the
        # pipeline + studio (journeys/{event_code}/content_artefacts/),
        # but exposed as a workshop-host-facing 3-tab surface: Status
        # (the 9-row table) / Exclude (paste a sha256) / Deploy (the
        # next-step recommendation + Cloud Run / Scheduler inventory).
        with gr.Tab("SourcingCopilot — interactive deploy guide"):
            gr.Markdown(
                "## The workshop host's sourcing-pipeline copilot\n\n"
                "Drive the official syllabus processing pipeline (Phase 2 of the GCP-first\n"
                "refactor). The 9-row status table below is the canonical view of what's\n"
                "been sourced, normalised, and ready for the BAML extraction step.\n\n"
                "Three tabs:\n\n"
                "  1. **Status** — live counts per step (sourced_ok / normalised / etc.)\n"
                "  2. **Exclude** — paste a sha256 + reason to mark a document out of scope\n"
                "  3. **Deploy** — the copilot's recommendation + Cloud Run / Scheduler inventory"
            )
            with gr.Tabs():
                with gr.Tab("Status (live counts)"):
                    cop_status_btn = gr.Button("Refresh status")
                    cop_status_out = gr.Code(
                        label="9-row status + recommendation", language="markdown"
                    )
                    cop_status_btn.click(fn=_cop_status_md, outputs=cop_status_out)
                with gr.Tab("Exclude a document"):
                    cop_ex_sha = gr.Textbox(
                        label="sha256 (paste from `list` below)", placeholder="e.g. abc123..."
                    )
                    cop_ex_reason = gr.Dropdown(
                        label="reason",
                        choices=[
                            "out_of_scope",
                            "corrupted",
                            "duplicate",
                            "superseded",
                            "language_unsupported",
                        ],
                        value="out_of_scope",
                    )
                    cop_ex_btn = gr.Button("Mark excluded")
                    cop_ex_out = gr.JSON(label="Result + next 10 candidates")
                    cop_ex_btn.click(
                        fn=_cop_exclude_json,
                        inputs=[cop_ex_sha, cop_ex_reason],
                        outputs=cop_ex_out,
                    )
                with gr.Tab("Deploy — what's next?"):
                    cop_deploy_btn = gr.Button("What's next + Cloud Run inventory?")
                    cop_deploy_out = gr.Markdown()
                    cop_deploy_btn.click(fn=_cop_deploy_md, outputs=cop_deploy_out)

        with gr.Tab("Run the whole journey (one click)"):
            gr.Markdown(
                "### Runs all 6 levels sequentially with a HITL pause between L4 and L5.\n\n"
                "Same backends as the per-level tabs, but orchestrated."
            )
            with gr.Row():
                wj_lid = gr.Textbox(label="learner_id", value="alice@school.ie")
                wj_sub = gr.Dropdown(
                    label="subnation", choices=[s for s, _, _ in L0_SUBNATIONS], value="ireland"
                )
                wj_sbj = gr.Dropdown(
                    label="subject",
                    choices=["mathematics", "gaeilge", "english"],
                    value="mathematics",
                )
            wj_q = gr.Textbox(
                label="user_question (for Level 5)",
                value="Draw a labelled diagram of the sine rule",
            )
            wj_btn = gr.Button("Run the whole journey")
            wj_out = gr.JSON(label="Journey outcome (all 6 levels)")
            wj_btn.click(
                fn=run_whole_journey, inputs=[wj_lid, wj_sub, wj_sbj, wj_q], outputs=wj_out
            )

    return demo


def main():
    app = build_app()
    if app is None:
        return 1
    app.launch(server_name="0.0.0.0", server_port=7860)
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
