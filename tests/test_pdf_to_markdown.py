"""test_pdf_to_markdown.py — Phase 2b verification of the markdown extractor.

Tests:
  1. ``extract_markdown`` returns one "## Page N" heading per page.
  2. ``extract_markdown`` returns empty string for corrupt bytes.
  3. ``output_path_for`` produces the canonical path shape.
  4. ``run`` returns the no-PDFs stats when raw_root is empty.
  5. ``run`` writes a .md file per PDF in raw_root (canned test).
  6. ``run`` increments ``failed`` when one PDF is corrupt.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

import pytest


def _load_module():
    """Load via importlib to avoid pulling the cocoindex_flows package init."""
    spec = importlib.util.spec_from_file_location(
        "_test_pdf_to_markdown_app",
        pathlib.Path(__file__).resolve().parent.parent
        / "cocoindex_flows" / "pdf" / "pdf_to_markdown_app.py",
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_shared():
    spec = importlib.util.spec_from_file_location(
        "_test_pdf_to_markdown_shared",
        pathlib.Path(__file__).resolve().parent.parent
        / "cocoindex_flows" / "pdf" / "_shared.py",
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Module-level bindings — single load per test session.
app_mod = _load_module()
shared_mod = _load_shared()


def _minimal_pdf_bytes(page_count: int = 1) -> bytes:
    """Build a minimal valid PDF byte string with ``page_count`` pages."""
    objects: list[str] = []
    objects.append("<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(
        f"<< /Type /Pages /Kids [{ ' '.join(f'{3+i} 0 R' for i in range(page_count))} ] /Count {page_count} >>"
    )
    for i in range(page_count):
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>"
        )
    body_parts = ["%PDF-1.4\n"]
    offsets: list[int] = []
    for i, obj in enumerate(objects):
        offsets.append(sum(len(p.encode("latin-1")) for p in body_parts))
        body_parts.append(f"{i+1} 0 obj\n{obj}\nendobj\n")
    xref_offset = sum(len(p.encode("latin-1")) for p in body_parts)
    body_parts.append(
        f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n"
        + "".join(f"{o:010d} 00000 n \n" for o in offsets)
        + "trailer\n<< /Size "
        + str(len(objects)+1)
        + " /Root 1 0 R >>\nstartxref\n"
        + str(xref_offset)
        + "\n%%EOF\n"
    )
    return "".join(body_parts).encode("latin-1")


def test_extract_markdown_returns_page_headings() -> None:
    pdf_bytes = _minimal_pdf_bytes(page_count=3)
    md = shared_mod.extract_markdown(pdf_bytes)
    # One "## Page N" heading per page.
    assert md.count("## Page 1") == 1
    assert md.count("## Page 2") == 1
    assert md.count("## Page 3") == 1


def test_extract_markdown_returns_empty_for_corrupt_bytes() -> None:
    md = shared_mod.extract_markdown(b"not a pdf")
    assert md == ""


def test_extract_markdown_returns_empty_for_empty_bytes() -> None:
    md = shared_mod.extract_markdown(b"")
    assert md == ""


def test_output_path_for_canonical_shape() -> None:
    raw = pathlib.Path("/tmp/raw")
    md = pathlib.Path("/tmp/md")
    out = shared_mod.output_path_for(
        pathlib.Path("/tmp/raw/aqa.org.uk/mathematics/en/abc123.pdf"),
        raw_root=raw,
        md_root=md,
    )
    assert out == pathlib.Path("/tmp/md/aqa.org.uk/mathematics/en/abc123.md")


def test_run_no_raw_root(tmp_path: pathlib.Path) -> None:
    """Missing raw_root -> empty stats, no crash."""
    stats = app_mod.run(
        raw_root=tmp_path / "missing",
        md_root=tmp_path / "md",
        extra_roots=[],
    )
    assert stats == {"discovered": 0, "converted": 0, "failed": 0}


def test_run_writes_md_per_pdf(tmp_path: pathlib.Path) -> None:
    """3 PDFs in raw_root -> 3 .md files in md_root."""
    raw = tmp_path / "raw"
    md = tmp_path / "md"
    raw.mkdir()
    for sub, sha in [
        ("aqa.org.uk/mathematics/en", "a" * 64),
        ("ocr.org.uk/chemistry/en", "b" * 64),
        ("wjec.co.uk/biology/en", "c" * 64),
    ]:
        d = raw / sub
        d.mkdir(parents=True)
        (d / f"{sha}.pdf").write_bytes(_minimal_pdf_bytes(page_count=2))

    stats = app_mod.run(raw_root=raw, md_root=md, extra_roots=[])
    assert stats["discovered"] == 3
    assert stats["converted"] == 3
    assert stats["failed"] == 0

    # All 3 .md files exist with the expected shape.
    for sha in ["a" * 64, "b" * 64, "c" * 64]:
        out = md / "aqa.org.uk" / "mathematics" / "en" / f"{sha}.md"
        if not out.exists():
            # Search by sha across all subdirs.
            matches = list(md.rglob(f"{sha}.md"))
            assert len(matches) == 1
            out = matches[0]
        text = out.read_text(encoding="utf-8")
        assert "## Page 1" in text
        assert "## Page 2" in text


def test_run_increments_failed_for_corrupt_pdf(
    tmp_path: pathlib.Path
) -> None:
    """One valid PDF + one corrupt PDF -> 1 converted, 1 failed."""
    raw = tmp_path / "raw"
    md = tmp_path / "md"
    raw.mkdir()

    valid = raw / "valid" / "en"
    valid.mkdir(parents=True)
    (valid / "v.pdf").write_bytes(_minimal_pdf_bytes(page_count=1))

    invalid = raw / "invalid" / "en"
    invalid.mkdir(parents=True)
    (invalid / "i.pdf").write_bytes(b"not a pdf at all")

    stats = app_mod.run(raw_root=raw, md_root=md, extra_roots=[])
    assert stats["discovered"] == 2
    assert stats["converted"] == 1
    assert stats["failed"] == 1


def test_run_handles_empty_raw_root(tmp_path: pathlib.Path) -> None:
    """raw_root exists but is empty -> zero discovered."""
    raw = tmp_path / "raw"
    md = tmp_path / "md"
    raw.mkdir()
    stats = app_mod.run(raw_root=raw, md_root=md, extra_roots=[])
    assert stats == {"discovered": 0, "converted": 0, "failed": 0}


def test_cocoindex_app_is_none_when_not_installed() -> None:
    """When cocoindex isn't installed, app is None (graceful degradation)."""
    # The module loaded COCOINDEX_AVAILABLE at import time.
    # Either True or False is acceptable; the test just guards against
    # the case where the App object is unexpectedly None vs an object.
    assert app_mod.COCOINDEX_AVAILABLE is False or app_mod.app is not None
    # The non-installed path yields app=None — that's the canonical dev path.
    if not app_mod.COCOINDEX_AVAILABLE:
        assert app_mod.app is None