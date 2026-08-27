# NCCA Policy Corpus

The 5 NCCA (National Council for Curriculum and Assessment) policy documents
that constitute the constitutional source of truth for the
`gemini_hackathon` Leaving Cycle / Junior Cycle certificate pipeline.

Every claim on every generated certificate cites a page in one of these
PDFs. The provenance footer of every certificate is non-negotiable:
it lists each policy PDF + the page(s) that informed the certificate's
content.

## Why these 5?

| Document | Role in the certificate |
|---|---|
| `SC-L1-L2-Programme-Statement.pdf` | Defines the Senior Cycle (LC) framework — the award types, descriptors, and the Senior Cycle reform context. |
| `key-competencies-in-senior-cycle_en.pdf` | Authoritative vocabulary for the 5 NCCA Key Competencies (Communicating, Being Creative, Working with Others, Managing Information & Thinking, Managing Myself). Used by `baml_extracts/education/certification_criteria.baml:ExtractKeyCompetencies` to ground the certificate's competency strip. |
| `the-potential-of-online-learning-environments_en.pdf` | NCCA advisory on online learning — authorises the "technology-supported assessment" framing. |
| `the-potential-of-technology-to-support-online-certification-and-reporting.pdf` | NCCA advisory on tech-enabled certification and reporting — defines the official frame for digital credentials (the certificate's PDF/PNG output). |
| `scr-advisory-report_en.pdf` | Senior Cycle Review advisory report — the reform framework that introduced L1LP/L2LP/Special Ed + revised the Key Competencies. |

## Provenance

- **Source repo**: `cianfhoghlaim` (the parent monorepo)
- **Source path**: `leaving_certificate/` (where the canonical NCCA corpus lives)
- **Lift method**: verbatim copy — no redaction, no modification, no OCR re-extraction
- **Lift date**: 2026-08-27 (W2 of the gemini_hackathon refactor)
- **SHA-256 checksums**: see `INDEX.yaml` (verified at lift time)

The checksums are the proof that the bytes in this folder match the bytes
in the source repo. If the cianfhoghlaim corpus changes, this lift
becomes stale — re-run `cp` + `shasum -a 256` to refresh.

## How the certificate pipeline uses these

In `baml_extracts/education/certification_criteria.baml` (W5+W14):

```baml
function ExtractSeniorCycleCertificationCriteria(
    pdf_text: string,
    source_pdf: string,
) -> CertificationCriteria {
    // Calls ExtractKeyCompetencies on the KC PDF
    // Calls ExtractCertificationDescriptors on the L1L2 PDF
    // Calls ExtractSCRContext on the SCR PDF
    // Returns the typed record + per-claim citations
}

class CertificationCitation {
    source_pdf: string
    page: int
    quote: string  // the verbatim text that informed the claim
}
```

The certificate's provenance footer is built from these citations:

```
Generated from 5 NCCA policy documents:
- SC-L1-L2-Programme-Statement.pdf, p. 12 (Senior Cycle framework)
- key-competencies-in-senior-cycle_en.pdf, p. 7 (5 Key Competencies)
- the-potential-of-technology-to-support-online-certification-and-reporting.pdf, p. 4 (tech-enabled certification)
- ...
Pipeline: gemini_hackathon data engineering platform
Date: YYYY-MM-DD
UNOFFICIAL — NOT an NCCA-issued credential
```

## What this corpus is NOT

- **Not the LC subject syllabi.** Those live in `gemini_hackathon/data/ireland/lc_subject/` (lifted in W5).
- **Not the JC subject specifications.** Those live in `gemini_hackathon/data/ireland/jc_subject/` (lifted in W5).
- **Not the SEC past papers or marking schemes.** Those are scraped by DLT (W5).
- **Not English AQA/OCR/Pearson or any other subnation.** The 5 PDFs are Ireland-NCCA only. The England equivalents (DfE + JCQ + Ofqual) are added in W11.

## Verification

```bash
cd gemini_hackathon
shasum -a 256 data/ireland/ncca_policy/*.pdf
# Compare against INDEX.yaml:checksum_sha256
```
