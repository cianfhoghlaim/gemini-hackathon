# Tasks

## Status: closed

## Workstream: W14

- [x] **Why**: The hackathon's headline feature is an LC/JC certificate that is provably grounded in the 5 NCCA policy PDFs (per the user's instruction: 'every claim cites a NCCA PDF page').
- [x] **Scope**: Created gemini_hackathon/certificate/ with types + pipeline.py (7 stages: extract_criteria → decompose_outcomes → extract_paper + marking → search_official → generate_background → compose_certificate ...
- [x] **Acceptance**: Smoke test passes (3 outcomes × 5 PDFs = 15 citations; PNG + PDF magic bytes valid; UNOFFICIAL banner present; award descriptor auto-selected). The pipeline is the SHOWCASE.