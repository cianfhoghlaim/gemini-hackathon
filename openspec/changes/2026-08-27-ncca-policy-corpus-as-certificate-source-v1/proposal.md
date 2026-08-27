# 2026-08-27-ncca-policy-corpus-as-certificate-source-v1

        > 5 NCCA policy PDFs as committed data — certificate source of truth

        ## Why

        The LC/JC certificate pipeline (W14) requires an authoritative corpus to cite. The 5 NCCA official PDFs are that corpus.

        ## What changes

        Lifted 5 PDFs verbatim from cianfhoghlaim/leaving_certificate/ into data/ireland/ncca_policy/ (SC-L1-L2-Programme-Statement.pdf, key-competencies-in-senior-cycle_en.pdf, the-potential-of-online-learning-environments_en.pdf, the-potential-of-technology-to-support-online-certification-and-reporting.pdf, scr-advisory-report_en.pdf). SHA-256 checksums in INDEX.yaml.

        ## Acceptance
        - INDEX.yaml present + valid
- shasum -a 256 matches
- PDF files open in a PDF reader
- certificates cite at least one page from each of the 5 PDFs.