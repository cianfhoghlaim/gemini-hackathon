"""cocoindex_flows.pdf._shared — PDF → Markdown helpers for the pdf_to_markdown App.

Phase 2b of the multi-stage plan (see AGENTS.md). Lightweight text-only
extractor using ``pypdfium2`` (already pinned in ``pyproject.toml``).

The choice of pypdfium2 over Docling/Marker:
- **Speed** — pypdfium2 is the fastest text-only PDF backend (parity with
  PyMuPDF at ~3 s for 7k pages per the 2026 benchmark).
- **Licence** — Apache-2.0 (vs PyMuPDF's AGPL-3.0).
- **Already installed** — no new dep. Docling + Marker would add ~500 MiB.

For official government PDFs that mix dense text with tables, the
``extract_markdown_with_layout`` helper pulls each page's text via
``PdfPage.get_textpage().get_text_range()`` + joins with double newlines.
Tables lose visual structure but text + page numbers survive.

For higher-fidelity table extraction (Phase 3+), plug in Docling via the
optional ``PDF_BACKEND=docling`` env var (the v2 App can override).
"""

from __future__ import annotations

import functools
import logging
import os
import pathlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=1)
def _pypdfium2_document(content: bytes):
    """Open a PDF document from bytes (cached per content hash)."""
    import pypdfium2 as pdfium

    return pdfium.PdfDocument(content)


def extract_markdown(content: bytes) -> str:
    """Extract text from a PDF and join per-page as Markdown.

    Returns a Markdown string with one ``## Page N`` heading per page
    followed by the page's text. Tables are flattened to text (no
    visual structure preserved).

    Falls back to ``""`` on any decode error (corrupt / encrypted PDF).
    """
    backend = os.environ.get("PDF_BACKEND", "pypdfium2").lower()
    if backend == "docling":
        return _extract_markdown_docling(content)
    return _extract_markdown_pypdfium2(content)


def _extract_markdown_pypdfium2(content: bytes) -> str:
    """pypdfium2-based text extraction."""
    try:
        import pypdfium2 as pdfium
    except ImportError:
        logger.warning("pdf._shared: pypdfium2 not installed; returning empty Markdown")
        return ""
    try:
        doc = pdfium.PdfDocument(content)
    except Exception as exc:
        logger.warning("pdf._shared: pypdfium2.PdfDocument failed: %s", exc)
        return ""
    try:
        n_pages = len(doc)
    except Exception:
        n_pages = 0
    parts: list[str] = []
    for i in range(n_pages):
        try:
            page = doc[i]
            tp = page.get_textpage()
            text = tp.get_text_range() or ""
            parts.append(f"## Page {i + 1}\n\n{text.strip()}\n")
        except Exception as exc:
            logger.warning("pdf._shared: page %d decode failed: %s", i, exc)
            parts.append(f"## Page {i + 1}\n\n_(decode error)_\n")
    return "\n".join(parts)


def _extract_markdown_docling(content: bytes) -> str:
    """Docling-based extraction (optional — only when PDF_BACKEND=docling)."""
    try:
        from docling.datamodel.base_models import DocumentStream  # type: ignore[import-not-found]
        from docling.document_converter import DocumentConverter  # type: ignore[import-not-found]

        converter = DocumentConverter()
        doc = converter.convert(
            DocumentStream(name="in.pdf", stream=__import__("io").BytesIO(content))
        )
        return doc.document.export_to_markdown()
    except ImportError:
        logger.warning(
            "pdf._shared: PDF_BACKEND=docling but docling is not installed; "
            "falling back to pypdfium2"
        )
        return _extract_markdown_pypdfium2(content)
    except Exception as exc:
        logger.warning("pdf._shared: docling convert failed: %s", exc)
        return _extract_markdown_pypdfium2(content)


def output_path_for(
    pdf_path: pathlib.Path,
    *,
    raw_root: pathlib.Path,
    md_root: pathlib.Path,
) -> pathlib.Path:
    """Return the canonical Markdown output path for a PDF input path.

    Layout::

        data/bi_ep/syllabi_raw/<source_key>/<subject>/<lang>/<sha>.pdf
            ->
        data/bi_ep/syllabi_md/<source_key>/<subject>/<lang>/<sha>.md

    The directory tree under ``raw_root`` is preserved verbatim.
    """
    relative = pdf_path.relative_to(raw_root)
    return md_root / relative.with_suffix(".md")
