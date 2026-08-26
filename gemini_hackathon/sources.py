"""
gemini_hackathon.sources — the jurisdiction/board split.

The earlier theming-only project conflated two axes. Per
openspec/specs/bie-8-jurisdictions/spec.md the canonical British
Isles has 8 jurisdictions, with England splitting into 3 boards.
This module surfaces both axes explicitly so the per-jurisdiction
theming, the per-board marking scheme lookup, and the cross-jurisdiction
resource discovery all have a single source of truth.

Public surface:
    JURISDICTIONS    — the 8 subnations
    BOARDS           — the 10 awarding bodies
    SUBJECTS         — per (jurisdiction, board) -> [subject,...]
    list_jurisdictions(), list_boards(), get_jurisdiction_meta(), get_board_meta()
    public_roster()  — every (jurisdiction, board) the project surfaces publicly
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

JurisdictionCode = Literal[
    "ireland",
    "england",
    "scotland",
    "wales",
    "northern_ireland",
    "jersey",
    "guernsey",
    "isle_of_man",
]

BoardCode = Literal[
    "ncca",       # Ireland
    "aqa",        # England
    "ocr",        # England
    "pearson",    # England
    "sqa",        # Scotland
    "wjec",       # Wales
    "ccea",       # Northern Ireland
    "jersey_ceb", # Jersey (Conférence Éducative de Bretagne ?; placeholder)
    "guernsey_esc", # Guernsey (placeholder)
    "iom_desc",   # Isle of Man Department of Education, Sport and Culture
]


@dataclass(frozen=True)
class JurisdictionMeta:
    code: JurisdictionCode
    name: str
    flag: str
    default_cycle: str
    cycles: tuple[str, ...]
    language_primary: str
    language_optional: str = ""
    awarding_bodies: tuple[str, ...] = ()
    safeguarding_source_key: str = ""
    palette_source_key: str = ""
    official_url: str = ""


@dataclass(frozen=True)
class BoardMeta:
    code: BoardCode
    name: str
    jurisdiction: JurisdictionCode
    official_url: str = ""


@dataclass(frozen=True)
class Subject:
    jurisdiction: JurisdictionCode
    board: BoardCode
    slug: str
    name: str
    cycle: str
    syllabus_url: str = ""
    is_welsh_medium: bool = False


# ---------------------------------------------------------------------------
# Jurisdictions (8)
# ---------------------------------------------------------------------------

JURISDICTIONS: tuple[JurisdictionMeta, ...] = (
    JurisdictionMeta(
        code="ireland",
        name="Ireland",
        flag="🇮🇪",
        default_cycle="leaving_cycle",
        cycles=("junior_cycle", "leaving_cycle"),
        language_primary="English",
        language_optional="Gaeilge (Irish)",
        awarding_bodies=("ncca",),
        safeguarding_source_key="gov.ie/education",
        palette_source_key="ncca.ie",
        official_url="https://ncca.ie",
    ),
    JurisdictionMeta(
        code="england",
        name="England",
        flag="🏴󠁧󠁢󠁥󠁮󠁧󠁿",
        default_cycle="a_level",
        cycles=("gcse", "a_level"),
        language_primary="English",
        awarding_bodies=("aqa", "ocr", "pearson"),
        safeguarding_source_key="gov.uk/dfe",
        palette_source_key="aqa.org.uk",
        official_url="https://www.gov.uk/education",
    ),
    JurisdictionMeta(
        code="scotland",
        name="Scotland",
        flag="🏴󠁧󠁢󠁳󠁣󠁴󠁿",
        default_cycle="higher",
        cycles=("national_5", "higher", "advanced_higher"),
        language_primary="English",
        awarding_bodies=("sqa",),
        safeguarding_source_key="education.gov.scot",
        palette_source_key="sqa.org.uk",
        official_url="https://www.sqa.org.uk",
    ),
    JurisdictionMeta(
        code="wales",
        name="Wales",
        flag="🏴󠁧󠁢󠁷󠁬󠁳󠁿",
        default_cycle="a_level",
        cycles=("gcse", "a_level"),
        language_primary="English",
        language_optional="Cymraeg (Welsh)",
        awarding_bodies=("wjec",),
        safeguarding_source_key="gov.wales/education",
        palette_source_key="wjec.co.uk",
        official_url="https://www.wjec.co.uk",
    ),
    JurisdictionMeta(
        code="northern_ireland",
        name="Northern Ireland",
        flag="🇬🇧",
        default_cycle="gcse",
        cycles=("gcse", "a_level"),
        language_primary="English",
        awarding_bodies=("ccea",),
        safeguarding_source_key="ccea.org.uk/safeguarding",
        palette_source_key="ccea.org.uk",
        official_url="https://ccea.org.uk",
    ),
    JurisdictionMeta(
        code="jersey",
        name="Jersey",
        flag="🇯🇪",
        default_cycle="gcse",
        cycles=("gcse", "a_level"),
        language_primary="English",
        language_optional="French (Baccalauréat hybrid)",
        awarding_bodies=("jersey_ceb",),
        safeguarding_source_key="gov.je/education",
        palette_source_key="gov.je/education",
        official_url="https://www.gov.je/education",
    ),
    JurisdictionMeta(
        code="guernsey",
        name="Guernsey",
        flag="🇬🇬",
        default_cycle="gcse",
        cycles=("gcse", "a_level"),
        language_primary="English",
        awarding_bodies=("guernsey_esc",),
        safeguarding_source_key="gov.gg/education",
        palette_source_key="gov.gg/education",
        official_url="https://www.gov.gg/education",
    ),
    JurisdictionMeta(
        code="isle_of_man",
        name="Isle of Man",
        flag="🇮🇲",
        default_cycle="gcse",
        cycles=("gcse", "a_level"),
        language_primary="English",
        language_optional="Manx Gaelic",
        awarding_bodies=("iom_desc",),
        safeguarding_source_key="gov.im/education",
        palette_source_key="gov.im/education",
        official_url="https://www.gov.im/education",
    ),
)


# ---------------------------------------------------------------------------
# Boards (10)
# ---------------------------------------------------------------------------

BOARDS: tuple[BoardMeta, ...] = (
    BoardMeta(code="ncca",       name="NCCA",                                       jurisdiction="ireland",          official_url="https://ncca.ie"),
    BoardMeta(code="aqa",        name="AQA",                                        jurisdiction="england",          official_url="https://www.aqa.org.uk"),
    BoardMeta(code="ocr",        name="OCR",                                        jurisdiction="england",          official_url="https://www.ocr.org.uk"),
    BoardMeta(code="pearson",    name="Pearson Edexcel",                            jurisdiction="england",          official_url="https://qualifications.pearson.com"),
    BoardMeta(code="sqa",        name="SQA",                                        jurisdiction="scotland",         official_url="https://www.sqa.org.uk"),
    BoardMeta(code="wjec",       name="WJEC",                                       jurisdiction="wales",            official_url="https://www.wjec.co.uk"),
    BoardMeta(code="ccea",       name="CCEA",                                       jurisdiction="northern_ireland", official_url="https://ccea.org.uk"),
    BoardMeta(code="jersey_ceb", name="Jersey Education Department",                jurisdiction="jersey",           official_url="https://www.gov.je/education"),
    BoardMeta(code="guernsey_esc", name="Guernsey Education Services",              jurisdiction="guernsey",         official_url="https://www.gov.gg/education"),
    BoardMeta(code="iom_desc",    name="Isle of Man DESC",                          jurisdiction="isle_of_man",      official_url="https://www.gov.im/education"),
)


# ---------------------------------------------------------------------------
# Subjects per (jurisdiction, board)
# ---------------------------------------------------------------------------

SUBJECTS: tuple[Subject, ...] = (
    # Ireland — NCCA
    Subject("ireland", "ncca", "mathematics_jc", "Mathematics",   "junior_cycle"),
    Subject("ireland", "ncca", "mathematics_lc", "Mathematics",   "leaving_cycle"),
    Subject("ireland", "ncca", "english_jc",    "English",      "junior_cycle"),
    Subject("ireland", "ncca", "english_lc",    "English",      "leaving_cycle"),
    Subject("ireland", "ncca", "gaeilge_jc",    "Gaeilge",      "junior_cycle"),
    Subject("ireland", "ncca", "gaeilge_lc",    "Gaeilge",      "leaving_cycle"),
    Subject("ireland", "ncca", "chemistry_lc",  "Chemistry",    "leaving_cycle"),
    Subject("ireland", "ncca", "physics_lc",    "Physics",      "leaving_cycle"),
    Subject("ireland", "ncca", "biology_lc",    "Biology",      "leaving_cycle"),
    Subject("ireland", "ncca", "geography_lc",  "Geography",    "leaving_cycle"),
    Subject("ireland", "ncca", "history_lc",    "History",      "leaving_cycle"),
    Subject("ireland", "ncca", "computer_science_lc", "Computer Science", "leaving_cycle"),

    # England — AQA
    Subject("england", "aqa",     "aqa-maths-gcse",       "Mathematics",      "gcse"),
    Subject("england", "aqa",     "aqa-maths-alevel",     "Mathematics A-Level", "a_level"),
    Subject("england", "aqa",     "aqa-chemistry-gcse",   "Chemistry GCSE",  "gcse"),
    Subject("england", "aqa",     "aqa-english-alevel",   "English Lit A-Level", "a_level"),

    # England — OCR
    Subject("england", "ocr",     "ocr-biology-alevel",   "Biology A-Level", "a_level"),
    Subject("england", "ocr",     "ocr-physics-gcse",     "Physics GCSE",  "gcse"),

    # England — Pearson
    Subject("england", "pearson", "pearson-fmaths",      "Further Maths A-Level", "a_level"),
    Subject("england", "pearson", "pearson-eng-lang",   "English Language GCSE", "gcse"),

    # Scotland — SQA
    Subject("scotland", "sqa",     "sqa-maths-n5",        "Mathematics N5", "national_5"),
    Subject("scotland", "sqa",     "sqa-maths-higher",    "Mathematics Higher", "higher"),
    Subject("scotland", "sqa",     "sqa-physics-higher",  "Physics Higher", "higher"),
    Subject("scotland", "sqa",     "sqa-chemistry-ah",    "Chemistry AH", "advanced_higher"),

    # Northern Ireland — CCEA
    Subject("northern_ireland", "ccea", "ccea-maths-gcse", "Mathematics GCSE", "gcse"),
    Subject("northern_ireland", "ccea", "ccea-rs-alevel",  "Religious Studies A-Level", "a_level"),

    # Wales — WJEC
    Subject("wales", "wjec",      "wjec-maths-num-gcse",  "Maths - Numeracy GCSE", "gcse"),
    Subject("wales", "wjec",      "wjec-cymraeg-alevel", "Cymraeg A-Level", "a_level", is_welsh_medium=True),

    # Jersey
    Subject("jersey", "jersey_ceb", "jersey-eng-gcse", "English GCSE", "gcse"),

    # Guernsey
    Subject("guernsey", "guernsey_esc", "guernsey-maths-gcse", "Mathematics GCSE", "gcse"),

    # Isle of Man
    Subject("isle_of_man", "iom_desc", "iom-bio-gcse", "Biology GCSE", "gcse"),
)


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

JURISDICTIONS_BY_CODE: dict[str, JurisdictionMeta] = {j.code: j for j in JURISDICTIONS}
BOARDS_BY_CODE: dict[str, BoardMeta] = {b.code: b for b in BOARDS}


def list_jurisdictions() -> tuple[JurisdictionMeta, ...]:
    return JURISDICTIONS


def list_boards() -> tuple[BoardMeta, ...]:
    return BOARDS


def get_jurisdiction_meta(code: str) -> JurisdictionMeta:
    if code not in JURISDICTIONS_BY_CODE:
        raise KeyError(f"Unknown jurisdiction: {code!r}")
    return JURISDICTIONS_BY_CODE[code]


def get_board_meta(code: str) -> BoardMeta:
    if code not in BOARDS_BY_CODE:
        raise KeyError(f"Unknown board: {code!r}")
    return BOARDS_BY_CODE[code]


def subjects_for(jurisdiction: str, board: str | None = None) -> list[Subject]:
    """Return all subjects for a jurisdiction (and optionally a board)."""
    out: list[Subject] = []
    for s in SUBJECTS:
        if s.jurisdiction != jurisdiction:
            continue
        if board is not None and s.board != board:
            continue
        out.append(s)
    return out


def public_roster() -> list[dict[str, str]]:
    """Stable (jurisdiction, board) surface for docs + UI.

    Returns one entry per (jurisdiction, board) pair, excluding the
    Jersey / Guernsey / Isle of Man "future expansion pack" entries
    from the *primary* surface (they remain accessible via the
    archipelago route). Each entry has the keys: jurisdiction, board,
    subject_count, palette, safeguarding.
    """
    out: list[dict[str, str]] = []
    for s in SUBJECTS:
        if s.jurisdiction in {"jersey", "guernsey", "isle_of_man"}:
            continue
        j = get_jurisdiction_meta(s.jurisdiction)
        b = get_board_meta(s.board)
        out.append({
            "jurisdiction":   j.name,
            "jurisdiction_code": j.code,
            "board":           b.name,
            "board_code":      b.code,
            "cycle":           s.cycle,
            "subject":         s.name,
        })
    return out


__all__ = [
    "JURISDICTIONS",
    "BOARDS",
    "SUBJECTS",
    "JURISDICTIONS_BY_CODE",
    "BOARDS_BY_CODE",
    "JurisdictionMeta",
    "BoardMeta",
    "Subject",
    "JurisdictionCode",
    "BoardCode",
    "list_jurisdictions",
    "list_boards",
    "get_jurisdiction_meta",
    "get_board_meta",
    "subjects_for",
    "public_roster",
]
