"""Session model for the per-subnation scoped theming.

The session binds a user to:
  - their home subnation (the primary content scope)
  - their role (student | parent | teacher) — drives the home page surfaces
  - their active subjects + cycle (a cycle like GCSE, A-Level, LC, JC, etc.)
  - the active safeguarding policy (auto-resolved from the subnation)
  - the active palette (auto-resolved from the subnation — the agent uses
    it as a voice)

The session is durable: in production it lives in Convex `userSessions`
+ BetterAuth's JWT, in dev it lives in localStorage (anonymous mode).

The five active subnations (Ireland + England default, NI/Scotland/Wales
available) + the three "future expansion pack" subnations (Jersey,
Guernsey, Isle of Man) are the only legal values for the active field.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


ActiveSubnation = Literal[
    "ireland",
    "england",
    "northern_ireland",
    "scotland",
    "wales",
    # Future expansion pack — rendered as locked "coming soon" cards.
    "jersey",
    "guernsey",
    "isle_of_man",
]
"""The eight subnations the platform knows about.

Default: `ireland` and `england` (most populous). Available: NI, Scotland,
Wales. Future expansion pack: jersey, guernsey, isle_of_man.
"""


class Role(str, Enum):
    STUDENT = "student"
    PARENT = "parent"
    TEACHER = "teacher"


class Cycle(str, Enum):
    """Cycles per subnation — each subnation has its own progression."""

    JC = "junior_cycle"
    LC = "leaving_cycle"
    GCSE = "gcse"
    A_LEVEL = "a_level"
    N5 = "national_5"
    HIGHER = "higher"
    AH = "advanced_higher"


CYCLES_PER_SUBNATION: dict[str, tuple[str, ...]] = {
    "ireland":          (Cycle.JC.value, Cycle.LC.value),
    "england":          (Cycle.GCSE.value, Cycle.A_LEVEL.value),
    "northern_ireland": (Cycle.GCSE.value, Cycle.A_LEVEL.value),
    "scotland":         (Cycle.N5.value, Cycle.HIGHER.value, Cycle.AH.value),
    "wales":            (Cycle.GCSE.value, Cycle.A_LEVEL.value),
    "jersey":           (Cycle.GCSE.value, Cycle.A_LEVEL.value),
    "guernsey":         (Cycle.GCSE.value, Cycle.A_LEVEL.value),
    "isle_of_man":      (Cycle.GCSE.value, Cycle.A_LEVEL.value),
}


# ---------------------------------------------------------------------------
# Subject catalogue
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Subject:
    """A single subject within a subnation."""

    subject_id: str
    source_key: str
    cycle: str
    name: str
    name_local: Optional[str] = None
    exam_board: Optional[str] = None
    short: Optional[str] = None


SUBJECT_CATALOGUE: tuple[Subject, ...] = (
    # Ireland — NCCA
    Subject("ncca_maths_jc",   "ncca.ie", Cycle.JC.value,  "Mathematics", name_local="Matamaitic", short="Maths"),
    Subject("ncca_maths_lc",   "ncca.ie", Cycle.LC.value,  "Mathematics", name_local="Matamaitic", short="Maths"),
    Subject("ncca_english_jc", "ncca.ie", Cycle.JC.value,  "English",    name_local="Béarla",     short="Eng"),
    Subject("ncca_english_lc", "ncca.ie", Cycle.LC.value,  "English",    name_local="Béarla",     short="Eng"),
    Subject("ncca_gaeilge_jc", "ncca.ie", Cycle.JC.value,  "Gaeilge (Irish)",                            short="Gae"),
    Subject("ncca_gaeilge_lc", "ncca.ie", Cycle.LC.value,  "Gaeilge (Irish)",                            short="Gae"),
    Subject("ncca_chem_lc",    "ncca.ie", Cycle.LC.value,  "Chemistry",                                  short="Chem"),
    Subject("ncca_phys_lc",    "ncca.ie", Cycle.LC.value,  "Physics",                                    short="Phys"),
    Subject("ncca_bio_lc",     "ncca.ie", Cycle.LC.value,  "Biology",                                    short="Bio"),
    Subject("ncca_geo_lc",     "ncca.ie", Cycle.LC.value,  "Geography",                                  short="Geo"),
    Subject("ncca_hist_lc",    "ncca.ie", Cycle.LC.value,  "History",                                    short="Hist"),
    Subject("ncca_cs_lc",      "ncca.ie", Cycle.LC.value,  "Computer Science",                           short="CS"),
    # England — AQA
    Subject("aqa_maths_gcse",    "aqa.org.uk",  Cycle.GCSE.value,    "Mathematics",                  exam_board="AQA",    short="Maths"),
    Subject("aqa_maths_alevel",  "aqa.org.uk",  Cycle.A_LEVEL.value, "Mathematics A-Level",          exam_board="AQA",    short="Maths"),
    Subject("aqa_chem_gcse",     "aqa.org.uk",  Cycle.GCSE.value,    "Chemistry GCSE",               exam_board="AQA",    short="Chem"),
    Subject("aqa_eng_alevel",    "aqa.org.uk",  Cycle.A_LEVEL.value, "English Literature A-Level",   exam_board="AQA",    short="Eng"),
    # England — OCR
    Subject("ocr_bio_alevel",    "ocr.org.uk",  Cycle.A_LEVEL.value, "Biology A-Level",              exam_board="OCR",    short="Bio"),
    Subject("ocr_phys_gcse",     "ocr.org.uk",  Cycle.GCSE.value,    "Physics GCSE",                 exam_board="OCR",    short="Phys"),
    # England — Pearson Edexcel
    Subject("pearson_fmaths",    "qualifications.pearson.com", Cycle.A_LEVEL.value, "Further Mathematics A-Level", exam_board="Pearson", short="FMaths"),
    Subject("pearson_eng_lang",  "qualifications.pearson.com", Cycle.GCSE.value,    "English Language GCSE",       exam_board="Pearson", short="Eng"),
    # Scotland — SQA
    Subject("sqa_maths_n5",      "sqa.org.uk",  Cycle.N5.value,     "Mathematics National 5",                       short="Maths"),
    Subject("sqa_maths_higher",  "sqa.org.uk",  Cycle.HIGHER.value, "Mathematics Higher",                          short="Maths"),
    Subject("sqa_phys_higher",  "sqa.org.uk",  Cycle.HIGHER.value, "Physics Higher",                              short="Phys"),
    Subject("sqa_chem_ah",      "sqa.org.uk",  Cycle.AH.value,     "Chemistry Advanced Higher",                    short="Chem"),
    # Northern Ireland — CCEA
    Subject("ccea_maths_gcse",   "ccea.org.uk", Cycle.GCSE.value,    "Mathematics GCSE",                            short="Maths"),
    Subject("ccea_rs_alevel",    "ccea.org.uk", Cycle.A_LEVEL.value, "Religious Studies A-Level",                    short="RS"),
    # Wales — WJEC
    Subject("wjec_maths_num_gcse", "wjec.co.uk", Cycle.GCSE.value,    "Mathematics — Numeracy GCSE",                 short="Maths"),
    Subject("wjec_cymraeg_alevel", "wjec.co.uk", Cycle.A_LEVEL.value, "Cymraeg (Welsh) A-Level",                     short="Cym"),
    # Jersey — expansion pack
    Subject("jersey_eng_gcse",  "gov.je/education",  Cycle.GCSE.value,    "English GCSE",                          short="Eng"),
    # Guernsey — expansion pack
    Subject("guernsey_maths_gcse", "gov.gg/education", Cycle.GCSE.value,    "Mathematics GCSE",                       short="Maths"),
    # Isle of Man — expansion pack
    Subject("iom_bio_gcse",      "gov.im/education", Cycle.GCSE.value,    "Biology GCSE",                            short="Bio"),
)


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------


@dataclass
class Session:
    """The user's active session.

    Durable: in production it lives in `Convex.userSessions`; in dev it lives
    in localStorage. The session is the load-bearing piece for per-route
    content scoping.
    """

    session_id: str
    user_id: str
    subnation: ActiveSubnation
    role: Role
    cycle: Optional[Cycle] = None
    selected_subjects: tuple[str, ...] = field(default_factory=tuple)
    safeguarding_source_key: Optional[str] = None
    palette_source_key: Optional[str] = None
    onboarded: bool = False
    created_at: Optional[str] = None
    last_used_at: Optional[str] = None

    @classmethod
    def make_default(cls, *, session_id: str, user_id: str) -> "Session":
        return cls(
            session_id=session_id,
            user_id=user_id,
            subnation="ireland",
            role=Role.STUDENT,
            cycle=Cycle.LC,
            safeguarding_source_key="gov.ie/education",
            palette_source_key="ncca.ie",
            onboarded=False,
        )

    def to_dict(self) -> dict:
        return {
            "sessionId": self.session_id,
            "userId": self.user_id,
            "subnation": self.subnation,
            "role": self.role.value,
            "cycle": self.cycle.value if self.cycle else None,
            "selectedSubjects": list(self.selected_subjects),
            "safeguardingSourceKey": self.safeguarding_source_key,
            "paletteSourceKey": self.palette_source_key,
            "onboarded": self.onboarded,
            "createdAt": self.created_at,
            "lastUsedAt": self.last_used_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Session":
        return cls(
            session_id=d["sessionId"],
            user_id=d["userId"],
            subnation=d["subnation"],
            role=Role(d["role"]),
            cycle=Cycle(d["cycle"]) if d.get("cycle") else None,
            selected_subjects=tuple(d.get("selectedSubjects", [])),
            safeguarding_source_key=d.get("safeguardingSourceKey"),
            palette_source_key=d.get("paletteSourceKey"),
            onboarded=d.get("onboarded", False),
            created_at=d.get("createdAt"),
            last_used_at=d.get("lastUsedAt"),
        )


# ---------------------------------------------------------------------------
# Subnation metadata
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SubnationMeta:
    code: ActiveSubnation
    name: str
    flag: str
    awarding_body: str
    awarding_body_url: str
    awarding_body_short: str
    cycles: tuple[str, ...]
    safeguarding_source_key: str
    palette_source_key: str
    default: bool
    available: bool
    expansion: bool
    language_primary: str
    language_secondary: str = ""


SUBNATIONS: tuple[SubnationMeta, ...] = (
    SubnationMeta(
        code="ireland", name="Ireland", flag="🇮🇪",
        awarding_body="NCCA — National Council for Curriculum and Assessment",
        awarding_body_url="https://ncca.ie",
        awarding_body_short="NCCA",
        cycles=CYCLES_PER_SUBNATION["ireland"],
        safeguarding_source_key="gov.ie/education",
        palette_source_key="ncca.ie",
        default=True, available=True, expansion=False,
        language_primary="English", language_secondary="Gaeilge",
    ),
    SubnationMeta(
        code="england", name="England", flag="🏴󠁧󠁢󠁥󠁮󠁧󠁿",
        awarding_body="AQA + OCR + Pearson Edexcel",
        awarding_body_url="https://www.gov.uk/education",
        awarding_body_short="Multiple",
        cycles=CYCLES_PER_SUBNATION["england"],
        safeguarding_source_key="gov.uk/dfe",
        palette_source_key="aqa.org.uk",
        default=True, available=True, expansion=False,
        language_primary="English",
    ),
    SubnationMeta(
        code="northern_ireland", name="Northern Ireland", flag="🇬🇧",
        awarding_body="CCEA",
        awarding_body_url="https://ccea.org.uk",
        awarding_body_short="CCEA",
        cycles=CYCLES_PER_SUBNATION["northern_ireland"],
        safeguarding_source_key="ccea.org.uk/safeguarding",
        palette_source_key="ccea.org.uk",
        default=False, available=True, expansion=False,
        language_primary="English",
    ),
    SubnationMeta(
        code="scotland", name="Scotland", flag="🏴󠁧󠁢󠁳󠁣󠁴󠁿",
        awarding_body="SQA",
        awarding_body_url="https://www.sqa.org.uk",
        awarding_body_short="SQA",
        cycles=CYCLES_PER_SUBNATION["scotland"],
        safeguarding_source_key="education.gov.scot",
        palette_source_key="sqa.org.uk",
        default=False, available=True, expansion=False,
        language_primary="English",
    ),
    SubnationMeta(
        code="wales", name="Wales", flag="🏴󠁧󠁢󠁷󠁬󠁳󠁿",
        awarding_body="WJEC",
        awarding_body_url="https://www.wjec.co.uk",
        awarding_body_short="WJEC",
        cycles=CYCLES_PER_SUBNATION["wales"],
        safeguarding_source_key="gov.wales/education",
        palette_source_key="wjec.co.uk",
        default=False, available=True, expansion=False,
        language_primary="English", language_secondary="Cymraeg",
    ),
    # Future expansion pack
    SubnationMeta(
        code="jersey", name="Jersey", flag="🇯🇪",
        awarding_body="States of Jersey",
        awarding_body_url="https://www.gov.je/education",
        awarding_body_short="Jersey",
        cycles=CYCLES_PER_SUBNATION["jersey"],
        safeguarding_source_key="gov.je/education",
        palette_source_key="gov.je/education",
        default=False, available=False, expansion=True,
        language_primary="English", language_secondary="French",
    ),
    SubnationMeta(
        code="guernsey", name="Guernsey", flag="🇬🇬",
        awarding_body="States of Guernsey",
        awarding_body_url="https://www.gov.gg/education",
        awarding_body_short="Guernsey",
        cycles=CYCLES_PER_SUBNATION["guernsey"],
        safeguarding_source_key="gov.gg/education",
        palette_source_key="gov.gg/education",
        default=False, available=False, expansion=True,
        language_primary="English",
    ),
    SubnationMeta(
        code="isle_of_man", name="Isle of Man", flag="🇮🇲",
        awarding_body="Isle of Man Government — DESC",
        awarding_body_url="https://www.gov.im/education",
        awarding_body_short="Isle of Man",
        cycles=CYCLES_PER_SUBNATION["isle_of_man"],
        safeguarding_source_key="gov.im/education",
        palette_source_key="gov.im/education",
        default=False, available=False, expansion=True,
        language_primary="English", language_secondary="Manx Gaelic",
    ),
)


SUBNATION_BY_CODE: dict[str, SubnationMeta] = {s.code: s for s in SUBNATIONS}
ACTIVE_SUBNATIONS: tuple[SubnationMeta, ...] = tuple(s for s in SUBNATIONS if s.available)
DEFAULT_SUBNATIONS: tuple[SubnationMeta, ...] = tuple(s for s in SUBNATIONS if s.default)
AVAILABLE_SUBNATIONS: tuple[SubnationMeta, ...] = tuple(s for s in SUBNATIONS if s.available and not s.default)
EXPANSION_SUBNATIONS: tuple[SubnationMeta, ...] = tuple(s for s in SUBNATIONS if s.expansion)
PALETTES_PER_JURISDICTION: dict[str, str] = {s.code: s.palette_source_key for s in SUBNATIONS}
DEFAULT_PALETTE_PER_SUBNATION: dict[str, str] = PALETTES_PER_JURISDICTION


def is_valid_role(value: str) -> bool:
    try:
        Role(value)
        return True
    except ValueError:
        return False


def is_valid_cycle(value: str) -> bool:
    try:
        Cycle(value)
        return True
    except ValueError:
        return False


def is_valid_subject(value: str) -> bool:
    return any(s.subject_id == value for s in SUBJECT_CATALOGUE)


def is_active_subnation(value: str) -> bool:
    return value in {s.code for s in ACTIVE_SUBNATIONS}


def is_expansion_subnation(value: str) -> bool:
    return value in {s.code for s in EXPANSION_SUBNATIONS}


def list_subnations() -> tuple[SubnationMeta, ...]:
    return SUBNATIONS


def list_active_subnations() -> tuple[SubnationMeta, ...]:
    return ACTIVE_SUBNATIONS


def list_expansion_pack_subnations() -> tuple[SubnationMeta, ...]:
    return EXPANSION_SUBNATIONS


def get_subnation_meta(code: str) -> SubnationMeta:
    if code not in SUBNATION_BY_CODE:
        raise KeyError(f"Unknown subnation: {code!r}")
    return SUBNATION_BY_CODE[code]


def subjects_for(subnation: str, cycle: Optional[str] = None) -> list[Subject]:
    """Return the subjects for a given subnation (and optionally cycle)."""
    out = [s for s in SUBJECT_CATALOGUE if s.source_key == PALETTES_PER_JURISDICTION.get(subnation, "")]
    if cycle is not None:
        out = [s for s in out if s.cycle == cycle]
    return out
