# Level 1 — Syllabus extraction

> **BAML `ExtractCurriculumSyllabus` → Vertex AI embeddings → Firestore
> `FindNearest`.** The 4-node Workflow runs end-to-end and writes the
> subject's learning outcomes into your Vector Search index.

The 4-node ADK 2 Workflow (per `adk2-tutorial/L1_graph_basics/workflow.py`
+ `gemini_hackathon/agents/workflows/pillar1_grading.py`):

```
START -> fetch_syllabus_pdf -> extract_baml -> embed_chunks -> upsert_vector
```

The 2 `#REPLACE-*` markers a workshop participant fills in are inside
`gemini_hackathon.journey.level_1_syllabus_extraction.__init__`:

  - **REPLACE-1** (in `embed_chunks`) — wire the `VertexEmbedder`:
    ```python
    from cocoindex_flows._shared._vertex_embedder import VertexEmbedder

    e = VertexEmbedder()
    vector = await e.embed(chunk_text)
    ```
    The stub returns a deterministic SHA-256 placeholder vector so the
    embed + upsert paths still exercise end-to-end without GCP creds.

  - **REPLACE-2** (in `upsert_vector`) — wire the `VectorTarget`:
    ```python
    from cocoindex_flows._shared._vector_target import get_vector_target, VectorRow

    v = get_vector_target()  # honours VECTOR_BACKEND env (firestore | vertex)
    await v.upsert_batch([VectorRow(...)])
    ```
    The stub writes to an in-memory list so the workshop still demos.

## What you'll learn

| Concept | Source |
|---|---|
| **BAML extraction** | The canonical pattern for typed LLM extraction |
| **Vertex AI embeddings** | `gemini-embedding-001` (1536-d, multilingual EN/GA) |
| **Firestore `FindNearest`** | The Phase 2 dual-backed VectorTarget — Firestore is the default; Vertex AI Vector Search via `VECTOR_BACKEND=vertex` |
| **Workflow graph** | `Workflow(edges=[(START, fn1, fn2, ..., agent)])` per `adk2-tutorial/L1_graph_basics` |

## What you'll build

By the end of Level 1:
- A `LCSyllabusDocument` JSON extracted from the official syllabus PDF
- One `VectorRow` per learning outcome embedded into Firestore `FindNearest`
- A "Top-3 related outcomes you've already mastered" surfacing query ready
  for the studio's Studio

## Prerequisites

- `setup.sh` run successfully (`GOOGLE_CLOUD_PROJECT` + a venv)
- `verify.sh` ticked all 8 boxes (incl. the "factory has >=100 Apps" tick)
- `mise run baml:generate` succeeded (you'll need the BAML client)
- The corpus has been ingested — run `mise run journey:bootstrap-corpus`
  (offline stub) OR `mise run gcp:ingest-corpus` (real GCS)

## Quickstart

```bash
# 1. Run the standalone pre-flight
cd gemini_hackathon/journey/level_1_syllabus_extraction
python -c "from gemini_hackathon.journey.level_1_syllabus_extraction import run_level_1; print('OK')"

# 2. Launch the studio (needs Gradio — `uv add gradio`)
python -m gemini_hackathon.journey.level_1_syllabus_extraction.app --port 7861

# 3. In the UI:
#    - Subnation: ireland
#    - Subject:   mathematics
#    - Language:  en
#    - Click "Extract + embed + upsert"
#
# 4. Verify the chunks landed in Firestore:
python -m journey.scripts.progress \\
    --event-code $JOURNEY_EVENT_CODE \\
    --learner-id test  # offline stub mode

# 5. Move to Level 2 once you see N total_learning_outcomes + chunks_embedded
```

## BAML schema (read this before filling in REPLACE-1)

The BAML function `b.ExtractCurriculumSyllabus(pdf_text, subject, language)`
returns an `LCSyllabusDocument` (in `baml_extracts_education/stages/
leaving_cycle.baml`):

```baml
class LCSyllabusDocument {
  subject LCSubjectSlug
  language string @description("EN | GA | EN_AND_GA")
  stage LCEducationStage
  source_pdf string
  module_topics LCModule[]
  total_learning_outcomes int
  ...
}
```

The `module_topics[].learning_outcomes[]` is what gets chunked + embedded.
A real codelab participant would:
  1. Call `b.ExtractCurriculumSyllabus` in `extract_baml` (this is the
     "agent node" — the only step with an LLM call).
  2. Loop over `module_topics` and embed each LO with the Vertex embedder.
  3. Upsert each embedded chunk via `VectorTarget.upsert_batch`.

## What the verify gate checks (between Level 1 and Level 2)

```
$ ./journey/scripts/verify.sh
=== 5. 4-stage factory manifest ===
  [OK]   4-stage factory has >=100 Apps
...
```

The factory has >=100 Apps — the same factory the orchestrator's Level 1
node calls into via `cocoindex_flows/_factory/four_stage.py`. If you ran
the codelab with `EMBED_BACKEND=vertex` you get real Vertex embeddings;
otherwise the stubs produce SHA-256 placeholders.
