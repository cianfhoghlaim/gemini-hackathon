# Spec Delta: theming

This delta is applied by the openspec change
[`2026-08-24-gemini-hackathon-public-v1`](../proposal.md). It
describes the ADDED Requirements to the canonical
[`openspec/specs/theming/spec.md`](../../../../specs/theming/spec.md)
that this change adds.

## ADDED Requirements

### Requirement: Per-source palette extraction from official documents

The system SHALL extract a per-source palette from each official
source PDF using the BAML `ExtractSourcePalette(pdf_path, source_name)
-> SourcePalette` function. The extraction MUST produce the following
fields:

- `palette.primary` (hex string, e.g. `"#00733B"`)
- `palette.secondary`, `palette.accent`, `palette.background`,
  `palette.text` (each hex string)
- `typography.heading`, `typography.body` (font family names)
- `iconography.logoUrl`, `iconography.faviconUrl`, `iconography.symbol`
- `flag` (Unicode flag emoji)
- `lineage.extractedBy`, `lineage.extractedFromPdf`, `lineage.confidence`
  (0.0–1.0), `lineage.extractedAt` (ISO-8601 timestamp)

#### Scenario: Palette extraction succeeds for a valid NCCA PDF

- **WHEN** the operator runs `ExtractSourcePalette(pdf_path="scr-advisory-report_en.pdf", source_name="NCCA")`
- **THEN** the returned `SourcePalette.primary` SHALL equal `"#00733B"`
  (the canonical NCCA green)
- **AND** `lineage.confidence` SHALL be `>= 0.85`
- **AND** `lineage.extractedFromPdf` SHALL equal `"scr-advisory-report_en.pdf"`

#### Scenario: Palette extraction rejects an invalid PDF

- **WHEN** the operator runs `ExtractSourcePalette(pdf_path="missing.pdf")`
  where the file does not exist
- **THEN** the function SHALL raise a `PaletteExtractionError`
  with the message `"PDF not found: missing.pdf"`
- **AND** SHALL NOT return a partially-populated palette

#### Scenario: Palette extraction preserves the lineage envelope

- **WHEN** the operator inspects any extracted palette JSON
- **THEN** the JSON SHALL include the `lineage` envelope with all
  four fields populated
- **AND** `extractedBy` SHALL equal `"ExtractSourcePalette v1.0.0"`
  (or the current version)

### Requirement: 8 British Isles jurisdiction palettes

The system SHALL ship 8 per-jurisdiction palettes, one per British
Isles jurisdiction, at `themes/<source_key>_palette.json`:

| Jurisdiction | Source key | File |
|--------------|-----------|------|
| Ireland | `ncca.ie` | `themes/ncca_palette.json` |
| England (AQA) | `aqa.org.uk` | `themes/aqa_palette.json` |
| England (OCR) | `ocr.org.uk` | `themes/ocr_palette.json` |
| England (Pearson) | `qualifications.pearson.com` | `themes/pearson_palette.json` |
| Scotland | `sqa.org.uk` | `themes/sqa_palette.json` |
| Wales | `wjec.co.uk` | `themes/wjec_palette.json` |
| Northern Ireland | `ccea.org.uk` | `themes/ccea_palette.json` |
| Isle of Man | `gov.im/education` | `themes/iom_palette.json` |

#### Scenario: Every jurisdiction has a palette file

- **WHEN** the operator lists `themes/*_palette.json`
- **THEN** the system SHALL return exactly 8 files (one per
  jurisdiction in the table above)
- **AND** each file SHALL load successfully via
  `gemini_hackathon.theming.load_palette(source_key)`

#### Scenario: Every palette declares a unique `primary`

- **WHEN** the operator inspects the 8 palettes
- **THEN** the `primary` color SHALL be unique across all 8 palettes
  (no two jurisdictions share the same brand colour)
- **AND** the `flag` SHALL match the canonical flag for the
  jurisdiction (e.g. Ireland = 🇮🇪, Scotland = 🏴󠁧󠁢󠁳󠁣󠁴󠁿)

### Requirement: 5 safeguarding body palettes

The system SHALL ship 5 per-body palettes for the safeguarding
policy sources, under `themes/safeguarding/`:

1. `gov.ie/education` → `themes/safeguarding/ie_dept_education_palette.json`
2. `gov.uk/dfe` → `themes/safeguarding/uk_dfe_palette.json`
3. `education.gov.scot` → `themes/safeguarding/scotland_gov_palette.json`
4. `gov.wales/education` → `themes/safeguarding/wales_gov_palette.json`
5. `ccea.org.uk/safeguarding` → `themes/safeguarding/ni_ccea_palette.json`

#### Scenario: Every safeguarding body has a palette file

- **WHEN** the operator lists `themes/safeguarding/*_palette.json`
- **THEN** the system SHALL return exactly 5 files
- **AND** each file SHALL load successfully via
  `gemini_hackathon.theming.load_palette(source_key)`

#### Scenario: Safeguarding palettes declare their policy URLs

- **WHEN** the operator inspects a safeguarding palette
- **THEN** the `policies` field SHALL contain at least one
  official policy URL (e.g. `"https://www.gov.ie/en/department-of-education/publications/..."`)
- **AND** each URL SHALL resolve to an `https://gov.ie`,
  `https://www.gov.uk`, `https://education.gov.scot`,
  `https://gov.wales`, or `https://ccea.org.uk` host

### Requirement: Palette loading via theming.py + Convex schema

The system SHALL load palettes through the canonical Python loader
at `gemini_hackathon/theming.py` and SHALL expose them to the
TanStack Start frontend via a Convex `palettes` table.

The `gemini_hackathon.theming.load_palette(source_key: str) ->
Optional[Palette]` function SHALL:

- Read `themes/<source_key>_palette.json` (or
  `themes/safeguarding/<file_stem>.json` for safeguarding keys)
- Parse the JSON and return a `Palette` dataclass
- Return `None` (and log a `WARNING`) if the palette does not exist

The Convex `palettes` table SHALL mirror the `Palette` dataclass:

```ts
palettes: defineTable({
  sourceKey: v.string(),
  sourceName: v.string(),
  jurisdiction: v.string(),
  primary: v.string(),
  secondary: v.string(),
  accent: v.string(),
  background: v.string(),
  text: v.string(),
  headingFont: v.string(),
  bodyFont: v.string(),
  flag: v.string(),
  logoUrl: v.string(),
})
```

#### Scenario: load_palette returns a Palette dataclass

- **WHEN** the operator calls
  `load_palette("ncca.ie")`
- **THEN** the returned object SHALL be a `Palette` dataclass
- **AND** `palette.primary` SHALL equal `"#00733B"`
- **AND** `palette.heading_font` SHALL equal `"Barlow"`

#### Scenario: load_palette returns None for an unknown source

- **WHEN** the operator calls `load_palette("unknown.gov")`
- **THEN** the function SHALL return `None`
- **AND** SHALL emit a `WARNING` log record with the source key

#### Scenario: Convex schema mirrors the Palette dataclass

- **WHEN** the operator queries `convex.query("palettes:getBySourceKey", { sourceKey: "ncca.ie" })`
- **THEN** the response SHALL include `primary: "#00733B"` +
  `headingFont: "Barlow"` + `flag: "🇮🇪"`

### Requirement: CSS custom properties injection at runtime

The system SHALL inject the chosen palette's CSS variables on the
root `<html>` element at runtime, so that every page renders with
the chosen source's brand identity.

The injection MUST follow this contract:

- The injected variables SHALL be `--color-primary`,
  `--color-secondary`, `--color-accent`, `--color-background`,
  `--color-text`, `--font-heading`, `--font-body`
- The injection SHALL happen client-side (via a React hook in
  `web/`) on first paint, AND server-side (via a TanStack Start
  middleware that sets the variables on the streamed HTML
  response) so the first paint is correctly themed
- The injection SHALL be reversible: changing the source key
  SHALL update the CSS variables without a page reload

#### Scenario: Default palette is NCCA on first paint

- **WHEN** a user visits the homepage with no source key set
- **THEN** the root `<html>` element SHALL have
  `--color-primary: #00733B` (NCCA green) injected
- **AND** the page SHALL render with NCCA green + Barlow headings

#### Scenario: Switching to AQA re-themes the page

- **WHEN** a user clicks the "Switch to AQA" button on the
  equivalency page
- **THEN** the CSS variables on the root `<html>` element SHALL
  update to `--color-primary: #00457C` (AQA navy)
- **AND** the page SHALL re-render with AQA navy + AQA Sans
  headings without a full page reload

#### Scenario: SSR injection matches client-side injection

- **WHEN** a user visits the AQA-themed page with JavaScript
  disabled
- **THEN** the streamed HTML response SHALL include
  `<html style="--color-primary: #00457C; ...">` (the SSR
  injection)
- **AND** the page SHALL render with AQA navy on first paint