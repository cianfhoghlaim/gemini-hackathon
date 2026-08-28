"""marimo_stub — the runtime stub that lets the .ipynb notebooks execute end-to-end.

When a marimo .py notebook is converted to .ipynb via `marimo export ipynb`,
the `mo.ui.*` calls become no-op code cells (they print None). The
`mo` import fails in a non-marimo kernel.

This stub provides a minimal `mo` namespace that:
  - exposes `mo.ui.table(df)` → returns the dataframe (no widget)
  - exposes `mo.ui.altair_chart(chart)` → returns the chart object (no widget)
  - exposes `mo.ui.tabs`, `mo.ui.dropdown`, `mo.ui.multiselect`, etc. → returns None
  - exposes `mo.status.progress_bar(n)` → returns a no-op context manager
  - exposes `mo.ui.chat`, `mo.ui.tabs`, `mo.ui.run_button().form()` → no-op
  - exposes `mo.ai.llm.openai(...)` → returns a stub

This lets the converted .ipynb files execute cleanly in any Jupyter kernel
without the marimo runtime. The cells just don't display the interactive
widgets — they print the data + chart objects.

Lifted from the cianfhoghlaim marimo-pure strategy (no full .ipynb
runtime replacement exists in the gemini-hackathon prior to this).
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

logger = logging.getLogger(__name__)


class _MoUI:
    """The stub `mo.ui` namespace — every widget call returns None or the raw arg."""

    def __getattr__(self, name: str) -> Any:
        # Every `mo.ui.X(*args, **kwargs)` returns a no-op callable
        def _stub(*args: Any, **kwargs: Any) -> Any:
            if args:
                # Return the first arg (the data object) so the rest of the
                # notebook can still work with the underlying dataframe/chart
                return args[0]
            return None
        return _stub


_mo_ui = _MoUI()


class _MoAI:
    """The stub `mo.ai` namespace (for the LLM chat integrations)."""

    class _LLM:
        def openai(self, *args: Any, **kwargs: Any) -> Any:
            return SimpleNamespace(
                chat=lambda *a, **k: None,
                complete=lambda *a, **k: None,
            )

    llm = _LLM()


class _MoStatus:
    """The stub `mo.status` namespace."""

    @staticmethod
    @contextmanager
    def progress_bar(*args: Any, **kwargs: Any):
        """A no-op progress bar context manager."""
        yield


# The public `mo` namespace — what the marimo .py files expect to import
class _MoNamespace:
    ui = _mo_ui
    ai = _MoAI
    status = _MoStatus()

    # Allow attribute access for any other `mo.X` lookup
    def __getattr__(self, name: str) -> Any:
        return SimpleNamespace()


mo = _MoNamespace()


__all__ = ["mo"]