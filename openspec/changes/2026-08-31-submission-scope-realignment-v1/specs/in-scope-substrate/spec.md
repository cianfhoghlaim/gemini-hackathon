# Spec delta — in-scope-substrate

> **Capability:** the canonical surface area of what the 2026-08-31 submission's
> demo path exercises, with the deferred substrate explicitly enumerated.

## ADDED Requirements

### Requirement: In-scope corpus

The submission's demo path MUST operate on the 97-PDF in-scope corpus:

- 5 NCCA policy PDFs at `data/ireland/ncca_policy/`
- 5 NCCE artefacts at `data/bi_ep/syllabi_raw/uk_ncce/curriculum/`
- 87 English Leaving Cert PDFs at `data/ireland/leaving_certificate/*/en/*.pdf`
- 1 sample LC Maths at `data/syllabi/sample_lc_maths_2024.pdf`

The demo path MUST NOT depend on any PDF outside this corpus.

#### Scenario: in-scope corpus count

- **WHEN** `notebooks/04_corpus_inventory.py` is run against `data/`
- **THEN** the reported in-scope PDF count MUST equal 97
- **AND** the deferred count MUST equal 52 (Gaeilge LC PDFs)

### Requirement: In-scope SQL view

The DuckDB view `raw.official_documents_in_scope` MUST exist and MUST
filter `raw.official_documents` to:

```sql
WHERE jurisdiction = 'United Kingdom (NCCE)'
   OR (jurisdiction = 'Ireland' AND UPPER(language) IN ('EN', 'E', 'ENGLISH', ''));
```

#### Scenario: view row count

- **WHEN** `SELECT COUNT(*) FROM raw.official_documents_in_scope` is executed
- **THEN** the count MUST equal 97

### Requirement: Deferred substrate preserved

The deferred jurisdictions + the Gaeilge PDFs + the non-LC rows MUST
remain on disk and in code, but MUST NOT appear in the demo path:

- 52 Gaeilge PDFs at `data/ireland/leaving_certificate/_deferred_ga/`
- 35 DuckDB rows in `raw.official_documents_deferred`
- 8 jurisdiction DLT scrapers in `dlt_pipelines/_base/` (gated)

#### Scenario: deferred still enumerable

- **WHEN** the deferred surface is enumerated (filesystem walk + DuckDB scan
  + DLT `_base/` directory scan)
- **THEN** the deferred counts MUST match the values above
- **AND** the `deferred` view MUST still be queryable

### Requirement: A2UI surface emit on generate_asset

The `generate_asset` ADK tool MUST emit a `NccaPdfCard` A2UI surface via
the existing `record_a2ui_raw_event` + `wrap_a2ui_in_raw_event` helpers
at `gemini_hackathon_backend/catalog/a2ui_emitter.py`.

#### Scenario: A2UI mount

- **WHEN** the `/agents` route is opened and a `generate_asset` call completes
- **THEN** the `<A2UIRenderer surfaceId={DEFAULT_SURFACE_ID} />` in
  `web/src/routes/agents.tsx` MUST render the `NccaPdfCard` component

### Requirement: 5-step demo reproducibility

The demo MUST be reproducible by following `docs/DEMO_SCRIPT.md` end-to-end:

1. `make backend` + `cd web && bun install && bun run dev` → `http://localhost:3000`
2. Click "Demo" → `/compare-models` → see Gemma-4 vs Gemini-3.5 vision charts
3. `/learning-graphs` → open notebooks 10 + 17 + 19 iframes
4. `/agents` → "Generate a certificate for an LC Maths student named Maya
   who mastered Differentiation" → A2UI NccaPdfCard
5. `make ncce-visualise` → `http://localhost:7860` → Editorial Studio →
   run the CertificatePipeline

#### Scenario: end-to-end demo

- **WHEN** all 5 steps complete without error
- **THEN** the demo MUST produce a visible `NccaPdfCard` A2UI component
- **AND** the certificate PNG MUST be written under `/tmp/certificates/`

## MODIFIED Requirements

None.

## REMOVED Requirements

None. The deferred substrate is preserved verbatim.

## Rationale

The submission's narrative is "the BIEP substrate is fully wired across
8 jurisdictions; for this demo we focused on the 97 PDFs that exercise
every layer". The substrate (DLT + CocoIndex + BAML + Google ADK +
Gemma 4 + Gemini 3.5 + A2UI + Gradio + Web SPA) is unchanged.

The deferred jurisdictions are tracked by:

- `2026-08-27-defer-ni-wales-scotland-iom-v1`
- `2026-08-27-deferred-jersey-guernsey-v1`
- `2026-08-27-defer-tuatha-consolidation-v1`