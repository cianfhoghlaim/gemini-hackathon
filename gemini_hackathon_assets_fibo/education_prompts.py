"""gemini_hackathon_assets_fibo.education_prompts — the 14-subject × 5-stage prompt bank.

Lifted from `cianfhoghlaim/docs/sruth/tuath/asset_generation/fibo/education_fibo.py`
(the 8 NCCA subject prompt templates) and extended to:
  - 8 NCCA LC subjects (mathematics, applied_mathematics, chemistry, geography,
    history, english, gaeilge, computer_science)
  - 6 NCCA-adjacent subjects (accounting, biology, business, french,
    irish_t2, physics)
  - 5 stage defaults (aistear / bunscoil / meanscoil /
    scoil_sinsearach / ollscoil)

The Celtic-mythology prompts (La Tène / Ogham / Knotwork / etc.)
are NOT lifted — out of scope for the education system.

Each prompt is a JSON-serialisable dict consumed by the FIBO JSON
emitter. The assets.py module (W4) builds the FIBO config from
a CurriculumConcept + the chosen SubjectStyle + stage.
"""

from __future__ import annotations

from typing import Any


# The 14 NCCA LC subjects (the canonical subject list per W7 registry)
NCCA_LC_SUBJECTS: tuple[str, ...] = (
    "mathematics", "applied_mathematics", "chemistry", "geography",
    "history", "english", "gaeilge", "computer_science",
    "accounting", "biology", "business", "french",
    "irish_t2", "physics",
)

# The 5 British Isles education stages
FIVE_STAGES: tuple[str, ...] = (
    "aistear", "bunscoil", "meanscoil", "scoil_sinsearach", "ollscoil",
)


# The per-subject prompt templates (replaces the 6 Celtic styles)
# Each prompt is a JSON-serialisable dict with the same shape as the
# `FIBO_CONFIG` BAML function output (gemini_hackathon_assets_fibo.schemas.FiboConfig).
EDUCATION_FIBO_PROMPTS: dict[str, dict[str, Any]] = {
    # 8 NCCA subjects
    "mathematics": {
        "title": "Mathematics Educational Asset",
        "short_description": (
            "Irish Leaving Certificate Mathematics visual — equations, "
            "graphs, geometric diagrams, or statistical plots"
        ),
        "visual_cue": (
            "Mathematical typography (CMU Serif / Computer Modern), "
            "graph paper texture, blue ink, clean white background"
        ),
        "color_palette": [
            "subject_mathematics_blue", "ncca_stone_grey",
            "scotland_sqa_blue", "england_aqa_purple",
        ],
        "font_style": "CMU Serif",
        "background": "graph paper (light grey grid on white)",
        "typical_diagrams": [
            "equation render", "function plot", "geometric shape",
            "statistical distribution", "matrix array",
        ],
    },
    "applied_mathematics": {
        "title": "Applied Mathematics Educational Asset",
        "short_description": (
            "Irish Leaving Certificate Applied Mathematics — mechanics, "
            "statistics, modelling"
        ),
        "visual_cue": (
            "Mathematical typography with applied context (mechanics diagrams, "
            "statistical charts, real-world scenarios)"
        ),
        "color_palette": [
            "subject_mathematics_blue", "scotland_sqa_blue",
            "meanscoil_green",
        ],
        "font_style": "CMU Serif",
        "background": "white with faint mathematical grid",
        "typical_diagrams": [
            "force diagram", "projectile motion", "statistical inference",
            "linear regression", "particle collision",
        ],
    },
    "chemistry": {
        "title": "Chemistry Educational Asset",
        "short_description": (
            "Irish Leaving Certificate Chemistry — molecular structures, "
            "apparatus diagrams, reaction pathways"
        ),
        "visual_cue": (
            "CPK-colored atoms (C=black, O=red, H=white, N=blue, S=yellow), "
            "laboratory glassware, reaction arrows"
        ),
        "color_palette": [
            "cpk_atoms", "subject_chemistry_orange", "england_aqa_purple",
            "meanscoil_green",
        ],
        "font_style": "CMU Serif",
        "background": "white laboratory sheet",
        "typical_diagrams": [
            "lewis_structure", "ball_and_stick", "skeletal_formula",
            "reaction_equation", "energy_diagram", "apparatus_setup",
        ],
    },
    "geography": {
        "title": "Geography Educational Asset",
        "short_description": (
            "Irish Leaving Certificate Geography — maps, climate graphs, "
            "geological diagrams, population pyramids"
        ),
        "visual_cue": (
            "Topographic map contours, blue (water), green (vegetation), "
            "brown (relief), contour lines, grid references"
        ),
        "color_palette": [
            "topographic_green", "ocean_blue", "relief_brown",
            "subject_geography_orange",
        ],
        "font_style": "Inter",
        "background": "topographic map texture",
        "typical_diagrams": [
            "choropleth_map", "climate_graph", "population_pyramid",
            "geological_cross_section", "river_system",
        ],
    },
    "history": {
        "title": "History Educational Asset",
        "short_description": (
            "Irish Leaving Certificate History — primary sources, "
            "chronologies, maps of events"
        ),
        "visual_cue": (
            "Sepia-toned historical documents, parchment texture, "
            "handwritten script style, period-accurate typography"
        ),
        "color_palette": [
            "parchment", "sepia_brown", "ink_black",
            "scoil_sinsearach_gold",
        ],
        "font_style": "Cormorant Garamond (serif)",
        "background": "aged parchment",
        "typical_diagrams": [
            "timeline", "primary_source_excerpt", "historical_map",
            "event_diagram", "cause_and_effect",
        ],
    },
    "english": {
        "title": "English Educational Asset",
        "short_description": (
            "Irish Leaving Certificate English — literary extracts, "
            "comparative tables, textual analysis"
        ),
        "visual_cue": (
            "Clean serif typography on cream paper, "
            "marginalia annotations, literary quotations"
        ),
        "color_palette": [
            "parchment", "ink_black", "margin_red",
            "subject_english_burgundy",
        ],
        "font_style": "Cormorant Garamond (serif)",
        "background": "cream paper texture",
        "typical_diagrams": [
            "comparative_table", "quote_extract", "theme_map",
            "character_diagram", "plot_arc",
        ],
    },
    "gaeilge": {
        "title": "Gaeilge Educational Asset",
        "short_description": (
            "Irish Leaving Certificate Gaeilge — Irish-language extracts, "
            "literary analysis, grammar diagrams"
        ),
        "visual_cue": (
            "Trinity College Dublin typeface style, Celtic interlace "
            "borders, Irish-language typography"
        ),
        "color_palette": [
            "subject_gaeilge_green", "trinity_cream", "celtic_gold",
            "scoil_sinsearach_gold",
        ],
        "font_style": "Gaelic / Cló Gaelach typography",
        "background": "aged Celtic manuscript",
        "typical_diagrams": [
            "irish_quote", "grammar_table", "celtic_interlace_border",
            "seanfhocail_collection",
        ],
    },
    "computer_science": {
        "title": "Computer Science Educational Asset",
        "short_description": (
            "Irish Leaving Certificate Computer Science — algorithms, "
            "data structures, computational flow"
        ),
        "visual_cue": (
            "Monospace code font (Fira Code / JetBrains Mono), "
            "flowchart symbols, UML notation, blue accent"
        ),
        "color_palette": [
            "code_background_dark", "syntax_blue", "syntax_green",
            "syntax_yellow",
        ],
        "font_style": "Fira Code / JetBrains Mono",
        "background": "IDE dark theme or white",
        "typical_diagrams": [
            "flowchart", "pseudocode_block", "data_structure_diagram",
            "recursion_tree", "complexity_graph",
        ],
    },
    # 6 NCCA-adjacent subjects
    "accounting": {
        "title": "Accounting Educational Asset",
        "short_description": (
            "Irish Leaving Certificate Accounting — ledger entries, "
            "financial statements, ratio analysis"
        ),
        "visual_cue": (
            "Tabular formatting, green (assets) / red (liabilities) "
            "colour convention, ledger paper texture"
        ),
        "color_palette": ["accounting_green", "accounting_red", "ledger_grey"],
        "font_style": "CMU Serif",
        "background": "ledger paper",
        "typical_diagrams": [
            "t_account", "balance_sheet", "trial_balance",
            "ratio_analysis_chart", "cash_flow_statement",
        ],
    },
    "biology": {
        "title": "Biology Educational Asset",
        "short_description": (
            "Irish Leaving Certificate Biology — cellular structures, "
            "ecosystems, genetics, physiology"
        ),
        "visual_cue": (
            "Cell membrane (phospholipid bilayer), DNA double helix, "
            "ecological pyramid, microscope lens effect"
        ),
        "color_palette": [
            "membrane_pink", "dna_blue", "chlorophyll_green",
            "subject_biology_green",
        ],
        "font_style": "Inter",
        "background": "white lab slide",
        "typical_diagrams": [
            "cell_diagram", "dna_helix", "ecosystem_pyramid",
            "heart_diagram", "calvin_cycle", "punnett_square",
        ],
    },
    "business": {
        "title": "Business Educational Asset",
        "short_description": (
            "Irish Leaving Certificate Business — SWOT analysis, "
            "org charts, business model canvas"
        ),
        "visual_cue": (
            "Corporate slide template, blue accent, infographic style, "
            "sans-serif typography"
        ),
        "color_palette": [
            "business_blue", "subject_business_grey", "accent_orange",
        ],
        "font_style": "Inter",
        "background": "white corporate",
        "typical_diagrams": [
            "swot_grid", "org_chart", "business_model_canvas",
            "porter_5_forces", "value_chain",
        ],
    },
    "french": {
        "title": "French Educational Asset",
        "short_description": (
            "Irish Leaving Certificate French — literary extracts, "
            "grammar, French cultural references"
        ),
        "visual_cue": (
            "Garamond typography on cream paper, French tricolour accent, "
            "Belle Époque decorative motifs"
        ),
        "color_palette": [
            "french_blue", "french_white", "french_red",
            "parchment_cream",
        ],
        "font_style": "Garamond",
        "background": "aged French paper",
        "typical_diagrams": [
            "french_quote", "grammar_table", "tense_conjugation",
            "literary_timeline", "verb_conjugation_chart",
        ],
    },
    "irish_t2": {
        "title": "Irish T2 Educational Asset",
        "short_description": (
            "Irish Leaving Certificate Irish T2 — "
            "non-Gaeltacht-learner pathway, simplified extracts"
        ),
        "visual_cue": (
            "Modern Irish typography, contrast colours for accessibility, "
            "bilingual EN/GA annotations"
        ),
        "color_palette": [
            "subject_gaeilge_green", "english_blue",
            "high_contrast_white",
        ],
        "font_style": "Gaelic / Cló Gaelach typography",
        "background": "white",
        "typical_diagrams": [
            "bilingual_quote", "t2_vocabulary_table",
            "t2_grammar_summary", "t2_simple_literary_extract",
        ],
    },
    "physics": {
        "title": "Physics Educational Asset",
        "short_description": (
            "Irish Leaving Certificate Physics — forces, energy, "
            "circuits, waves, particle diagrams"
        ),
        "visual_cue": (
            "Chalkboard or whiteboard style, blue (vectors) + red (scalars) "
            "+ green (energy), physics symbols"
        ),
        "color_palette": [
            "physics_chalkboard_dark", "vector_blue", "scalar_red",
            "energy_green",
        ],
        "font_style": "CMU Serif",
        "background": "chalkboard or white",
        "typical_diagrams": [
            "force_diagram", "circuit_diagram", "ray_optics",
            "wave_diagram", "particle_track", "field_diagram",
        ],
    },
}


def get_subject_prompt_template(subject_slug: str) -> dict[str, Any]:
    """Return the per-subject FIBO prompt template.

    Falls back to a generic educational template if the subject isn't
    in the registry.
    """
    if subject_slug in EDUCATION_FIBO_PROMPTS:
        return dict(EDUCATION_FIBO_PROMPTS[subject_slug])
    return {
        "title": f"{subject_slug.replace('_', ' ').title()} Educational Asset",
        "short_description": (
            f"British Isles education visual for the {subject_slug} subject"
        ),
        "visual_cue": "Clean educational typography on white background",
        "color_palette": ["ncca_stone_grey"],
        "font_style": "Inter",
        "background": "white",
        "typical_diagrams": ["diagram", "table", "chart"],
    }


def get_stage_modifier(stage: str) -> dict[str, Any]:
    """Return the per-stage modifier that tweaks the per-subject prompt.

    The stage modifier adjusts visual complexity + label style:
      - aistear (Early Years): high visual contrast, large labels, simple shapes
      - bunscoil (Primary): bright colours, friendly typography
      - meanscoil (Junior Cycle): balanced visual, medium complexity
      - scoil_sinsearach (Senior Cycle / LC): professional, examination-quality
      - ollscoil (Tertiary): academic, dense, citation-ready
    """
    stage_modifiers = {
        "aistear": {
            "complexity": "very low",
            "label_style": "large, friendly, sans-serif (Inter)",
            "visual_density": "high contrast, minimal detail",
        },
        "bunscoil": {
            "complexity": "low",
            "label_style": "friendly sans-serif (Inter)",
            "visual_density": "bright, approachable",
        },
        "meanscoil": {
            "complexity": "medium",
            "label_style": "sans-serif (Inter)",
            "visual_density": "balanced, exam-prep",
        },
        "scoil_sinsearach": {
            "complexity": "high",
            "label_style": "serif (Cormorant Garamond)",
            "visual_density": "professional, examination-quality",
        },
        "ollscoil": {
            "complexity": "very high",
            "label_style": "academic serif (Cormorant Garamond)",
            "visual_density": "dense, citation-ready",
        },
    }
    return stage_modifiers.get(stage, stage_modifiers["scoil_sinsearach"])


__all__ = [
    "NCCA_LC_SUBJECTS",
    "FIVE_STAGES",
    "EDUCATION_FIBO_PROMPTS",
    "get_subject_prompt_template",
    "get_stage_modifier",
]
