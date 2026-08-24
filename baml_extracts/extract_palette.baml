// ============================================================================
// baml_extracts/extract_palette.baml
//
// SourcePalette extraction — the 4-path OCR/VLM ensemble returns palette +
// typography + iconography from an official exam-board PDF.
//
// Produces a SourcePalette that gets persisted to themes/<source>_palette.json
// and served to the TanStack Start frontend as CSS custom properties.
// ============================================================================

class SourcePalette {
  source_key       string                   @description("Stable slug, e.g. 'ncca.ie', 'aqa.org.uk'")
  source_name      string                   @description("Human-readable board name")
  jurisdiction     string                   @description("ISO-style: 'Ireland' | 'England' | 'Scotland' | 'Wales' | 'Northern Ireland' | 'Isle of Man'")
  level            CurriculumLevel          @description("Curriculum level this palette governs")
  primary          string                   @description("Primary brand hex (#RRGGBB)")
  secondary        string                   @description("Secondary brand hex")
  accent           string                   @description("Accent / highlight hex")
  background       string                   @description("Page background hex")
  text             string                   @description("Body-text hex")
  heading_font     string                   @description("Web-safe heading typeface name")
  body_font        string                   @description("Web-safe body typeface name")
  logo_url         string?                  @description("Absolute URL to the official logo PNG/SVG")
  flag             string?                  @description("ISO 3166-1 alpha-2 + emoji ('IE 🇮🇪')")
  symbol           string?                  @description("Cultural symbol — 'shamrock' | 'rose' | 'thistle' | 'daffodil' | 'shamrock-tara' | 'triskelion' | 'dragon' | …")
  confidence       float                    @description("Overall extraction confidence in [0.0, 1.0]")
}

enum CurriculumLevel {
  LC               @alias("Leaving Certificate")
  JC               @alias("Junior Cycle")
  GCSE             @alias("GCSE")
  GCSE_A               @alias("GCSE-A")
  AS_A2            @alias("AS-A2")
  A_Level          @alias("A-Level")
  National_5       @alias("National-5")
  Higher           @alias("Higher")
  Advanced_Higher  @alias("Advanced-Higher")
  Other            @alias("Other")
}

// ----------------------------------------------------------------------------
// Primary extraction function
// ----------------------------------------------------------------------------

function ExtractSourcePalette(source_url: string, pdf_path: string) -> SourcePalette {
  client "MiniMax"
  prompt #"
    You are a theming/brand analyst for the BIEP (British & Irish Education
    Pipeline) project. Your job is to extract the complete visual identity
    of an official exam-board source from its brand-guidelines PDF.

    INPUTS
    ------
    source_url : {{ source_url }}
    pdf_path   : {{ pdf_path }}

    EXTRACTION TARGETS
    ------------------
    1. Colors — primary, secondary, accent, background, text (all hex).
       Pick the canonical official hex from the brand book. If the source
       uses sub-branding (e.g. "primaryDark"), collapse to the main primary.
    2. Typography — heading + body typeface name as it appears on the
       brand page (e.g. "Barlow", "Georgia", "Open Sans", "Source Sans 3").
    3. Iconography — logo_url (absolute URL), flag (ISO-2 + emoji),
       symbol (cultural symbol per the jurisdiction).
    4. Level — which curriculum this palette governs (LC / A-Level / GCSE /
       National-5 / Higher / Advanced-Higher / GCSE-A / AS-A2 / JC).

    CONFIDENCE
    ----------
    Score the overall extraction in [0.0, 1.0]:
      1.00 — every field directly visible in the PDF
      0.85 — most fields directly visible, 1-2 inferred
      0.70 — multiple fields inferred from context
      <0.70 — should not be persisted; flag for manual review

    Return the result in the JSON schema above.
    {{ ctx.output_format }}
  "#
}

// ----------------------------------------------------------------------------
// Secondary fallback — single-color heuristic for low-confidence PDFs
// ----------------------------------------------------------------------------

function ExtractPaletteHeuristic(pdf_path: string) -> SourcePalette {
  client "Unsloth"
  prompt #"
    You are a fast theming extractor running on a local 26B Unsloth model.
    Given a PDF at {{ pdf_path }}, extract the dominant palette using
    cheap heuristics (k-means on rendered pages, font-name OCR).

    Return a SourcePalette. Set confidence <= 0.7 if the PDF appears
    low-resolution or the brand guidelines are ambiguous.
    {{ ctx.output_format }}
  "#
}