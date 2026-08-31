"""Session model: per-user subnation + role + subjects + cycles.

The session binds:
  - home subnation (ireland + england default; NI/Scotland/Wales
    available; jersey/guernsey/isle_of_man = future expansion pack)
  - role (student | parent | teacher)
  - active cycle + selected subjects
  - auto-resolved safeguarding + palette source keys

In production the session is durable (Firestore `users/{uid}` + Firebase
Auth ID token — see `web/src/lib/firebase.ts` + `functions/src/
auth_oncreate.ts`); in dev it lives in localStorage. The session is the
load-bearing piece for per-route content scoping.
"""

from .schema import (
    ACTIVE_SUBNATIONS,
    AVAILABLE_SUBNATIONS,
    CYCLES_PER_SUBNATION,
    DEFAULT_PALETTE_PER_SUBNATION,
    DEFAULT_SUBNATIONS,
    EXPANSION_SUBNATIONS,
    PALETTES_PER_JURISDICTION,
    SUBJECT_CATALOGUE,
    SUBNATION_BY_CODE,
    SUBNATIONS,
    ActiveSubnation,
    Cycle,
    Role,
    Session,
    Subject,
    SubnationMeta,
    get_subnation_meta,
    is_active_subnation,
    is_expansion_subnation,
    is_valid_cycle,
    is_valid_role,
    is_valid_subject,
    list_active_subnations,
    list_expansion_pack_subnations,
    list_subnations,
    subjects_for,
)

__all__ = [
    "ACTIVE_SUBNATIONS",
    "AVAILABLE_SUBNATIONS",
    "CYCLES_PER_SUBNATION",
    "DEFAULT_PALETTE_PER_SUBNATION",
    "DEFAULT_SUBNATIONS",
    "EXPANSION_SUBNATIONS",
    "PALETTES_PER_JURISDICTION",
    "SUBJECT_CATALOGUE",
    "SUBNATIONS",
    "SUBNATION_BY_CODE",
    "ActiveSubnation",
    "Cycle",
    "Role",
    "Session",
    "Subject",
    "SubnationMeta",
    "get_subnation_meta",
    "is_active_subnation",
    "is_expansion_subnation",
    "is_valid_cycle",
    "is_valid_role",
    "is_valid_subject",
    "list_active_subnations",
    "list_expansion_pack_subnations",
    "list_subnations",
    "subjects_for",
]
