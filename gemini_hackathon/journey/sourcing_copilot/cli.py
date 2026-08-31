"""cli.py — the SourcingCopilot's CLI entrypoint.

Usage:
    python -m gemini_hackathon.journey.sourcing_copilot.cli --status
        # one-shot: print the 9-row status table + "what should I deploy next?"

    python -m gemini_hackathon.journey.sourcing_copilot.cli --exclude <sha256>:<reason>
        # one-shot: mark one doc excluded + show next 10 candidates

    python -m gemini_hackathon.journey.sourcing_copilot.cli
        # interactive REPL: "what's sourced? / how many normalised? / should
        # I exclude X? / run the sourced step now?" — multi-turn

    python -m gemini_hackathon.journey.sourcing_copilot.cli --list-services
        # one-shot: list deployed Cloud Run services + Cloud Scheduler jobs

The REPL uses the ADK 2 `Runner.run_async()` per
`docs/adk-examples/adk2-tutorial/L0_first_agent/`. In offline mode
(google.adk not importable), the REPL degrades to a tool-call-only
fallback that prints the tool result + a recommended next-step — no
LLM in the loop, but the workshop host still gets the same answer.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _print_status_table(counts: dict[str, Any]) -> None:
    print("\n=== Sourcing pipeline status ===")
    rows = [
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
    for k in rows:
        print(f"  {k:<22}  {counts.get(k, '-')}")


def _status_one_shot() -> int:
    from gemini_hackathon.journey.sourcing.pipeline import step_status

    counts = step_status(project_id=None)
    _print_status_table(counts)
    rec = _recommend_next_steps_one_shot(counts)
    print("\n=== Recommendation ===")
    print(f"  next step:  {rec.get('recommendation', '?')}")
    for reason in rec.get("reasons", []):
        print(f"    - {reason}")
    return 0


def _recommend_next_steps_one_shot(counts: dict[str, Any]) -> dict[str, Any]:
    """Pure-Python version of `recommend_next_steps` (no LLM, no SDK)."""
    rec: dict[str, Any] = {"recommendation": None, "reasons": []}
    if counts.get("sourced_ok", 0) == 0:
        rec["recommendation"] = "sourced"
        rec["reasons"].append(
            "No docs sourced yet — run `python -m gemini_hackathon.journey.sourcing.pipeline --step=sourced`"
        )
    elif (counts.get("normalised") or 0) < (counts.get("sourced_ok") or 0):
        rec["recommendation"] = "normalised"
        rec["reasons"].append(f"{counts['normalised']}/{counts['sourced_ok']} docs normalised")
    elif (counts.get("baml_extracted") or 0) < (counts.get("normalised") or 0):
        rec["recommendation"] = "extract-baml"
        rec["reasons"].append(
            f"{counts['baml_extracted']}/{counts['normalised']} docs BAML-extracted"
        )
    else:
        rec["recommendation"] = "journey:level_1"
        rec["reasons"].append(
            "All docs sourced + normalised + BAML-extracted — ready for the Journey orchestrator"
        )
    return rec


def _exclude_one_shot(spec: str) -> int:
    from gemini_hackathon.journey.sourcing_copilot.tools import mark_excluded

    sha, _, reason = spec.partition(":")
    result = mark_excluded(sha, reason=reason or "out_of_scope")
    if not result.get("ok"):
        print(f"failed: {result.get('error', 'unknown error')}")
        return 1
    print(f"excluded: {result.get('excluded')}  reason={result.get('reason')}")
    print("\nNext candidates (top 10 non-excluded):")
    for c in result.get("next_candidates", []):
        print(
            f"  {c.get('sha256', '?')[:16]}...  {c.get('jurisdiction', '?'):<14}  {c.get('subject_slug', '?'):<22}  {c.get('document_type', '?')}"
        )
    return 0


def _list_services_one_shot() -> int:
    from gemini_hackathon.journey.sourcing_copilot.tools import (
        list_cloud_run_services,
        list_scheduled_jobs,
    )

    services = list_cloud_run_services()
    print("\n=== Cloud Run services ===")
    for svc in services:
        print(
            f"  {svc.get('metadata', {}).get('name', svc.get('name', '?')):<35}  {svc.get('metadata', {}).get('region', svc.get('region', '?'))}"
        )

    jobs = list_scheduled_jobs()
    print("\n=== Cloud Scheduler jobs ===")
    for j in jobs:
        print(
            f"  {j.get('name', '?'):<30}  {j.get('schedule', '?')}  {j.get('lastRun', j.get('last_run', '?'))}"
        )

    return 0


async def _repl_turn(runner, user_id: str, session_id: str, content: Any) -> str:
    """Run one ADK 2 runner turn, return the final agent text.

    Mirrors the pattern at
    `docs/adk-examples/adk2-tutorial/L0_first_agent/agent.py:ask()`.
    """
    from google.genai import types as gtypes

    message = gtypes.Content(role="user", parts=[gtypes.Part(text=content)])
    final_text = "(no response)"
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=message,
    ):
        msg = getattr(event, "message", None)
        if msg and getattr(msg, "parts", None):
            chunks = [p.text for p in msg.parts if getattr(p, "text", None)]
            if chunks:
                final_text = "".join(chunks)
    return final_text


def _interactive_repl() -> int:
    from gemini_hackathon.journey.sourcing_copilot.agent import build_copilot_agent, build_runner

    agent = build_copilot_agent()
    if agent is None:
        print(
            "Interactive REPL requires `google-adk` — falling back to one-shot tool-call surface."
        )
        return _status_one_shot()

    runner = build_runner(agent)
    if runner is None:
        return _status_one_shot()

    print("SourcingCopilot REPL — type a question, 'exit' to leave.")
    print("(offline-aware: tools still run; LLM responses degrade if no GCP creds)")
    print()
    user_id = "copilot-host"
    session_id = "repl"
    while True:
        try:
            query = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye.")
            return 0
        if not query or query.lower() in ("exit", "quit"):
            print("bye.")
            return 0
        if query == "status":
            _status_one_shot()
            continue
        if query.startswith("exclude "):
            _exclude_one_shot(query[len("exclude ") :].strip())
            continue
        try:
            response = asyncio.run(_repl_turn(runner, user_id, session_id, query))
            print(f"\ncopilot> {response}\n")
        except Exception as exc:
            print(f"REPL error: {exc}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--status", action="store_true", help="Print the 9-row status table + recommendation"
    )
    parser.add_argument(
        "--list-services", action="store_true", help="List Cloud Run services + Scheduler jobs"
    )
    parser.add_argument(
        "--exclude",
        type=str,
        default=None,
        metavar="sha256[:reason]",
        help="Mark one document excluded (one-shot)",
    )
    parser.add_argument(
        "--trigger",
        type=str,
        default=None,
        metavar="step",
        help="Trigger one sourcing step (one-shot, delegates to the pipeline CLI)",
    )
    args = parser.parse_args(argv)

    if args.status:
        return _status_one_shot()
    if args.list_services:
        return _list_services_one_shot()
    if args.exclude:
        return _exclude_one_shot(args.exclude)
    if args.trigger:
        from gemini_hackathon.journey.sourcing_copilot.tools import trigger_step

        return trigger_step(args.trigger).get("ok", False) is False

    # Default: interactive REPL (or one-shot status if REPL fails).
    return _interactive_repl()


if __name__ == "__main__":
    sys.exit(main())
