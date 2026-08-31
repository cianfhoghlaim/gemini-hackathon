"""NCCA-informed progression ledger + unofficial certificate generation.

Two surfaces, deliberately scoped to the Irish NCCA (the canonical home
jurisdiction; the descriptor vocabulary + award types are the same
shape across all 8 subnations):

1. ``progression.py`` — the mastery ledger. ``AssessmentEvent`` events
   flow in; ``OutcomeMastery`` is updated by ``apply_event()``. The
   descriptors are the NCCA CBA vocabulary:
   - "Exceptional"
   - "Above expectations"
   - "In line with expectations"
   - "Yet to meet expectations"

2. ``certificate.py`` — the unofficial certificate builder. ``render()``
   returns a string (markdown) the frontend can show + a metadata
   object the UI uses to render the badge. Every certificate is marked
   "UNOFFICIAL" — never a credential, always a celebration of progress.

Award types supported (Phase 11 surface):
   - Junior Cycle / Leaving Cycle / GCSE / A-Level / National 5 /
     Higher / Advanced Higher
   - CBA (Classroom-Based Assessment)
   - Short Course
   - L1LP / L2LP (Level 1 / Level 2 Learning Programmes)
"""

from .certificate import (
    AwardType,
    CertificateRecord,
    render_certificate_markdown,
)
from .progression import (
    AssessmentEvent,
    AssessmentType,
    MasteryDescriptor,
    OutcomeMastery,
    apply_event,
    progress_summary,
)

__all__ = [
    "AssessmentEvent",
    "AssessmentType",
    "AwardType",
    "CertificateRecord",
    "MasteryDescriptor",
    "OutcomeMastery",
    "apply_event",
    "progress_summary",
    "render_certificate_markdown",
]
