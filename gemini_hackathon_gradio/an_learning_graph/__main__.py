"""CLI entry point: ``python -m gemini_hackathon_gradio.an_learning_graph``.

``__init__.py`` defines ``main()`` behind an ``if __name__ == "__main__"``
guard, which never fires when the package is run with ``-m``. This module
is what ``-m`` actually executes (per `make ncce-visualise`).
"""

from __future__ import annotations

import sys

from . import main

if __name__ == "__main__":
    sys.exit(main())
