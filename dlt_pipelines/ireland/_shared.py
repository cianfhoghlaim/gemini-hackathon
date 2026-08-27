"""gemini_hackathon.dlt_pipelines.ireland._shared — shared helpers for the Ireland DLT pipeline.

Lifted + adapted from `cianfhoghlaim/dlt_sources/common/destinations.py`.
The `named_destinations()` factory is the canonical way to get a
MotherDuck / DuckLake / DuckDB destination by name.

In gemini_hackathon the destinations are:
  - `duckdb`: a local DuckDB file (default in dev / offline)
  - `ducklake`: a DuckLake catalog (the canonical lakehouse — lifted
    from cianfhoghlaim's `ducklake_cianfhoghlaim` named destination)
  - `motherduck`: MotherDuck cloud (the production lakehouse)
"""

from __future__ import annotations

import os
from typing import Any


# Canonical named destinations in gemini_hackathon
_NAMED_DESTINATIONS: dict[str, str] = {
    # Local DuckDB — the default in dev / offline mode.
    "duckdb": "duckdb:///./data/gemini_hackathon.duckdb",
    # Local DuckLake — the canonical lakehouse for the editorial canvas.
    "ducklake": "ducklake:///./data/gemini_hackathon.ducklake",
    # cianfhoghlaim compatibility — the cianfhoghlaim ducklake destination.
    "ducklake_cianfhoghlaim": "ducklake:///./data/gemini_hackathon.ducklake",
    # MotherDuck cloud — production lakehouse.
    "motherduck": "md:gemini_hackathon",
}


def named_destinations(name: str, **kwargs: Any) -> str:
    """Return the canonical destination URL for the named destination.

    Args:
        name: One of "duckdb", "ducklake", "motherduck".
        **kwargs: Ignored (kept for API compat with the original
            `named_destinations()` factory — pass-through kwargs).

    Returns:
        The destination URL string.

    Raises:
        ValueError: If `name` is not a recognised destination.
    """
    if name not in _NAMED_DESTINATIONS:
        raise ValueError(
            f"Unknown destination {name!r}; "
            f"valid: {sorted(_NAMED_DESTINATIONS)}"
        )
    return _NAMED_DESTINATIONS[name]


def get_default_destination() -> str:
    """Return the default destination based on env vars.

    Order:
      1. MOTHERDUCK_TOKEN set → "motherduck"
      2. DUCKLAKE_PATH set   → "ducklake"
      3. Otherwise           → "duckdb"
    """
    if os.getenv("MOTHERDUCK_TOKEN"):
        return named_destinations("motherduck")
    if os.getenv("DUCKLAKE_PATH"):
        return named_destinations("ducklake")
    return named_destinations("duckdb")


__all__ = ["named_destinations", "get_default_destination"]
