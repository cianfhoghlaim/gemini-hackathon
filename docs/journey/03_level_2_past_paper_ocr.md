# Level 2 — Past paper OCR (4-path consensus)

> **Document AI + Gemini Vision + Gemma Vertex + pypdfium2 text-layer, in
> parallel. Pairwise-Jaccard consensus vote picks the winner.** Honest
> about what the "consensus" really measures (inter-path agreement, NOT
> a quality score — see the honesty note in `gemini_hackathon.ocr_ensemble`).

The 2-node ADK 2 Workflow (per `adk2-tutorial/L2a_parallel_join/workflow.py`):

```
START -> extract_4_paths (ParallelAgent: 4 OCR backends in parallel)
       -> consensus_vote_node (picks the winner, extracts NCCA citations)
```

The 4 OCR paths:

  1. **document_ai** — Document AI Layout Parser (structured text + layout)
  2. **gemini_vision** — Gemini 3.5 Flash via Vertex AI (multimodal)
  3. **gemma4_vertex** — Gemma 4 26B-A4B on Vertex AI Model Garden (opt-in)
  4. **pypdfium2** — the PDF's embedded text layer (zero-cost ground truth)

## What you'll learn

| Concept | Source |
|---|---|
| **ParallelAgent + JoinNode** | `adk2-tutorial/L2a_parallel_join/workflow.py` |
| **Multi-modal OCR ensemble** | `gemini_hackathon.ocr_ensemble.EnsembledExtractor` |
| **Consensus vote** | pairwise-Jaccard token similarity (per `ocr_ensemble.consensus_vote`) |
| **NCCA policy PDF citations** | The canonical "every claim cites a page" rule |

## What you'll build

By the end of Level 2:
- All 4 paths return their text extraction
- The consensus vote picks the winning path
- NCCA policy citations are extracted from the winning text
- The studio's "Past paper OCR" tab shows all 4 path outputs + the winner

## Prerequisites

- Level 0 completed (you have a `learner_id` + subnation in Firestore)
- You have a past paper PDF path (or use the offline-stub path)
- Vertex AI service account has `roles/documentai.user` (for the live path)

## Quickstart

```bash
# 1. Launch the studio (Gradio)
python -m gemini_hackathon.journey.level_2_past_paper_ocr.app --port 7862

# 2. In the UI:
#    - PDF path: data/ireland/lc_subject/mathematics/en/lc_maths_2024_p1.pdf
#               (or empty for offline stub)
#    - Click "Run the 4-path ensemble"
#
# 3. Inspect the outputs:
#    - "Path results" tab: per-path text lengths + errors
#    - "Consensus vote" tab: winning path + score + NCCA citations
#    - "Winning text" tab: the winning extraction (first 6000 chars)
```

## Honesty about the consensus

The pairwise-Jaccard vote measures **inter-path agreement**, NOT extraction
quality. A 4-path vote where all paths agree does NOT mean the text is
correct — it means they all hallucinated the same way. To measure actual
extraction quality, you'd swap in a real `ragas.evaluate()` call (when a
labelled eval set exists). For workshop demo purposes, the consensus vote
shows what `gemini_hackathon.ocr_ensemble` does — and the docs are honest
about the gap.

## What the verify gate checks (between Level 2 and Level 3)

```
$ ./journey/scripts/verify.sh
=== 4. OCR dispatch table ===
  [OK]   OCR dispatch table has 7 capabilities
...
```

The 7-capability dispatch table is the public API of `gemini_hackathon.ocr`;
the journey's Level 2 uses 4 of those 7 (`forms`, `layout`, `gaelic`,
`english`) via `run_backend` directly.
