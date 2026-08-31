# Level 5 — Generate an asset (REFRAMED from "mint a certificate")

> **You ask a question. The pipeline grounds it in the syllabus and
> generates a personalised asset.** This is the showcase — per
> `docs/ideas/AI Syllabus to JSON Schema.md` + `AI Chemistry Education
> Image Generation.md`, the point of the whole syllabus pipeline is to
> inform AI output with the official specification. Level 5 is the
> demonstration.

The 3-node ADK 2 Workflow:

```
START -> search_syllabus_node (Firestore Vector Search over L1's output)
       -> baml_extract_asset_request (BAML ExtractCurriculumSyllabus re-call)
       -> fibo_generate_node (FIBO JSON-native image gen -> GCS upload)
```

The 2 `#REPLACE-*` markers a workshop participant fills in are inside
`gemini_hackathon.journey.level_5_asset_generation.__init__`:

  - **REPLACE-1** (in `search_syllabus_node`) — wire the `VectorTarget.find_nearest()`:
    ```python
    from cocoindex_flows._shared._vector_target import get_vector_target

    v = get_vector_target()
    matches = await v.find_nearest("biep_lc_mathematics_en_chunks", query_vector, k=3)
    ```
    The stub returns 3 deterministic synthetic outcomes from the offline
    sample so the search → BAML → FIBO flow still exercises end-to-end.

  - **REPLACE-2** (in `baml_extract_asset_request`) — wire the BAML call:
    ```python
    from baml_client import b
    from gemini_hackathon_assets_fibo.models import EducationAssetRequest

    request_dict = b.ExtractEducationAssetRequest(
        user_question=question,
        matched_outcomes=matched,
        subject=subject,
        subnation=subnation,
    )
    ```
    The stub builds the canonical `EducationAssetRequest` shape directly.

## What you'll learn

| Concept | Source |
|---|---|
| **BAML re-call for asset generation** | `AI Syllabus to JSON Schema.md` + `AI Chemistry Education Image Generation.md` |
| **FIBO JSON-native image gen** | `gemini_hackathon_assets_fibo` |
| **GCS upload + provenance** | `gs://<project>-biep-assets/journey/<file>.png` |
| **Per-subject prompt bank** | `gemini_hackathon_assets_fibo.education_prompts` (14 subjects x 5 stages) |

## What you'll build

By the end of Level 5:
- A `VectorSearch` over the syllabus corpus returning 3 top-k matches
- A structured `EducationAssetRequest` (subject style + asset type + prompt text + citation list)
- A real PNG (in production) or a deterministic stub PNG (in offline mode) saved to `./data/journey_assets/`
- A `gs://` URL (in production) or `file://` URL (offline) recorded as the asset's provenance

## Why the REFRAME from "mint a certificate" to "generate an asset"

Per the user's direction during planning: the pedagogical value of
the official syllabus pipeline is **grounding AI output in the official
specification**. A certificate is a personal milestone — fine, but
doesn't exercise the pipeline's distinguishing feature (knowing what
the syllabus says and using it). Generating an asset, by contrast,
demonstrates the pipeline's purpose every time: the question is the
learner's question; the answer is *grounded* in the curriculum; the
visible asset is the proof.

This also aligns with the `gemini_hackathon_assets_fibo` package's
existing purpose — the certificate pipeline was always one specific
asset type among many (`syllabus_diagram`, `experiment_apparatus`,
`formative_exit_card`, `topic_summary`, `molecule_svg`, `equation_render`,
`map_diagram`).

## Quickstart

```bash
# 1. Launch the studio
python -m gemini_hackathon.journey.level_5_asset_generation.app --port 7865

# 2. In the UI:
#    - user_question: "Draw a labelled diagram of the sine rule for triangle ABC,
#                      with a note on when the ambiguous case applies"
#    - subnation:     ireland
#    - subject:       mathematics
#    - Click "Generate asset"
#
# 3. The asset appears:
#    - matched_outcomes: 3 syllabus chunks (or stub placeholders offline)
#    - asset_request:    EducationAssetRequest with asset_type, subject_style,
#                         prompt_text, citation_lo_codes, ncca_policy_citations
#    - storage_uri:      gs://<project>-biep-assets/journey/lvl5_<timestamp>.png
#                         (or file:// in offline mode)
#    - asset_bytes_size: ~100 (stub) or the real PNG size (production)
```

## What's the asset, exactly?

Per the BAML contract, the generated asset is a `EducationAssetRequest`
that the FIBO pipeline (or, in the offline stub, a placeholder PNG)
renders. The request captures:

  - **subject_style**: `subject_mathematics` (one of 14 NCCA subjects)
  - **asset_type**: `syllabus_diagram` (default; could be `equation_render`,
    `molecule_svg`, etc. per the asset type catalogue)
  - **prompt_text**: the FIBO JSON-native scene description, anchored on
    the user's question + the cited learning outcomes
  - **citation_lo_codes**: the learning outcome codes the asset must
    visualise (every visible element grounded in an LO)
  - **ncca_policy_citations**: the 5 NCCA policy PDFs (Phase 1's
    authoritative source of truth)

The whole point of the pipeline: a future participant can ask
"draw me the cosine rule" and the answer is guaranteed to be anchored
in `MA-LC-MA-2.2` (the cosine rule LO) + `SC-L1-L2-Programme-Statement.pdf`
(the NCCA maths policy). No hallucinated formulas.

## What the verify gate checks (after Level 5)

```
$ ./journey/scripts/verify.sh
...
=== 7. OCR ensemble consensus ===
  [OK]   OCR ensemble consensus vote
=== 8. Journey config + subnation table ===
  [OK]   journey config loads
```

The OCR consensus tick (#7) ensures the 4-path OCR fan-out (used by
Level 2, which Level 5's BAML re-call depends on for any historical
PDFs) is healthy. The journey config tick (#8) ensures the workshop's
event code is wired correctly.
