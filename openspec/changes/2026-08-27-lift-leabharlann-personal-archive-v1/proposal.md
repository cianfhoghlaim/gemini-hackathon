# 2026-08-27-lift-leabharlann-personal-archive-v1

        > Lift leabharlann corpus + UoG archive manifests (verbatim)

        ## Why

        The user's personal / academic library corpus is the supplementary material for the editorial canvas. The full 3.6 GB is too large for git; commit the 4 smaller subdirs verbatim + manifests for the 3 larger ones.

        ## What changes

        Copied data/leabharlann/{README.md,aigne/,gemini_deep_research/,mata/,saontacht_oideachais/} verbatim (~430 MB). Generated manifests (CSV with sha256 + path + size) for gaeilge/, zotero/, ollscoil_na_gaillimhe/. Wrote fetch_full_corpus.sh.

        ## Acceptance
        - 4 subdirs committed
- 3 manifests with correct sha256 hashes
- the fetch script is executable + idempotent.