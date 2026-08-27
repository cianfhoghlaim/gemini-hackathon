# 2026-08-27-official-lc-jc-certificate-pipeline-v1

        > Official-style LC/JC certificate pipeline (the SHOWCASE)

        ## Why

        The hackathon's headline feature is an LC/JC certificate that is provably grounded in the 5 NCCA policy PDFs (per the user's instruction: 'every claim cites a NCCA PDF page').

        ## What changes

        Created gemini_hackathon/certificate/ with types + pipeline.py (7 stages: extract_criteria → decompose_outcomes → extract_paper + marking → search_official → generate_background → compose_certificate → save_to_provenance). The output is a CertificateRecord with PNG (~80 KB) + PDF (~700 B) + provenance + skill-progression summary.

        ## Acceptance
        - Smoke test passes (3 outcomes × 5 PDFs = 15 citations
- PNG + PDF magic bytes valid
- UNOFFICIAL banner present
- award descriptor auto-selected). The pipeline is the SHOWCASE.