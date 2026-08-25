"""Session model: per-user subnation + role + subjects + cycles.

The session binds:
  - home subnation (ireland + england default; NI/Scotland/Wales
    available; jersey/guernsey/isle_of_man = future expansion pack)
  - role (student | parent | teacher)
  - active cycle + selected subjects
  - auto-resolved safeguarding + palette source keys

In production the session is durable (Convex `userSessions` + BetterAuth
JWT); in dev it lives in localStorage. The session is the load-bearing
piece for per-route content scoping.
"""

from .schema import (
    ActiveSubnation,
    Role,
    Cycle,
    Subject,
    Session,
    SubnationMeta,
    SUBNATIONS,
    ACTIVE_SUBNATIONS,
    DEFAULT_SUBNATIONS,
    AVAILABLE_SUBNATIONS,
    EXPANSION_SUBNATIONS,
    SUBNATION_BY_CODE,
    PALETTES_PER_JURISDICTION,
    DEFAULT_PALETTE_PER_SUBNATION,
    CYCLES_PER_SUBNATION,
    SUBJECT_CATALOGUE,
    is_valid_role,
    is_valid_cycle,
    is_valid_subject,
    is_active_subnation,
    is_expansion_subnation,
    list_subnations,
    list_active_subnations,
    list_expansion_pack_subnations,
    get_subnation_meta,
    subjects_for,
)

__all__ = [
    "ActiveSubnation",
    "Role",
    "Cycle",
    "Subject",
    "Session",
    "SubnationMeta",
    "SUBNATIONS",
    "ACTIVE_SUBNATIONS",
    "DEFAULT_SUBNATIONS",
    "AVAILABLE_SUBNATIONS",
    "EXPANSION_SUBNATIONS",
    "SUBNATION_BY_CODE",
    "PALETTES_PER_JURISDICTION",
    "DEFAULT_PALETTE_PER_SUBNATION",
    "CYCLES_PER_SUBNATION",
    "SUBJECT_CATALOGUE",
    "is_valid_role",
    "is_valid_cycle",
    "is_valid_subject",
    "is_active_subnation",
    "is_expansion_subnation",
    "list_subnations",
    "list_active_subnations",
    "list_expansion_pack_subnations",
    "get_subnation_meta",
    "subjects_for",
]
