"""gemini_hackathon.dlt_pipelines.ireland — Ireland K-12 + LC DLT sources.

Lifted + rewritten from `cianfhoghlaim/dlt_sources/education/ireland/british_isles/`.
The 5 educational stages are covered:

  - Aistear (Early Years 0-6)        — placeholder (W5 scope: Primary + Secondary)
  - Primary (4-12)                   — primary.py
  - Junior Cycle (12-15)              — junior_cycle.py
  - Senior Cycle / Leaving Cert (15-19) — leaving_cert.py + ncca_<subject>.py × 6
  - Tertiary                          — deferred (Phase 2)

Modules:
  - _shared               — `named_destinations()` factory
  - primary               — NCCA Primary curriculum DLT source
  - junior_cycle          — NCCA Junior Cycle DLT source
  - leaving_cert          — NCCA Leaving Cert DLT source (the umbrella)
  - ncca_chemistry        — per-subject NCCA chemistry DLT source
  - ncca_computer_science — per-subject NCCA computer_science DLT source
  - ncca_english          — per-subject NCCA english DLT source
  - ncca_gaeilge          — per-subject NCCA gaeilge DLT source (bilingual)
  - ncca_geography        — per-subject NCCA geography DLT source
  - ncca_mathematics      — per-subject NCCA mathematics DLT source

The 6 NCCA-adjacent subjects (accounting, biology, business, french,
irish_t2, physics) are scaffolded but not lifted in W5 — they ship in
W11 with the England AQA/OCR/Pearson equivalents.
"""

from dlt_pipelines.ireland._shared import (
    named_destinations,
    get_default_destination,
)

__all__ = [
    "named_destinations",
    "get_default_destination",
]
