"""British Isles Education 5-stage palette + Hades Shadow-First base for Gradio.

The 5-stage palette replaces the Celtic 5-element palette (Talamh / Uisce /
Tine / Aer / Anam). The 5 education stages are:

  - Aistear        (Early Years, 0-6)
  - Bunscoil       (Primary, 4-12)
  - MeanScoil      (Junior Cycle, 12-15)
  - ScoilSinsearach (Senior Cycle / Leaving Certificate, 15-19)
  - Ollscoil       (Tertiary — placeholder; full tertiary is Phase 2)

The Hades Shadow-First base is kept verbatim (it's the dark-mode
foundation that works for education context too).

Per-subnation awarding-body colours (NCCA, AQA, OCR, Pearson, CCEA,
WJEC, SQA, IoM) are loaded from `gemini_hackathon/themes/*.json` —
this module exposes them as CSS custom properties too.

The Celtic palette's RED → Aistear (early-years, dawn-orange)
                       BLUE → Bunscoil (primary, sea-blue)
                       GREEN → MeanScoil (Junior Cycle, meadow-green)
                       GOLD → Scoil Sinsearach (Leaving Cycle, harvest-gold)
                       INDIGO → Ollscoil (Tertiary, scholarship-indigo, future)

The 5-element Celtic palette is NOT imported; the 5 stages are
inspired by the same structural idea (a colour per stage) but
applied to the Irish education system, not to Celtic mythology.
"""

from __future__ import annotations

from pathlib import Path

try:
    import gradio as gr
except ImportError:
    gr = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# 5-stage education palette
# ---------------------------------------------------------------------------

EDUCATION_PALETTE: dict[str, str] = {
    # Aistear — Early Years (0-6). Dawn-orange = sunrise = start.
    "aistear": "#e8915c",
    "aistear_soft": "#f4b690",
    "aistear_ink": "#5c2c0c",
    # Bunscoil — Primary (4-12). Sea-blue = discovery = depth.
    "bunscoil": "#1e80c6",
    "bunscoil_soft": "#7ab5d8",
    "bunscoil_ink": "#0d2f4a",
    # MeanScoil — Junior Cycle (12-15). Meadow-green = growth.
    "meanscoil": "#28955e",
    "meanscoil_soft": "#7cc09c",
    "meanscoil_ink": "#0e3a23",
    # Scoil Sinsearach — Senior Cycle (15-19). Harvest-gold = achievement.
    "scoil_sinsearach": "#cc9966",
    "scoil_sinsearach_soft": "#e3c2a0",
    "scoil_sinsearach_ink": "#5c3a1a",
    # Ollscoil — Tertiary (future). Scholarship-indigo = wisdom.
    "ollscoil": "#5a4fcf",
    "ollscoil_soft": "#9b93e6",
    "ollscoil_ink": "#221e5c",
    # Common
    "stone": "#bcb8b0",          # NCCA stone gray (borders)
    "paper": "#fdfaf3",          # parchment (certificates)
    "crimson": "#a83a2a",        # Pobal DEIS crimson (safeguarding accent)
    "bronze": "#a67c52",         # seal/badge accent
}

# Hades Shadow-First base (kept verbatim from the Celtic theme — the
# dark-mode foundation works equally well for education context).
HADES_PALETTE: dict[str, str] = {
    "base": "#1d1d2f",
    "ink": "#1a1d2e",
    "blood": "#ff6e61",
    "bone": "#d8d4cc",
}


# ---------------------------------------------------------------------------
# Per-subnation awarding-body palettes (loaded from themes/*.json)
# ---------------------------------------------------------------------------

_THEMES_DIR = Path(__file__).resolve().parent.parent.parent / "themes"


def _load_subnation_palettes() -> dict[str, dict[str, str]]:
    """Load per-subnation palettes from themes/*.json.

    Returns {subnation_key: {token_name: hex}} for every palette file.
    """
    palettes: dict[str, dict[str, str]] = {}
    if not _THEMES_DIR.exists():
        return palettes
    for path in _THEMES_DIR.glob("*_palette.json"):
        import json

        key = path.stem.replace("_palette", "")
        try:
            palettes[key] = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
    return palettes


SUBNATION_PALETTES: dict[str, dict[str, str]] = _load_subnation_palettes()


# Combined token map
ALL_TOKENS: dict[str, str] = {
    **EDUCATION_PALETTE,
    **HADES_PALETTE,
    **{f"sub-{k}-{t}": v for k, tokens in SUBNATION_PALETTES.items() for t, v in tokens.items()},
}


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

GRADIO_CSS: str = """
/* 5-stage British Isles education palette + Hades base */
:root {
    /* Aistear (Early Years) */
    --aistear:        #e8915c;
    --aistear-soft:   #f4b690;
    --aistear-ink:    #5c2c0c;
    /* Bunscoil (Primary) */
    --bunscoil:       #1e80c6;
    --bunscoil-soft:  #7ab5d8;
    --bunscoil-ink:   #0d2f4a;
    /* MeanScoil (Junior Cycle) */
    --meanscoil:      #28955e;
    --meanscoil-soft: #7cc09c;
    --meanscoil-ink:  #0e3a23;
    /* Scoil Sinsearach (Senior Cycle / LC) */
    --scoil-sinsearach:      #cc9966;
    --scoil-sinsearach-soft: #e3c2a0;
    --scoil-sinsearach-ink:  #5c3a1a;
    /* Ollscoil (Tertiary, future) */
    --ollscoil:       #5a4fcf;
    --ollscoil-soft:  #9b93e6;
    --ollscoil-ink:   #221e5c;
    /* Common */
    --ncca-stone:     #bcb8b0;
    --parchment:      #fdfaf3;
    --pobal-crimson:  #a83a2a;
    --celtic-bronze:  #a67c52;
    --hades-base:     #1d1d2f;
    --hades-ink:      #1a1d2e;
    --hades-bone:     #d8d4cc;
}

/* Hades shadow-first base */
.dark {
    --body-background-fill: var(--hades-base);
    --body-text-color: var(--hades-bone);
    --block-background-fill: var(--hades-ink);
    --block-border-color: var(--celtic-bronze);
    --primary-button-background-fill: var(--scoil-sinsearach);
    --primary-button-text-color: var(--hades-ink);
    --secondary-button-background-fill: var(--meanscoil);
    --secondary-button-border-color: var(--aistear);
}

/* 5-stage accents (left-border + faint gradient) */
.stage-aistear {
    border-left: 4px solid var(--aistear);
    background: linear-gradient(90deg, rgba(232,145,92,0.08), transparent);
}
.stage-aistear h2, .stage-aistear h3 { color: var(--aistear); }

.stage-bunscoil {
    border-left: 4px solid var(--bunscoil);
    background: linear-gradient(90deg, rgba(30,128,198,0.08), transparent);
}
.stage-bunscoil h2, .stage-bunscoil h3 { color: var(--bunscoil); }

.stage-meanscoil {
    border-left: 4px solid var(--meanscoil);
    background: linear-gradient(90deg, rgba(40,149,94,0.08), transparent);
}
.stage-meanscoil h2, .stage-meanscoil h3 { color: var(--meanscoil); }

.stage-scoil-sinsearach {
    border-left: 4px solid var(--scoil-sinsearach);
    background: linear-gradient(90deg, rgba(204,153,102,0.12), transparent);
}
.stage-scoil-sinsearach h2, .stage-scoil-sinsearach h3 {
    color: var(--scoil-sinsearach);
    text-shadow: 0 0 8px rgba(204,153,102,0.4);
}

.stage-ollscoil {
    border-left: 4px solid var(--ollscoil);
    background: linear-gradient(90deg, rgba(90,79,207,0.08), transparent);
}
.stage-ollscoil h2, .stage-ollscoil h3 { color: var(--ollscoil); }

/* Bilingual EN/GA label */
.lang-toggle {
    font-family: 'Cormorant Garamond', 'Cinzel', serif;
    color: var(--scoil-sinsearach);
    cursor: pointer;
    font-size: 0.9em;
}

/* Anam Bonneagar footer (renamed "Anam Faisnéise" for education context) */
.anam-bonneagar-footer {
    font-size: 0.75em;
    color: var(--ncca-stone);
    border-top: 1px solid var(--celtic-bronze);
    padding-top: 0.5em;
    margin-top: 2em;
    font-family: 'JetBrains Mono', monospace;
}
.anam-bonneagar-footer .label { color: var(--scoil-sinsearach); }
.anam-bonneagar-footer .value { color: var(--meanscoil); }

/* Bronze borders (kept from Celtic theme) */
.bronze-border {
    border: 2px solid var(--celtic-bronze);
    border-radius: 4px;
    box-shadow:
        inset 0 0 8px rgba(204,153,102,0.2),
        0 0 4px rgba(204,153,102,0.1);
    padding: 1em;
}

/* Certificate parchment (used by W14) */
.parchment {
    background: var(--parchment);
    color: #2a1f0c;
    border: 1px solid var(--celtic-bronze);
    padding: 1.5em;
    font-family: 'Cormorant Garamond', 'Cinzel', serif;
}

/* Headings use Cinzel serif; body uses Inter */
.gradio-container h1, .gradio-container h2 {
    font-family: 'Cinzel', 'Cormorant Garamond', serif;
    color: var(--scoil-sinsearach);
    letter-spacing: 0.05em;
}
"""


def apply_education_theme():
    """Return a Gradio Theme configured with the British Isles education palette.

    Raises:
        ImportError: If Gradio is not installed.

    Usage:
        with gr.Blocks(theme=apply_education_theme(), css=GRADIO_CSS) as demo:
            ...
    """
    if gr is None:
        raise ImportError(
            "Gradio is required for apply_education_theme(); install with "
            "`pip install gradio>=5.28.0,<6.0`"
        )
    theme = gr.themes.Soft(
        primary_hue="orange",  # Aistear dawn-orange
        secondary_hue="green",  # MeanScoil meadow-green
        neutral_hue="dark",
    )
    # Override specific tokens via the .set() method if available
    try:
        theme = theme.set(
            body_background_fill="#1d1d2f",
            body_text_color="#d8d4cc",
            block_background_fill="#1a1d2e",
            block_border_color="#a67c52",
            button_primary_background_fill="#cc9966",
            button_primary_text_color="#1a1d2e",
            button_secondary_background_fill="#28955e",
            input_background_fill="#1a1d2e",
        )
    except Exception:
        # Older Gradio API - fallback
        pass
    return theme


def stage_class(stage: str) -> str:
    """Return the CSS class for a 5-stage accent.

    >>> stage_class("Aistear")
    'stage-aistear'
    >>> stage_class("primary")
    'stage-bunscoil'
    """
    norm = stage.lower().replace(" ", "-").replace("/", "-")
    if "aistear" in norm or "early" in norm or "naíonáin" in norm:
        return "stage-aistear"
    if "primary" in norm or "bunscoil" in norm or "primary" in norm:
        return "stage-bunscoil"
    if "junior" in norm or "meanscoil" in norm or "jc" == norm:
        return "stage-meanscoil"
    if "senior" in norm or "leaving" in norm or "lc" == norm or "sinsearach" in norm:
        return "stage-scoil-sinsearach"
    if "tert" in norm or "ollscoil" in norm or "university" in norm:
        return "stage-ollscoil"
    return "stage-bunscoil"  # safe default
