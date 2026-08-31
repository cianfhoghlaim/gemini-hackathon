"""notebooks._shared.converted — runtime helpers for the converted .ipynb notebooks.

Lifted from cianfhoghlaim/notebooks/_shared/ for the .ipynb conversion:
  - marimo_stub.py        (the marimo runtime replacement — lets .ipynb execute)
  - db_stub.py            (DuckDB connection helper — no MotherDuck)
  - baml_stub.py          (BAML client lookup — returns no-op when unavailable)
  - schema_stub.py        (introspection helpers)

When `marimo export ipynb` runs against the cianfhoghlaim per-subject
marimo .py files, the resulting .ipynb files import these helpers from
this directory. The marimo_stub makes the .ipynb executable in any
Jupyter kernel without the marimo runtime.
"""

from .marimo_stub import mo  # re-export the stub `mo` namespace

__all__ = ["mo"]
