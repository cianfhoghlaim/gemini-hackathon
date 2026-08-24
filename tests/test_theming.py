"""Tests for ``gemini_hackathon.theming`` — the palette loader.

13 tests, one per requirement:

* 8 tests for the 8 BI jurisdiction palettes (NCCA / AQA / OCR /
  Pearson / SQA / WJEC / CCEA / IoM).
* 1 test for all 5 safeguarding palettes together.
* 1 test for the missing-palette returns-None contract.
* 1 test for the ``list_all_palettes`` returns-13 invariant.
* 1 test for the ``css_variables`` property contract.
* 1 test for the ``extract_source_palette_from_pdf`` stub.

All tests use the :func:`tmp_themes_dir` fixture from
:mod:`tests.conftest` so they don't depend on the canonical
``themes/`` directory on disk (which may be a subset).
"""

from __future__ import annotations

import pytest

from gemini_hackathon.theming import (
    JURISDICTIONS,
    SAFEGUARDING_SOURCES,
    Palette,
    extract_source_palette_from_pdf,
    list_all_palettes,
    load_palette,
)


# ---------------------------------------------------------------------------
# 8 jurisdiction palettes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "source_key,expected_jurisdiction",
    [
        ("ncca.ie", "Ireland"),
        ("aqa.org.uk", "England"),
        ("ocr.org.uk", "England"),
        ("qualifications.pearson.com", "England"),
        ("sqa.org.uk", "Scotland"),
        ("wjec.co.uk", "Wales"),
        ("ccea.org.uk", "Northern Ireland"),
        ("gov.im/education", "Isle of Man"),
    ],
)
def test_load_each_of_8_jurisdiction_palettes(
    tmp_themes_dir: object,
    source_key: str,
    expected_jurisdiction: str,
) -> None:
    """Each of the 8 BI jurisdiction palettes loads successfully.

    Asserts:

    * :func:`load_palette` returns a :class:`Palette` (not ``None``).
    * ``palette.source_key`` round-trips.
    * ``palette.jurisdiction`` matches the canonical mapping.
    * ``palette.css_variables`` has all 7 keys.
    """
    palette = load_palette(source_key)
    assert palette is not None, f"load_palette({source_key!r}) returned None"
    assert isinstance(palette, Palette)
    assert palette.source_key == source_key
    assert palette.jurisdiction == expected_jurisdiction
    # Hex codes must look like #RRGGBB.
    assert palette.primary.startswith("#") and len(palette.primary) == 7


def test_load_ncca_palette(tmp_themes_dir: object) -> None:
    """The NCCA (Ireland) palette loads and carries the expected fields."""
    palette = load_palette("ncca.ie")
    assert palette is not None
    assert palette.source_key == "ncca.ie"
    assert palette.jurisdiction == "Ireland"
    # The NCCA palette in the test fixture is "LC" level.
    assert palette.level == "LC"
    # The fixture writes a non-empty heading + body font.
    assert palette.heading_font
    assert palette.body_font


def test_load_aqa_palette(tmp_themes_dir: object) -> None:
    """The AQA (England) palette loads with the expected jurisdiction."""
    palette = load_palette("aqa.org.uk")
    assert palette is not None
    assert palette.jurisdiction == "England"


def test_load_ocr_palette(tmp_themes_dir: object) -> None:
    """The OCR (England) palette loads with the expected jurisdiction."""
    palette = load_palette("ocr.org.uk")
    assert palette is not None
    assert palette.jurisdiction == "England"


def test_load_pearson_palette(tmp_themes_dir: object) -> None:
    """The Pearson Edexcel (England) palette loads with the expected jurisdiction."""
    palette = load_palette("qualifications.pearson.com")
    assert palette is not None
    assert palette.jurisdiction == "England"


def test_load_sqa_palette(tmp_themes_dir: object) -> None:
    """The SQA (Scotland) palette loads with the expected jurisdiction."""
    palette = load_palette("sqa.org.uk")
    assert palette is not None
    assert palette.jurisdiction == "Scotland"


def test_load_wjec_palette(tmp_themes_dir: object) -> None:
    """The WJEC (Wales) palette loads with the expected jurisdiction."""
    palette = load_palette("wjec.co.uk")
    assert palette is not None
    assert palette.jurisdiction == "Wales"


def test_load_ccea_palette(tmp_themes_dir: object) -> None:
    """The CCEA (Northern Ireland) palette loads with the expected jurisdiction."""
    palette = load_palette("ccea.org.uk")
    assert palette is not None
    assert palette.jurisdiction == "Northern Ireland"


def test_load_iom_palette(tmp_themes_dir: object) -> None:
    """The Isle of Man palette loads with the expected jurisdiction."""
    palette = load_palette("gov.im/education")
    assert palette is not None
    assert palette.jurisdiction == "Isle of Man"


# ---------------------------------------------------------------------------
# Safeguarding palettes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "source_key,expected_jurisdiction",
    [
        ("gov.ie/education", "Ireland"),
        ("gov.uk/dfe", "England"),
        ("education.gov.scot", "Scotland"),
        ("gov.wales/education", "Wales"),
        ("ccea.org.uk/safeguarding", "Northern Ireland"),
    ],
)
def test_load_all_5_safeguarding_palettes(
    tmp_themes_dir: object,
    source_key: str,
    expected_jurisdiction: str,
) -> None:
    """All 5 safeguarding palettes load via the keyed API.

    Note: :func:`load_palette` looks up safeguarding sources via the
    :data:`SAFEGUARDING_SOURCES` map, NOT via direct file glob — so
    the call must use the ``gov.ie/education`` style key, not the
    file stem.
    """
    palette = load_palette(source_key)
    assert palette is not None, f"load_palette({source_key!r}) returned None"
    assert palette.jurisdiction == expected_jurisdiction
    assert palette.source_key == source_key


# ---------------------------------------------------------------------------
# Error / edge cases
# ---------------------------------------------------------------------------


def test_load_palette_missing_returns_none(tmp_themes_dir: object) -> None:
    """A missing source-key returns ``None`` (graceful degradation).

    Per the theming module contract: unknown keys return ``None``
    so the rest of the fleet can fall through to the canonical
    ``ncca.ie`` default. The logger records a WARNING.
    """
    palette = load_palette("definitely.not.a.real.source.key")
    assert palette is None


def test_list_all_palettes_includes_jurisdiction_files(tmp_themes_dir: object) -> None:
    """Within the tmp_themes_dir fixture, every jurisdiction + safeguarding palette is listed."""
    palettes = list_all_palettes()
    assert isinstance(palettes, list)
    assert len(palettes) >= 13, (
        f"Expected at least 13 palette fixtures, got {len(palettes)}"
    )

    # Every listed palette must carry the canonical 4 keys.
    for entry in palettes:
        assert "sourceKey" in entry
        assert "jurisdiction" in entry
        assert "level" in entry

    # All 5 safeguarding sources must be loadable individually.
    safeguarding_keys = list(SAFEGUARDING_SOURCES.keys())
    assert len(safeguarding_keys) == 5
    for safe_key in safeguarding_keys:
        assert load_palette(safe_key) is not None

    # Combined count = 8 jurisdictions + 5 safeguarding = 13.
    jurisdiction_count = len(JURISDICTIONS)
    safeguarding_count = len(SAFEGUARDING_SOURCES)
    assert jurisdiction_count + safeguarding_count == 13


# ---------------------------------------------------------------------------
# Dataclass behaviour
# ---------------------------------------------------------------------------


def test_palette_css_variables(sample_palette: dict) -> None:
    """The ``css_variables`` property exposes the 7 canonical CSS keys.

    Per the theming module contract the property returns a dict with
    ``--color-primary`` / ``--color-secondary`` / ``--color-accent``
 / ``--color-background`` / ``--color-text`` / ``--font-heading`` /
    ``--font-body``.
    """
    palette = sample_palette["palette"]
    css = palette.css_variables
    assert isinstance(css, dict)
    expected_keys = {
        "--color-primary",
        "--color-secondary",
        "--color-accent",
        "--color-background",
        "--color-text",
        "--font-heading",
        "--font-body",
    }
    assert set(css.keys()) == expected_keys
    # The hex codes must round-trip.
    assert css["--color-primary"] == palette.primary
    assert css["--font-heading"] == palette.heading_font


# ---------------------------------------------------------------------------
# BAML extraction stub
# ---------------------------------------------------------------------------


def test_extract_source_palette_from_pdf_stub(tmp_themes_dir: object) -> None:
    """The BAML extraction stub returns the canonical ``status=stub`` payload.

    Per the theming module: in production this delegates to the
    BAML ``ExtractSourcePalette`` function (which uses the 4-path
    OCR/VLM ensemble). In the stub, the function returns a dict
    with ``status="stub"`` + the echoed ``pdf_path`` / ``source_name``.
    """
    result = extract_source_palette_from_pdf(
        pdf_path="/tmp/some-syllabus.pdf",
        source_name="NCCA",
    )
    assert isinstance(result, dict)
    assert result["status"] == "stub"
    assert result["pdf_path"] == "/tmp/some-syllabus.pdf"
    assert result["source_name"] == "NCCA"
    assert "message" in result


def test_extract_source_palette_from_pdf_default_source_name(
    tmp_themes_dir: object,
) -> None:
    """``source_name`` defaults to ``""`` when not provided."""
    result = extract_source_palette_from_pdf(pdf_path="/tmp/x.pdf")
    assert result["source_name"] == ""