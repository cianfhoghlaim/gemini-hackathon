"""journey.scripts — workshop-host CLI entrypoints (top-level).

Re-exports the implementations from `gemini_hackathon.journey.scripts.*`
so the README-documented invocation pattern `python -m journey.scripts.X`
works without requiring the workshop host to know about `gemini_hackathon.*`.

(The actual implementation files are duplicated to `journey/scripts/`
in the repo for documentation discoverability — the `pyproject.toml`'s
`[tool.hatch.build.targets.sdist]` includes this directory so the files
ship with the source distribution. Keeping them as separate files (not
symlinks) keeps the deploy-artifact self-contained.)
"""
from __future__ import annotations

# Import from the canonical implementation. The two file pairs (one in
# `/journey/scripts/`, one in `/gemini_hackathon/journey/scripts/`) share
# content; the workshop host can `python -m journey.scripts.X` directly,
# and the in-package import (`gemini_hackathon.journey.scripts.X`) reads
# the in-package files.
from gemini_hackathon.journey.scripts import (  # noqa: F401  (re-export)
    admin_create_event,
    progress,
)

__all__ = [
    "admin_create_event",
    "progress",
]
