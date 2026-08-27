"""gemini_hackathon_gradio._common — shared library for the 5 editorial studios.

The Celtic theme is replaced with the British Isles education 5-stage palette
(see `theme.py`). The Hades Shadow-First base is preserved.

Modules (all importable without Gradio — gradio is optional):
  - theme: 5-stage palette + CSS + subnation awarding-body palette loader
  - baml_client: 3-tier LiteLLM gateway fallback chain
  - baml_pydantic_bridge: BAML → Pydantic schema mirror (per an_scrudu/extraction.py)
  - i18n: bilingual EN/GA toggle (with 5 Celtic TODO placeholders + Welsh/Gaelic/Manx)
  - pclm_emitter: PCLM-XML + minimal-PDF emitter (lifted from sruth/spaces/an_scrudu/pclm.py)
  - hlml_emitter: HLML (Heatmap Layout Markup) for LC exam-paper topic heatmaps
  - anam_bonneagar: per-Space trust-signal footer (renamed "Anam Faisnéise")
  - hf_hub_push: push generated assets to a HuggingFace dataset repo
  - demo_recorder: programmatic demo sequence recorder

Gradio-dependent symbols (apply_education_theme, GRADIO_CSS,
render_anam_bonneagar_footer) are re-exported here; importing them
without Gradio installed raises ImportError (callable only when Gradio
is in the environment).

The Celtic mythology assets (soulbound SVG, social card with Celtic knotwork)
are NOT lifted — out of scope for the education system.
"""

# Re-exports (no Gradio required at import time)
from gemini_hackathon_gradio._common.i18n import (
    LANGS,
    LANG_NAMES,
    I18N_STRINGS,
    get_lang,
    set_lang,
    translate,
)
from gemini_hackathon_gradio._common.baml_pydantic_bridge import (
    extract_via_llm,
    extract_with_fallback,
    fallback_regex,
    mirror_baml_schema,
    pydantic_to_baml_prompt_hint,
)
from gemini_hackathon_gradio._common.baml_client import (
    T1_BASE_URL,
    T1_DEFAULT_MODEL,
    T1_API_KEY,
    T2_BASE_URL,
    T2_MODEL,
    T2_API_KEY,
    T3_BASE_URL,
    T3_FALLBACK_CHAIN,
    T3_API_KEY,
    chat_complete,
    chat_complete_json,
    get_client_config,
)
from gemini_hackathon_gradio._common.hlml_emitter import (
    HLML_VERSION,
    emit_hlml_json,
    emit_hlml_pdf_bytes,
)
from gemini_hackathon_gradio._common.pclm_emitter import (
    emit_pclm_pdf_bytes,
    emit_pclm_xml,
)
from gemini_hackathon_gradio._common.hf_hub_push import (
    build_user_dataset_repo_id,
    push_assets_to_hub,
)
from gemini_hackathon_gradio._common.demo_recorder import (
    STAGE_LABELS,
    DemoSequence,
    DemoStep,
    record_interaction,
)

# Gradio-dependent re-exports (these will raise ImportError if gradio is missing,
# but only when *called* — the symbols themselves are bound).
try:
    from gemini_hackathon_gradio._common.theme import (
        ALL_TOKENS,
        EDUCATION_PALETTE,
        GRADIO_CSS,
        HADES_PALETTE,
        SUBNATION_PALETTES,
        apply_education_theme,
        stage_class,
    )
except ImportError:
    # Theme module needs Gradio for the apply_education_theme function — but the
    # constants and CSS are pure-Python and should still load.
    GRADIO_CSS = None  # type: ignore[assignment]
    apply_education_theme = None  # type: ignore[assignment]
    stage_class = None  # type: ignore[assignment]
    try:
        from gemini_hackathon_gradio._common.theme import (
            ALL_TOKENS,
            EDUCATION_PALETTE,
            HADES_PALETTE,
            SUBNATION_PALETTES,
        )
    except ImportError:
        ALL_TOKENS = None  # type: ignore[assignment]
        EDUCATION_PALETTE = None  # type: ignore[assignment]
        HADES_PALETTE = None  # type: ignore[assignment]
        SUBNATION_PALETTES = None  # type: ignore[assignment]

# Anam Bonneagar footer (also Gradio-dependent)
try:
    from gemini_hackathon_gradio._common.anam_bonneagar import (
        _DEFAULT_FOOTER_STUB,
        render_anam_bonneagar_footer,
    )
except ImportError:
    _DEFAULT_FOOTER_STUB = None  # type: ignore[assignment]
    render_anam_bonneagar_footer = None  # type: ignore[assignment]


__all__ = [
    # i18n
    "LANGS",
    "LANG_NAMES",
    "I18N_STRINGS",
    "get_lang",
    "set_lang",
    "translate",
    # baml_pydantic_bridge
    "extract_via_llm",
    "extract_with_fallback",
    "fallback_regex",
    "mirror_baml_schema",
    "pydantic_to_baml_prompt_hint",
    # baml_client
    "T1_BASE_URL",
    "T1_DEFAULT_MODEL",
    "T1_API_KEY",
    "T2_BASE_URL",
    "T2_MODEL",
    "T2_API_KEY",
    "T3_BASE_URL",
    "T3_FALLBACK_CHAIN",
    "T3_API_KEY",
    "chat_complete",
    "chat_complete_json",
    "get_client_config",
    # hlml_emitter
    "HLML_VERSION",
    "emit_hlml_json",
    "emit_hlml_pdf_bytes",
    # pclm_emitter
    "emit_pclm_pdf_bytes",
    "emit_pclm_xml",
    # hf_hub_push
    "build_user_dataset_repo_id",
    "push_assets_to_hub",
    # demo_recorder
    "STAGE_LABELS",
    "DemoSequence",
    "DemoStep",
    "record_interaction",
    # theme (Gradio-dependent — symbols may be None if Gradio missing)
    "ALL_TOKENS",
    "EDUCATION_PALETTE",
    "GRADIO_CSS",
    "HADES_PALETTE",
    "SUBNATION_PALETTES",
    "apply_education_theme",
    "stage_class",
    # anam_bonneagar (Gradio-dependent)
    "_DEFAULT_FOOTER_STUB",
    "render_anam_bonneagar_footer",
]
