# DESIGN.md — Google Stitch design system for the gemini-hackathon

> This is the canonical `DESIGN.md` for `web/.stitch/DESIGN.md` — pushed
> via the Stitch MCP server + the REST API at
> `https://stitch.googleapis.com/v1/projects/{projectId}/screens:batchCreate`.
>
> Every Material-3 token name below maps to an **official government /
> awarding-body source** from `themes/_official_guidelines/*.json` (NOT
> mythology, NOT deity mapping — per the user's 2026-08-27 design decision).

## Frontmatter (parsed by `create_design_system_from_design_md`)

```yaml
# Colors (Material-3 token taxonomy — Stitch requires these names)
primary: "#CC4500"           # NCCA burnt orange (Ireland)
primary-container: "#B51E01"
on-primary: "#FFFFFF"
on-primary-container: "#F5B23E"
primary-fixed: "#CC4500"
primary-fixed-dim: "#882A04"
on-primary-fixed: "#FFFFFF"
on-primary-fixed-variant: "#E3E3DB"

secondary: "#1d70b8"         # GOV.UK brand (England)
secondary-container: "#5694ca"
on-secondary: "#FFFFFF"
on-secondary-container: "#0f385c"
secondary-fixed: "#1d70b8"
secondary-fixed-dim: "#16548a"
on-secondary-fixed: "#FFFFFF"
on-secondary-fixed-variant: "#5694ca"

tertiary: "#0065bd"          # Scottish Government brand (Scotland)
tertiary-container: "#4ea3db"
on-tertiary: "#FFFFFF"
on-tertiary-container: "#00437e"
tertiary-fixed: "#0065bd"
tertiary-fixed-dim: "#00437e"
on-tertiary-fixed: "#FFFFFF"
on-tertiary-fixed-variant: "#4ea3db"

neutral: "#1a1a1a"           # Body text black (all jurisdictions)
neutral-variant: "#484949"
inverse-surface: "#FFFFFF"
inverse-on-surface: "#1a1a1a"

surface: "#FAFAF7"          # Cream / soft-pastel (BDA Dyslexia Style Guide)
surface-dim: "#E3E3DB"
surface-bright: "#FFFFFF"
surface-container-lowest: "#FFFFFF"
surface-container-low: "#FAFAF7"
surface-container: "#FAFAF7"
surface-container-high: "#F0F0E8"
surface-container-highest: "#E8E8E0"
on-surface: "#1a1a1a"
on-surface-variant: "#484949"
surface-tint: "#CC4500"
surface-variant: "#E8E8E0"

background: "#FAFAF7"
on-background: "#1a1a1a"

outline: "#828893"
outline-variant: "#CECECE"

inverse-primary: "#FFFFFF"
inverse-secondary: "#E3E3DB"

error: "#d32205"
on-error: "#FFFFFF"
error-container: "#F5B23E"
on-error-container: "#882A04"

success: "#1a7032"
on-success: "#FFFFFF"

warning: "#fdd522"          # = focus background (gov.ie + SG)
on-warning: "#1a1a1a"

# Typography (Arial-first stack per /themes/_typography/shared.json)
display:
  font_family: "Arial"
  font_size_lg: "48px"
  font_size_md: "40px"
  font_size_sm: "32px"
  line_height: "1.2"
  font_weight: "700"

headline:
  font_family: "Arial"
  font_size_lg: "32px"
  font_size_md: "28px"
  font_size_sm: "24px"
  line_height: "1.3"
  font_weight: "700"

body:
  font_family: "Arial"
  font_size_lg: "19px"
  font_size_md: "16px"
  font_size_sm: "14px"
  line_height: "1.5"
  font_weight: "400"

label:
  font_family: "Arial"
  font_size_lg: "16px"
  font_size_md: "14px"
  font_size_sm: "12px"
  line_height: "1.4"
  font_weight: "600"

# Roundness
rounded:
  sm: "4px"
  DEFAULT: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
  full: "9999px"

# Spacing (8-pt grid)
spacing:
  unit: "8px"
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
  gutter: "16px"
  margin-mobile: "16px"
  margin-desktop: "32px"

# Theme config (matches Stitch's `update_design_system` schema)
theme:
  colorMode: "LIGHT"
  headlineFont: "ARIMO"        # Arimo for Welsh diacritics (gov.wales Counsel General, Dec 2025)
  bodyFont: "ARIMO"           # Arimo is the universal Welsh-diacritic-safe font
  labelFont: "ARIMO"
  roundness: "ROUND_TWELVE"
  customColor: "#CC4500"        # NCCA burnt orange (per the Irish primary subnation)
  colorVariant: "TONAL"
  overridePrimaryColor: "#CC4500"
  overrideSecondaryColor: "#1d70b8"
  overrideTertiaryColor: "#0065bd"
  overrideNeutralColor: "#1a1a1a"
  spacingScale: "1.0"
```

## Sections

### 1. Color tokens

| Token | Hex | Source URL | Used by |
|---|---|---|---|
| primary | `#CC4500` | https://ncca.ie (data/ireland/ncca_policy/*.pdf covers) | Ireland / NCCA accents (cert banners, IRB headers) |
| secondary | `#1d70b8` | https://design-system.service.gov.uk/styles/colour/ | England / DfE brand (GOV.UK link, cert authority pill) |
| tertiary | `#0065bd` | https://designsystem.gov.scot/styles/colour | Scotland / SG brand (SQA accents) |
| neutral | `#1a1a1a` | https://designsystem.gov.scot/styles/colour | Body text across all jurisdictions |
| surface | `#FAFAF7` | BDA Dyslexia Style Guide 2023 | Background (cream instead of pure white per BDA) |
| error | `#d32205` | https://designsystem.gov.scot/styles/colour | UNOFFICIAL banner + error states |
| success | `#1a7032` | https://designsystem.gov.scot/styles/colour | Verified / official-context accent |
| warning | `#fdd522` | https://designsystem.gov.scot/styles/colour | Focus background (WCAG 2.2 SC 2.4.7) |

### 2. Typography

Arial-first stack with Arimo (gov.wales Counsel General, Dec 2025) as the Welsh-diacritic-safe primary. The single stack satisfies all 8 subnations + WCAG 2.2 AA + BDA Dyslexia Style Guide + JCQ Access Arrangements 2025-26.

### 3. Spacing

8-pt grid. Mobile gutter 16px, desktop 32px.

### 4. Roundness

ROUND_TWELVE (matches the parchment / cream aesthetic).

### 5. Components

- **CertBanner**: A horizontal layout with subject header + NCCA-coloured pill + UNOFFICIAL pill
- **AuthorityStrip**: A row of 6 jurisdiction badges (IE / EN / SCT / WLS / NI / IoM) coloured per the per-subnation palette
- **SubjectCard**: Card with subject name (display) + LOs (body) + award descriptor pill
- **KeyCompetencyBar**: A 6-pill horizontal layout (Communicating / Being Creative / Working with Others / Managing Information & Thinking / Managing Myself / Staying Well)

### 6. Voice

- **Sentence case** (NOT title case) — per GOV.UK guidance
- **Plain English** — per NCCA accessibility statement
- **No italics** — per BDA Dyslexia Style Guide
- **Citation on every claim** — every generated cert cites a NCCA policy PDF page
- **"UNOFFICIAL" banner** — always present on generated artefacts

### 7. Push to Stitch

```bash
curl -X POST https://stitch.googleapis.com/v1/projects/${STITCH_PROJECT_ID}/screens:batchCreate \
  -H "X-Goog-Api-Key: ${STITCH_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "parent": "projects/${STITCH_PROJECT_ID}",
    "requests": [{
      "screen": {
        "htmlCode": {"fileContentBase64": "<base64-encoded-DESIGN.md>"},
        "screenType": "DOCUMENT",
        "isCreatedByClient": true,
        "title": "gemini_hackathon_design_system",
        "generatedBy": "UserUploadedDesignMd"
      }
    }],
    "createScreenInstances": true
  }'
```

Then call `create_design_system_from_design_md` to materialize the Material-3 tokens at the project level.

## 8. Anti-patterns (BANNED)

- ❌ Inter font (per Stitch `taste-design/SKILL.md:26`)
- ❌ Pure black `#000000` (per BDA — use `#1a1a1a`)
- ❌ AI purple / neon gradients
- ❌ "Elevate / Seamless / Unleash / Next-Gen" copy
- ❌ Fake metric cards (e.g. "99.99% UPTIME SLA")
- ❌ Centred hero layouts
- ❌ Title-case headings
- ❌ Italics for emphasis (BDA)
- ❌ Underline for emphasis (BDA)

---

## Sources (all verified)

| URL | Page |
|---|---|
| https://ncca.ie/en/accessibility-statement/ | NCCA WCAG 2.1 AA declaration |
| https://github.com/ogcio/govie-ds | gov.ie canonical design tokens (MIT) |
| https://design-system.service.gov.uk/styles/colour/ | GOV.UK functional colours + web palette |
| https://design-system.service.gov.uk/styles/typography/ | GDS Transport + responsive scale |
| https://designsystem.gov.scot/styles/colour | Scottish Government brand palette |
| https://designsystem.gov.scot/styles/typography | Roboto + responsive scale |
| https://www.jcq.org.uk/knowledge-hub/adjustments-for-candidates-with-disabilities-and-learning-difficulties/ | JCQ Access Arrangements 2025-26 |
| https://cdn.bdadyslexia.org.uk/uploads/documents/Advice/style-guide/BDA-Style-Guide-2023.pdf | BDA Dyslexia-friendly Style Guide 2023 |
| https://www.sensorytrust.org.uk/resources/guidance/designing-with-clear-and-large-print | RNIB Clear Print guidance |
| https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html | WCAG 2.2 SC 1.4.3 contrast |
| https://www.gov.je/ServiceManual/BrandDesign/Pages/Colours.aspx | Jersey official palette |
| https://www.wjec.co.uk | WJEC red (masthead + specimen PDF footers) |
| https://ccea.org.uk | CCEA navy (logo + spec PDF covers) |
| https://www.yumpu.com/en/document/view/22052354/isle-of-man-government-corporate-identity-guidelines | IoM Corporate Identity Guidelines |
| https://www.gov.wales/changes-to-the-formatting-of-printed-welsh-statutory-instruments-welsh-language-impact-assessment | Welsh Government Counsel General decision (Arimo over Helvetica) |