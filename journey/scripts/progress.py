"""progress.py — per-learner progress + workshop leaderboard (CLI + JSON).

Lifted structurally from the per-learner status dashboards in
`docs/adk-examples/way-back-home/level_2/backend/api/routes/`, re-anchored
on the gemini-hackathon Firestore schema. Two modes:

    --leaderboard          : print all participants sorted by current_level + progress
    --learner-id UID       : print one participant's full state across all 6 levels

Both modes default to pretty-printed CLI; --json emits one JSON object
per line (so a workshop host can pipe to `jq` for dashboard panels).

Usage:
    python -m journey.scripts.progress --event-code bwai-mycity
    python -m journey.scripts.progress --event-code bwai-mycity --learner-id alice@school.ie
    python -m journey.scripts.progress --event-code bwai-mycity --leaderboard --json | jq -s 'sort_by(.current_level) | reverse | .[0:10]'
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _get_client():
    """Return a Firestore client (None if offline / unset / no library)."""
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    if not project_id:
        logger.warning("GOOGLE_CLOUD_PROJECT unset — running in offline-stub mode")
        return None
    try:
        from google.cloud import firestore
    except ImportError:
        logger.warning("google-cloud-firestore not installed — running in offline-stub mode")
        return None
    database = os.environ.get("JOURNEY_FIRESTORE_DATABASE", "(default)")
    return firestore.Client(project=project_id, database=database)


def _load_event(client, event_code: str):
    if client is None:
        return None
    snap = client.collection("journeys").document(event_code).get()
    return snap.to_dict() if snap.exists else None


def _list_participants(client, event_code: str) -> list[dict]:
    """Return the participants under `journeys/{event_code}/participants`."""
    if client is None:
        return []
    return [doc.to_dict() for doc in client.collection("journeys").document(event_code).collection("participants").stream()]


def _format_leaderboard(participants: list[dict]) -> str:
    """Pretty-print a leaderboard sorted by current_level desc, progress desc."""
    if not participants:
        return "  (no participants yet)"
    sorted_p = sorted(
        participants,
        key=lambda p: (-int(p.get("current_level", "0")), -(int(p.get("progress", "000000"), 16))),
    )
    rows = []
    rows.append(f"  {'learner':<35}  {'level':>5}  {'progress':>8}  last_updated")
    rows.append("  " + "-" * 78)
    for p in sorted_p:
        rows.append(
            f"  {p.get('learner_id', '?')[:33]:<35}  "
            f"{p.get('current_level', '0'):>5}  "
            f"0x{(p.get('progress', '000000') or '000000'):>6}  "
            f"{p.get('last_updated', '?')}"
        )
    return "\n".join(rows)


def _format_learner(p: dict) -> str:
    """Pretty-print one participant's full state across the 6 levels."""
    lines = []
    lines.append(f"  learner_id:    {p.get('learner_id', '?')}")
    lines.append(f"  display_name:  {p.get('display_name', '?')}")
    lines.append(f"  subnation:     {p.get('subnation', '?')}")
    lines.append(f"  current_level: {p.get('current_level', '0')}")
    lines.append(f"  progress:      0x{p.get('progress', '000000') or '000000'}")
    lines.append(f"  last_updated:  {p.get('last_updated', '?')}")
    lines.append("")
    lines.append("  Per-level status:")
    for level in range(6):
        completed_at = p.get(f"level_{level}_completed_at")
        marker = "✓" if completed_at else "·"
        lines.append(f"    [{marker}] Level {level} {completed_at or '—'}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-code", required=True)
    parser.add_argument("--learner-id", default=None)
    parser.add_argument("--leaderboard", action="store_true")
    parser.add_argument("--database", default=None)
    parser.add_argument("--project-id", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.project_id:
        os.environ["GOOGLE_CLOUD_PROJECT"] = args.project_id
    if args.database:
        os.environ["JOURNEY_FIRESTORE_DATABASE"] = args.database

    client = _get_client()
    event = _load_event(client, args.event_code)
    if event is None and client is not None:
        logger.error("event not found: journeys/%s", args.event_code)
        return 1

    if args.learner_id:
        participants = _list_participants(client, args.event_code)
        match = next((p for p in participants if p.get("learner_id") == args.learner_id), None)
        if match is None:
            logger.warning("learner_id %r not found in event %r", args.learner_id, args.event_code)
            return 1
        if args.json:
            print(json.dumps(match, indent=2))
        else:
            print(_format_learner(match))
        return 0

    if not args.leaderboard:
        # Default: print the event summary + leaderboard together.
        if event is not None:
            print(f"  event:        {event.get('name')}  ({event.get('code')})")
            print(f"  subnation:    {event.get('default_subnation')}")
            print(f"  max_partic.:  {event.get('max_participants')}")
            print(f"  created_at:   {event.get('created_at')}")
        participants = _list_participants(client, args.event_code)
        if not args.json:
            print(f"\n  leaderboard ({len(participants)} participant(s)):")
            print(_format_leaderboard(participants))
        else:
            for p in participants:
                print(json.dumps(p))
        return 0

    # --leaderboard flag: just the leaderboard.
    participants = _list_participants(client, args.event_code)
    if args.json:
        for p in participants:
            print(json.dumps(p))
    else:
        print(_format_leaderboard(participants))
    return 0


if __name__ == "__main__":
    sys.exit(main())
