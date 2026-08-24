# Theming — gemini_hackathon

> **Status:** enforced project-wide (per
> [`openspec/specs/theming/spec.md`](../../openspec/specs/theming/spec.md))
> **Last updated:** 2026-08-24

This document describes the **per-source theming** pattern that
unifies all four hackathon ideas. The pattern is: every British
Isles jurisdiction has its own brand identity, and the
`gemini_hackathon` frontend adapts in real time to the chosen
source's identity.

---

## Why per-source theming matters

The British Isles have **eight jurisdictions** and **five
safeguarding bodies**, each with its own official palette,
typography, and iconography. The published syllabuses, brand
guidelines, and safeguarding policies are all visually distinct.

A pupil preparing for the Leaving Cert in Dublin has no easy
way to navigate to the equivalent specification in SQA's
National 5 or WJEC's A-Level — the documents live on different
websites with different visual identities. A safeguarding lead
at the Department of Education (Ireland) cannot quickly find the
matching policy in the Department for Education (UK) without
manually opening eight websites.

**Per-source theming** is the architectural pattern that
addresses both problems: the same application can render as NCCA
green-and-gold for one pupil, SQA blue for another, and WJEC red
for a third. The user picks their jurisdiction, and the entire
UI re-themes itself — palette, typography, flag, and logo — in
real time.

---

## The 8 British Isles jurisdictions

The `gemini_hackathon` repo ships **8 per-jurisdiction palettes**
at `themes/<source_key>_palette.json`:

| # | Jurisdiction | Source key | File | Brand colour |
|--:|--------------|-----------|------|--------------|
| 1 | Ireland | `ncca.ie` | [`themes/ncca_palette.json`](../../themes/ncca_palette.json) | NCCA green (`#00733B`) |
| 2 | England (AQA) | `aqa.org.uk` | [`themes/aqa_palette.json`](../../themes/aqa_palette.json) | AQA navy (`#00457C`) |
| 3 | England (OCR) | `ocr.org.uk` | `themes/ocr_palette.json` | OCR red (`#ED1C24`) |
| 4 | England (Pearson) | `qualifications.pearson.com` | [`themes/pearson_palette.json`](../../themes/pearson_palette.json) | Pearson blue (`#0067AD`) |
| 5 | Scotland | `sqa.org.uk` | [`themes/sqa_palette.json`](../../themes/sqa_palette.json) | SQA blue (`#003D7D`) |
| 6 | Wales | `wjec.co.uk` | [`themes/wjec_palette.json`](../../themes/wjec_palette.json) | WJEC red (`#751D2C`) |
| 7 | Northern Ireland | `ccea.org.uk` | `themes/ccea_palette.json` | CCEA navy (`#003366`) |
| 8 | Isle of Man | `gov.im/education` | [`themes/iom_palette.json`](../../themes/iom_palette.json) | IoM red (`#C8102E`) |

Each palette has the same JSON shape:

```json
{
  "sourceKey": "ncca.ie",
  "sourceName": "NCCA - National Council for Curriculum and Assessment",
  "jurisdiction": "Ireland",
  "level": "Senior Cycle (LC + JC)",
  "officialUrl": "https://www.curriculumonline.ie",
  "palette": {
    "primary": "#00733B",
    "primaryDark": "#00471F",
    "primaryLight": "#4FA776",
    "secondary": "#0E2D5C",
    "secondaryDark": "#061637",
    "secondaryLight": "#3C5684",
    "accent": "#FFB81C",
    "background": "#FFFFFF",
    "backgroundAlt": "#F5F5F5",
    "surface": "#FAFAFA",
    "border": "#E5E5E5",
    "text": "#1A1A1A",
    "textMuted": "#666666",
    "success": "#28A745",
    "warning": "#FFC107",
    "error": "#DC3545"
  },
  "typography": {
    "heading": "Barlow",
    "headingFallback": "Helvetica Neue, Arial, sans-serif",
    "body": "Georgia",
    "bodyFallback": "Georgia, Times New Roman, serif",
    "monospace": "Source Code Pro, monospace"
  },
  "iconography": {
    "logoUrl": "https://www.curriculumonline.ie/Publishing/PICS/Logo_2017.png",
    "faviconUrl": "https://www.curriculumonline.ie/favicon.ico",
    "symbol": "shamrock"
  },
  "flag": "🇮🇪",
  "lineage": {
    "extractedBy": "ExtractSourcePalette v1.0.0",
    "extractedFromPdf": "scr-advisory-report_en.pdf",
    "confidence": 0.92,
    "extractedAt": "2026-08-23T00:00:00Z"
  }
}
```

The 8 palettes are unique (no two share the same `primary`
colour) so the operator can tell at a glance which jurisdiction
they are looking at.

---

## The 5 safeguarding bodies

The safeguarding policy map covers **5 government bodies**, with
palettes at `themes/safeguarding/<file_stem>_palette.json`:

| # | Body | Source key | File | Brand colour |
|--:|------|-----------|------|--------------|
| 1 | Department of Education (Ireland) | `gov.ie/education` | [`themes/safeguarding/ie_dept_education_palette.json`](../../themes/safeguarding/ie_dept_education_palette.json) | Irish gov green (`#00563F`) |
| 2 | Department for Education (UK) | `gov.uk/dfe` | `themes/safeguarding/uk_dfe_palette.json` | UK gov blue (`#1D70B8`) |
| 3 | Scottish Government Education | `education.gov.scot` | [`themes/safeguarding/scotland_gov_palette.json`](../../themes/safeguarding/scotland_gov_palette.json) | Scottish gov blue (`#002F6C`) |
| 4 | Welsh Government Education | `gov.wales/education` | [`themes/safeguarding/wales_gov_palette.json`](../../themes/safeguarding/wales_gov_palette.json) | Welsh gov blue (`#1F3A93`) |
| 5 | CCEA Safeguarding (NI) | `ccea.org.uk/safeguarding` | [`themes/safeguarding/ni_ccea_palette.json`](../../themes/safeguarding/ni_ccea_palette.json) | CCEA navy (`#003366`) |

The safeguarding palettes are stored separately from the
jurisdiction palettes (under `themes/safeguarding/`) so that the
safeguarding theming roster is independent of the syllabus
roster.

---

## The BAML `ExtractSourcePalette` function

The palettes were originally extracted from the official PDFs by
the BAML `ExtractSourcePalette(pdf_path, source_name) ->
SourcePalette` function. The function is defined at
`baml_src/gemini_hackathon/extract_source_palette.baml`.

The function returns a `SourcePalette` BAML class with the same
fields as the JSON palette above. The class also includes the
`LineageEnvelope`:

```baml
class SourcePalette {
  sourceKey string
  sourceName string
  jurisdiction string
  level string
  officialUrl string
  palette PaletteColors
  typography Typography
  iconography Iconography
  flag string
  lineage LineageEnvelope
}

class LineageEnvelope {
  extractedBy string
  extractedFromPdf string
  confidence float
  extractedAt string  // ISO-8601
}
```

The `confidence` field is a float between `0.0` and `1.0` that
quantifies the model's confidence in the extracted palette. The
launch-quality bar is `confidence >= 0.85`.

The function uses the **4-path OCR/VLM ensemble** (per the
upstream BIEP v1 contract) — PyMuPDF text extraction, Tesseract
OCR, Google Document AI, and Claude Sonnet VLM — and the consensus
output is the one with the highest RAGAS score.

---

## The CSS custom property injection pattern

The chosen palette's CSS variables are injected on the root
`<html>` element at runtime, so every page renders with the
chosen source's brand identity.

The injected variables are:

| CSS variable | Source field | Example (NCCA) |
|--------------|-------------|----------------|
| `--color-primary` | `palette.primary` | `--color-primary: #00733B` |
| `--color-secondary` | `palette.secondary` | `--color-secondary: #0E2D5C` |
| `--color-accent` | `palette.accent` | `--color-accent: #FFB81C` |
| `--color-background` | `palette.background` | `--color-background: #FFFFFF` |
| `--color-text` | `palette.text` | `--color-text: #1A1A1A` |
| `--font-heading` | `typography.heading` | `--font-heading: Barlow` |
| `--font-body` | `typography.body` | `--font-body: Georgia` |

The injection runs both client-side (React hook in `web/`) and
server-side (TanStack Start middleware that sets the variables
on the streamed HTML response) so the first paint is correctly
themed.

### The hook (client-side)

```tsx
// web/src/hooks/useTheming.ts
import { useEffect } from "react";
import { usePalette } from "@/convex/palettes";

export function useTheming(sourceKey: string) {
  const palette = usePalette(sourceKey);

  useEffect(() => {
    if (!palette) return;
    const root = document.documentElement;
    root.style.setProperty("--color-primary", palette.primary);
    root.style.setProperty("--color-secondary", palette.secondary);
    root.style.setProperty("--color-accent", palette.accent);
    root.style.setProperty("--color-background", palette.background);
    root.style.setProperty("--color-text", palette.text);
    root.style.setProperty("--font-heading", palette.headingFont);
    root.style.setProperty("--font-body", palette.bodyFont);
  }, [palette]);
}
```

### The middleware (server-side)

```tsx
// web/src/middleware/theming.ts
import { getPalette } from "@/convex/palettes";

export async function themingMiddleware(request: Request) {
  const url = new URL(request.url);
  const sourceKey = url.searchParams.get("source") ?? "ncca.ie";
  const palette = await getPalette(sourceKey);

  // Inject the CSS variables on the streamed HTML response
  const cssVars = `
    --color-primary: ${palette.primary};
    --color-secondary: ${palette.secondary};
    --color-accent: ${palette.accent};
    --color-background: ${palette.background};
    --color-text: ${palette.text};
    --font-heading: ${palette.headingFont};
    --font-body: ${palette.bodyFont};
  `;

  // ... (the actual middleware is implemented in TanStack Start)
}
```

The hook + the middleware guarantee that the user sees the
correct brand identity on first paint, even with JavaScript
disabled.

---

## The Convex schema for palettes

The palettes are mirrored in the Convex database so the frontend
can query them via `convex.query("palettes:getBySourceKey", { sourceKey: "ncca.ie" })`.

The Convex schema is:

```ts
// web/convex/schema.ts
import { defineTable, defineSchema } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  palettes: defineTable({
    sourceKey: v.string(),
    sourceName: v.string(),
    jurisdiction: v.string(),
    level: v.string(),
    primary: v.string(),
    primaryDark: v.string(),
    primaryLight: v.string(),
    secondary: v.string(),
    secondaryDark: v.string(),
    secondaryLight: v.string(),
    accent: v.string(),
    background: v.string(),
    backgroundAlt: v.string(),
    surface: v.string(),
    border: v.string(),
    text: v.string(),
    textMuted: v.string(),
    success: v.string(),
    warning: v.string(),
    error: v.string(),
    headingFont: v.string(),
    bodyFont: v.string(),
    monospaceFont: v.string(),
    logoUrl: v.string(),
    faviconUrl: v.string(),
    symbol: v.string(),
    flag: v.string(),
    lineage: v.object({
      extractedBy: v.string(),
      extractedFromPdf: v.string(),
      confidence: v.number(),
      extractedAt: v.string(),
    }),
  }).index("by_source_key", ["sourceKey"]),
});
```

The Convex table mirrors the JSON palette 1-to-1. The
`getBySourceKey` query is indexed on the `sourceKey` column so
the lookup is O(1).

---

## References

- [`openspec/specs/theming/spec.md`](../../openspec/specs/theming/spec.md) —
  the canonical theming spec
- [`openspec/changes/2026-08-24-gemini-hackathon-public-v1/specs/theming/spec.md`](../../openspec/changes/2026-08-24-gemini-hackathon-public-v1/specs/theming/spec.md) —
  the theming spec delta
- [`gemini_hackathon/theming.py`](../../gemini_hackathon/theming.py) —
  the Python palette loader (the `Palette` dataclass +
  `load_palette()` + `list_all_palettes()`)
- [`themes/`](../../themes/) — the 8 jurisdiction palettes
- [`themes/safeguarding/`](../../themes/safeguarding/) — the
  5 safeguarding body palettes