# Leabharlann — the gemini_hackathon library corpus

This directory contains the personal / academic library corpus that the
gemini_hackathon education system uses for context grounding +
supplementary material.

The corpus is lifted **verbatim** from `cianfhoghlaim/leabhoghlaim/leabharlann/`
(the parent monorepo's library directory) per the August 2026 refactor.

## What's here (committed)

This directory contains ONLY:
  - `README.md` — this file
  - `README.gaeilge.md` — the Irish-language version of the source README
  - `fetch_full_corpus.sh` — the script to populate the corpus from the
    parent monorepo (idempotent, safe to re-run)
  - `gaeilge.manifest.csv`, `zotero.manifest.csv`,
    `ollscoil_na_gaillimhe.manifest.csv` — the canonical integrity records
    (path + SHA-256 + size) for the 3 deferred subdirs

The full ~432 MB of PDFs from the 4 "verbatim" subdirs (aigne/,
gemini_deep_research/, mata/, saontacht_oideachais/) is NOT committed
(the cumulative pack size exceeds GitHub's receive-pack timeout for
a single push). Use `./fetch_full_corpus.sh` to populate them locally
from `../cianfhoghlaim/leabharlann/`.

## What's NOT here (deferred — fetch via the script)

The 7 subdirs + their PDFs:
  - **aigne/** (46 MB, psychology / philosophy / wellbeing) — fetch via script
  - **gemini_deep_research/** (80 MB, research across technology/law/politics/medical/culture) — fetch via script
  - **mata/** (146 MB, mathematics textbook archive) — fetch via script
  - **saontacht_oideachais/** (160 MB, Irish-medium education) — fetch via script
  - **gaeilge/** (621 MB, 40 Irish-language PDFs) — fetch via script
  - **zotero/** (381 MB, 117 academic PDFs in Zotero format) — fetch via script
  - **ollscoil_na_gaillimhe/** (2.2 GB, 5 UoG programmes) — fetch via script

## Fetching the corpus

For the deferred subdirs, use the fetch script:

```bash
cd /Users/cianmacandeisigh/dev/gemini_hackathon
./data/leabharlann/fetch_full_corpus.sh
```

This script copies from `$LEABHARLANN_SRC` (default
`/Users/cianmacandeisigh/dev/cianfhoghlaim/leabharlann`) into this
directory. It's idempotent — running twice is safe.

## Manifests

Each of the 3 manifest CSVs contains the canonical "what should be
in this directory" record for the deferred subdirs:

```
path,sha256,size_bytes,format,title,subject,language,year
```

The manifest is the canonical integrity record — verify with
`shasum -a 256` against `data/leabharlann/<subdir>.manifest.csv`.
