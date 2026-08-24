"""``python -m gemini_hackathon`` — the CLI entry point.

This module is the canonical entry point for the gemini_hackathon
public demo (per the BIEP Hackathon v3 specification). Running::

    python -m gemini_hackathon

is equivalent to invoking the console script::

    gemini-hackathon

Both routes go through :func:`gemini_hackathon.cli.main`.

The module is intentionally a thin wrapper — the entire CLI lives
in :mod:`gemini_hackathon.cli` so the console-script surface and
the ``-m`` surface stay byte-identical.
"""

from __future__ import annotations

from gemini_hackathon.cli import main


if __name__ == "__main__":
    main()