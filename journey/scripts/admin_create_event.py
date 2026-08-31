"""admin_create_event.py — idempotent creation of the journey workshop event doc.

Lifted structurally from `docs/adk-examples/way-back-home/scripts/create_event.py`
(the Firestore-direct + CLI-auth + API variants), re-anchored on the
gemini-hackathon Firestore schema (Phase 6). Writes:

    journeys/{event_code}                  : the workshop metadata
    journeys/{event_code}/participants/{uid} : per-learner status (created lazily)

Usage:
    python -m journey.scripts.admin_create_event bwai-mycity "British Isles Journey Workshop" \\
        --max-participants 500 \\
        --admin-email your-name@google.com
"""

from __future__ import annotations

import argparse
import datetime as _dt
import logging
import os
import sys
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return _dt.datetime.now(tz=_dt.UTC).isoformat(timespec="seconds")


def _build_event_doc(
    code: str,
    name: str,
    *,
    max_participants: int,
    admin_email: str = "",
    default_subnation: str = "ireland",
) -> dict[str, Any]:
    """Build the canonical event doc shape (idempotent — safe to re-write)."""
    return {
        "code": code,
        "name": name,
        "default_subnation": default_subnation,
        "max_participants": max_participants,
        "admin_email": admin_email,
        "active": True,
        "created_at": _now_iso(),
        "last_updated": _now_iso(),
        "levels_unlocked": ["0", "1", "2", "3", "4", "5"],
        "current_level": "0",
        "progress": "000000",
    }


def _get_firestore_client():
    """Lazy Firestore client (returns None in offline mode)."""
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    if not project_id:
        return None
    try:
        from google.cloud import firestore

        database = os.environ.get("JOURNEY_FIRESTORE_DATABASE", "(default)")
        return firestore.Client(project=project_id, database=database)
    except ImportError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("code", help="The event code (e.g. 'bwai-mycity')")
    parser.add_argument("name", help="The workshop display name")
    parser.add_argument(
        "--max-participants",
        type=int,
        default=int(os.environ.get("JOURNEY_MAX_PARTICIPANTS", "200")),
    )
    parser.add_argument("--admin-email", default=os.environ.get("JOURNEY_ADMIN_EMAIL", ""))
    parser.add_argument(
        "--default-subnation",
        choices=(
            "ireland",
            "england",
            "northern_ireland",
            "scotland",
            "wales",
            "jersey",
            "guernsey",
            "isle_of_man",
        ),
        default=os.environ.get("JOURNEY_DEFAULT_SUBNATION", "ireland"),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the doc that would be written but don't touch Firestore",
    )
    parser.add_argument(
        "--project-id",
        default=os.environ.get("GOOGLE_CLOUD_PROJECT", ""),
        help="GCP project ID (overrides GOOGLE_CLOUD_PROJECT env var)",
    )
    parser.add_argument(
        "--database",
        default=os.environ.get("JOURNEY_FIRESTORE_DATABASE", "(default)"),
        help="Firestore database ID (defaults to '(default)')",
    )
    args = parser.parse_args()

    doc = _build_event_doc(
        args.code,
        args.name,
        max_participants=args.max_participants,
        admin_email=args.admin_email,
        default_subnation=args.default_subnation,
    )

    if args.dry_run:
        import json as _json

        print(_json.dumps(doc, indent=2))
        return 0

    client = _get_firestore_client()
    if client is None:
        logger.warning(
            "GOOGLE_CLOUD_PROJECT unset OR google-cloud-firestore missing — "
            "running in offline-stub mode (no Firestore write)."
        )
        import json as _json

        print(_json.dumps({"offline_stub": True, "would_write": doc}, indent=2))
        return 0

    client.collection("journeys").document(args.code).set(doc)
    logger.info("wrote journeys/%s to Firestore", args.code)
    return 0


if __name__ == "__main__":
    sys.exit(main())
