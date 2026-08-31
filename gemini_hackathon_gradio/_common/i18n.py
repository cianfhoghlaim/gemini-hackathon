"""gemini_hackathon_gradio._common.i18n — British Isles bilingual + multilingual.

Languages supported (in priority order):
  - en (English) — primary
  - ga (Gaeilge / Irish) — primary, the official language of Ireland
  - cy (Cymraeg / Welsh) — second-tier (Wales)
  - gd (Gàidhlig / Scottish Gaelic) — second-tier (Scotland)
  - gv (Gaelg / Manx) — second-tier (Isle of Man)

Plus 2 TODO placeholders for the other Celtic languages:
  - kw (Kernewek / Cornish) — TODO
  - br (Brezhoneg / Breton) — TODO

Per the hackathon scope: NI uses English (with Irish-medium schools
covered by `ga`); Jersey + Guernsey use English; IoM uses English with
Manx-medium schools covered by `gv`. The Celtic-language TODO languages
are scoped to a future expansion pack (see `docs/SUBNATIONS.md`).

The toggle is a Gradio Radio component whose value updates a global
`current_lang` module variable; every `translate()` call picks it up.

Mirrors `spaces/_common/i18n.py` from sruth but rewritten for the
education system (the Celtic-mythology strings are replaced with
education strings).
"""

from __future__ import annotations

from typing import Final

# Supported languages
LANGS: Final[tuple[str, ...]] = ("en", "ga", "cy", "gd", "gv", "kw", "br")
LANG_NAMES: Final[dict[str, str]] = {
    "en": "English",
    "ga": "Gaeilge",
    "cy": "Cymraeg",
    "gd": "Gàidhlig",
    "gv": "Gaelg",
    "kw": "Kernewek (TODO)",
    "br": "Brezhoneg (TODO)",
}

# Module-level current language (mutated by set_lang)
_current_lang: str = "en"


# Typed i18n strings. Keep keys in the "section.subkey" namespace.
I18N_STRINGS: dict[str, dict[str, str]] = {
    "app.title": {
        "en": "gemini_hackathon",
        "ga": "gemini_hackathon",
        "cy": "gemini_hackathon",
        "gd": "gemini_hackathon",
        "gv": "gemini_hackathon",
    },
    "app.subtitle": {
        "en": "The British Isles Education Platform — Aistear → Bunscoil → MeanScoil → Scoil Sinsearach",
        "ga": "An Ardán Oideachais Oileán na Breataine — Aistear → Bunscoil → MeanScoil → Scoil Sinsearach",
        "cy": "Llwyfan Addysg Ynysoedd Prydain — Aistear → Bunscoil → MeanScoil → Scoil Sinsearach",
        "gd": "Àrd-ogon Foghlam Eileanan Breatannach — Aistear → Bunscoil → MeanScoil → Scoil Sinsearach",
        "gv": "Arrane Lhoghaght Ellan Vretnagh — Aistear → Bunscoil → MeanScoil → Scoil Sinsearach",
    },
    "common.submit": {"en": "Submit", "ga": "Seol"},
    "common.loading": {"en": "Loading...", "ga": "A lódáil..."},
    "common.error": {
        "en": "An error occurred. Please try again.",
        "ga": "Tharla earráid. Bain triail eile as.",
    },
    "common.bilingual_toggle": {"en": "Gaeilge", "ga": "English"},
    "common.generate": {"en": "Generate", "ga": "Gin"},
    "common.clear": {"en": "Clear", "ga": "Glan"},
    "common.save": {"en": "Save", "ga": "Sábháil"},
    # Stage names
    "stage.aistear": {"en": "Aistear (Early Years 0-6)", "ga": "Aistear (Naíonáin 0-6)"},
    "stage.bunscoil": {"en": "Bunscoil (Primary 4-12)", "ga": "Bunscoil (Bunscoil 4-12)"},
    "stage.meanscoil": {
        "en": "MeanScoil (Junior Cycle 12-15)",
        "ga": "MeanScoil (Timthriall Shóisearaí 12-15)",
    },
    "stage.scoil_sinsearach": {
        "en": "Scoil Sinsearach (Senior Cycle / Leaving Certificate 15-19)",
        "ga": "Scoil Sinsearach (Timthriall Shinsearach / Teistiméireacht 15-19)",
    },
    "stage.ollscoil": {
        "en": "Ollscoil (Tertiary — Phase 2)",
        "ga": "Ollscoil (Tríú Leibhéal — Chéad 2)",
    },
    # An Scrudu (past paper heatmap) — Space 1
    "an_scrudu.title": {
        "en": "An Scrúdú — Past Paper Heatmap",
        "ga": "An Scrúdú — Léarscáil Teasa an Scrúdaithe",
    },
    "an_scrudu.subtitle": {
        "en": "BAML extracts marking schemes from Irish Leaving Cert past papers.",
        "ga": "Baintear scéimeanna marcála as scrúduithe cáilitheacha na hÉireann.",
    },
    "an_scrudu.upload_label": {
        "en": "Upload a past paper PDF (or pick from the corpus).",
        "ga": "Uaslódáil PDF scrúdaithe (nó roghnaigh ón gcorpas).",
    },
    "an_scrudu.extract_button": {
        "en": "Extract Marking Scheme",
        "ga": "Bain an Scéim Mharcála",
    },
    "an_scrudu.heatmap_caption": {
        "en": "Topic heatmap: frequency of marking points by topic & year.",
        "ga": "Léarscáil teasa: minicíocht bpointí marcála de réir ábhair & bliana.",
    },
    # Anam: Education (integration Space) — Space 4-equivalent
    "anam_education.title": {
        "en": "Anam Oideachais — The Education Integration Studio",
        "ga": "Anam Oideachais — Stiúideo Comhtháthaithe an Oideachais",
    },
    "anam_education.subtitle": {
        "en": "7 features across the 5 British Isles education stages.",
        "ga": "7 ngné trasna 5 chéim oideachais Oileán na Breataine.",
    },
    "anam_education.curriculum_map": {
        "en": "Curriculum Map (Talamh)",
        "ga": "Léarscáil Curaclaim (Talamh)",
    },
    "anam_education.chemistry_visual": {
        "en": "Chemistry Visual (Uisce)",
        "ga": "Léirshamhlú Ceimice (Uisce)",
    },
    "anam_education.exit_card": {
        "en": "Exit Card — Formative Assessment (Mac Léinn)",
        "ga": "Cárta Scoir — Measúnú Formeach (Mac Léinn)",
    },
    "anam_education.gaelscribhneoir": {
        "en": "Irish Text Quality (Tine)",
        "ga": "Cáilíocht Téacs Gaeilge (Tine)",
    },
    "anam_education.bilingual_toggle": {
        "en": "Bilingual EN/GA Toggle (Fiosraigh)",
        "ga": "Aistriúchán Dátheangach EN/GA (Fiosraigh)",
    },
    "anam_education.certificate": {
        "en": "Certificate Generation (Anam)",
        "ga": "Giniúint Teastais (Anam)",
    },
    "anam_education.skill_progression": {
        "en": "Skill Progression Ledger (Anam)",
        "ga": "Leabhar Mion-Oideas Scileanna (Anam)",
    },
    # Oideachais Mission Control — Space 5 (5-stage control)
    "mission_control.title": {
        "en": "Oideachais — Mission Control",
        "ga": "Oideachais — Rialú Misean",
    },
    "mission_control.subtitle": {
        "en": "5 educational stages of the British Isles curriculum.",
        "ga": "5 chéim oideachais de churaclam Oileán na Breataine.",
    },
    # Oideachais PDF Review
    "pdf_review.title": {
        "en": "Oideachais PDF Review",
        "ga": "Athbhreithniú PDF Oideachais",
    },
    "pdf_review.subtitle": {
        "en": "Human review of Stage-4 mismatches.",
        "ga": "Athbhreithniú daonna ar mhí-oiriúnuithe Céim 4.",
    },
    # Editorial Studio
    "editorial_studio.title": {
        "en": "Editorial Studio — the British Isles Education Workflow Canvas",
        "ga": "Stiúideo Eagarthóireachta — an Chanbhás Sreabha Oibre Oideachais Oileán na Breataine",
    },
    "editorial_studio.subtitle": {
        "en": "Drag nodes to compose the LC/JC certificate pipeline.",
        "ga": "Tarraing nóid chun píblíne teastais LC/JC a chumadh.",
    },
    # Footer
    "footer.anam_bonneagar": {
        "en": "Anam Faisnéise (Trust Signal Footer)",
        "ga": "Anam Faisnéise (Buntás Iontaobhais)",
    },
    "footer.unofficial": {
        "en": "UNOFFICIAL — NOT an NCCA-issued credential",
        "ga": "NEAMHOIFIGIÚIL — NÍ chreidiúint é ó NCCA",
    },
    "footer.generated_from": {
        "en": "Generated from 5 NCCA policy documents",
        "ga": "Ginte as 5 dhoiciméad beartais NCCA",
    },
}


def set_lang(lang: str) -> None:
    """Set the current language. Must be one of LANGS."""
    if lang not in LANGS:
        raise ValueError(f"Unknown language '{lang}'. Supported: {', '.join(LANGS)}")
    global _current_lang
    _current_lang = lang


def get_lang() -> str:
    """Get the current language code."""
    return _current_lang


def translate(key: str, lang: str | None = None, **kwargs: object) -> str:
    """Translate a key into the current (or specified) language.

    Args:
        key: The i18n key (e.g. "stage.aistear").
        lang: Optional explicit language override. Defaults to current.
        **kwargs: For keys with placeholders, e.g. translate(
            "stage.school", school="Gaelscoil Mhic Aodha").

    Returns:
        The translated string. Falls back to English, then the key itself
        if neither is available. Missing languages return the English
        string and a TODO marker.
    """
    target = lang or _current_lang
    strings = I18N_STRINGS.get(key)
    if strings is None:
        return key
    translated = strings.get(target)
    if translated is None:
        translated = strings.get("en", key)
        if target != "en":
            return f"{translated} (TODO: {target})"
    if kwargs:
        try:
            return translated.format(**kwargs)
        except (KeyError, IndexError):
            return translated
    return translated
