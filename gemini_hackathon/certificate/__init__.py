"""gemini_hackathon.certificate — the LC/JC certificate pipeline (W14, the showcase).

The end-to-end pipeline that produces an official-style Leaving Certificate
(LC) or Junior Certificate (JC) certificate for a learner, grounded
in the 5 NCCA policy documents + the learner's mastery ledger.

7 stages:

  1. ExtractCertificationCriteria — BAML extraction of the official
     certification criteria from the 5 NCCA PDFs (data/ireland/ncca_policy/).
  2. DecomposeOutcomes — split the learner's request into per-outcome
     parts (the LC has ~30 outcomes per subject).
  3. ExtractExamPaper + ExtractMarking — pull the relevant exam paper
     + marking scheme from data/ireland/lc_subject/.
  4. SearchOfficial — RAG over the 5 NCCA policy corpus.
  5. GenerateCertificateBackground — Flux + the W10 prompt bank
     (subject × stage → visual prompt).
  6. ComposeCertificate — PIL: background + text overlay + seal
     + competency strip + provenance footer.
  7. SaveToProvenance — write the result to Firestore + the mastery-vector
     store + markdown memory (W9 MasteryLedger — Google-native since the
     Phase 6 GCP-first refactor; see gemini_hackathon/ledger/).

The output is a `CertificateRecord` with:
  - learner_id + name + subject + stage
  - The certificate image (PNG bytes)
  - The PDF export (PDF bytes)
  - The full provenance footer (every cited page)
  - The skill-progression summary

Per the user's instruction: every claim on every certificate cites a
page from one of the 5 NCCA policy PDFs. The "UNOFFICIAL" banner is
always present (never an NCCA-issued credential).

Pipeline consumed by:
  - The W7 ADK 2 cross-subject workflow (Stage 1 coordinator)
  - The W12 editorial canvas (build_workflow_canvas)
  - The W13 LC HF Space (the headline demo)
"""

from gemini_hackathon.certificate.pipeline import (
    NCCA_POLICY_PDFS,
    CertificatePipeline,
    CertificatePipelineConfig,
)
from gemini_hackathon.certificate.types import (
    CertificateOutcomeRecord,
    CertificateRecord,
    CertificationCitation,
    CertificationCriteria,
)

__all__ = [
    "NCCA_POLICY_PDFS",
    "CertificateOutcomeRecord",
    "CertificatePipeline",
    "CertificatePipelineConfig",
    "CertificateRecord",
    "CertificationCitation",
    "CertificationCriteria",
]
