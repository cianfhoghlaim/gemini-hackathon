"""cocoindex_flows.pdf.pdf_to_markdown_app — Phase 2b CocoIndex App.

Phase 2b of the multi-stage plan (see AGENTS.md). Walks the
``data/bi_ep/syllabi_raw/`` directory recursively, extracts each PDF to
Markdown, and writes the output to ``data/bi_ep/syllabi_md/`` preserving
the directory tree.

This module follows the canonical v1 CocoIndex pattern lifted from
``docs/cocoindex_examples/pdf_embedding/main.py``:

  1. ``@coco.fn.as_async(runner=coco.CPU)`` for the per-file extractor
  2. ``@coco.fn(memo=True)`` for the orchestration (cached on input path)
  3. ``localfs.declare_file(out_path, content, create_parent_dirs=True)``
     for the output

CocoIndex is optional — the module degrades to a plain ``run()``
function when ``import cocoindex`` fails. Tests exercise the
``run()`` path directly (no CocoIndex dependency required).

Run::

    python -m cocoindex_flows.pdf.pdf_to_markdown_app

Or programmatically via ``run()``.
"""

from __future__ import annotations

import logging
import pathlib
import sys
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

# Try to import cocoindex; gracefully degrade when missing.
try:
    from cocoindex.connectors import localfs  # type: ignore[import-not-found]

    import cocoindex as coco  # type: ignore[import-not-found]

    COCOINDEX_AVAILABLE = True
except ImportError:
    coco = None  # type: ignore[assignment]
    localfs = None  # type: ignore[assignment]
    COCOINDEX_AVAILABLE = False
    logger.warning("pdf_to_markdown_app: cocoindex not installed; falling back to plain run()")


try:
    from ._shared import extract_markdown, output_path_for
except ImportError:  # pragma: no cover — standalone-load fallback
    import importlib.util as _iu

    _spec = _iu.spec_from_file_location(
        "_shared_mod",
        pathlib.Path(__file__).resolve().parent / "_shared.py",
    )
    _mod = _iu.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    extract_markdown = _mod.extract_markdown
    output_path_for = _mod.output_path_for

#: Default input directory (matches ``dlt_pipelines/pdf_downloader.py`` output).
RAW_ROOT: pathlib.Path = pathlib.Path(
    __import__("os").environ.get(
        "BI_EP_PDF_RAW_ROOT",
        pathlib.Path.cwd() / "data" / "bi_ep" / "syllabi_raw",
    )
)

#: Default output directory.
MD_ROOT: pathlib.Path = pathlib.Path(
    __import__("os").environ.get(
        "BI_EP_PDF_MD_ROOT",
        pathlib.Path.cwd() / "data" / "bi_ep" / "syllabi_md",
    )
)


def _process_one_pdf(
    pdf_path: pathlib.Path,
    *,
    raw_root: pathlib.Path,
    md_root: pathlib.Path,
) -> pathlib.Path | None:
    """Read one PDF, extract Markdown, write to the canonical output path.

    Returns the output path on success, ``None`` on read failure.
    """
    try:
        content = pdf_path.read_bytes()
    except OSError as exc:  # pragma: no cover — disk / permissions
        logger.warning("pdf_to_markdown.read_failed path=%s reason=%s", pdf_path, exc)
        return None
    md = extract_markdown(content)
    if not md:
        logger.warning(
            "pdf_to_markdown.empty_extract path=%s (PDF may be image-only or encrypted)",
            pdf_path,
        )
        return None
    out = output_path_for(pdf_path, raw_root=raw_root, md_root=md_root)
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8")
    except OSError as exc:  # pragma: no cover
        logger.warning("pdf_to_markdown.write_failed out=%s reason=%s", out, exc)
        return None
    logger.info(
        "pdf_to_markdown.wrote path=%s bytes=%d pages=%d",
        out,
        len(md),
        md.count("## Page"),
    )
    return out


def run(
    *,
    raw_root: pathlib.Path | None = None,
    md_root: pathlib.Path | None = None,
    extra_roots: list[pathlib.Path] | None = None,
) -> dict[str, int]:
    """Run the markdown extraction over all PDFs under ``raw_root`` (+ extras).

    Phase 2 also walks the additional canonical roots the BIEP substrate
    uses outside of ``data/bi_ep/syllabi_raw/``:

      - ``data/ireland/ncca_policy`` — the 5 NCCA policy PDFs (the
        certificate source-of-truth lifted in W2 of the refactor)
      - ``data/syllabi`` — the 1 sample LC Maths PDF used by the
        ``notebooks/16_baml_extraction_visualisation.py`` smoke test

    Outputs from extra roots are written under ``<md_root>/extra/<rel>``
    so the canonical layout under ``<md_root>/uk_ncce/...`` stays
    untouched. Pass ``extra_roots=[]`` to skip the extra scan.

    Returns a stats dict:
        ``discovered`` — number of PDFs seen (raw_root + extras)
        ``converted`` — number of .md files written
        ``failed`` — number that raised during read or extract
    """
    raw = raw_root or RAW_ROOT
    md = md_root or MD_ROOT
    md.mkdir(parents=True, exist_ok=True)

    stats = {"discovered": 0, "converted": 0, "failed": 0}

    if raw.exists():
        pdfs = sorted(raw.rglob("*.pdf"))
        stats["discovered"] += len(pdfs)
        for pdf_path in pdfs:
            try:
                result = _process_one_pdf(pdf_path, raw_root=raw, md_root=md)
            except Exception as exc:
                logger.warning(
                    "pdf_to_markdown.unhandled_failure path=%s reason=%s",
                    pdf_path,
                    exc,
                )
                stats["failed"] += 1
                continue
            if result is None:
                stats["failed"] += 1
            else:
                stats["converted"] += 1
    else:
        logger.warning(
            "pdf_to_markdown_app.raw_root_missing path=%s "
            "— run `python -m dlt_pipelines.pdf_downloader` first",
            raw,
        )

    # Extra canonical roots (Phase 2): NCCA policy + sample LC Maths.
    if extra_roots is None:
        extra_roots = [
            pathlib.Path.cwd() / "data" / "ireland" / "ncca_policy",
            pathlib.Path.cwd() / "data" / "syllabi",
        ]
    for extra_root in extra_roots:
        if not extra_root.exists():
            continue
        for pdf_path in sorted(extra_root.rglob("*.pdf")):
            stats["discovered"] += 1
            target = md / "extra" / pdf_path.relative_to(extra_root.parent)
            target = target.with_suffix(".md")
            try:
                content = pdf_path.read_bytes()
                try:
                    from ._shared import extract_markdown
                except ImportError:  # pragma: no cover — standalone-load fallback
                    import importlib.util as _iu

                    _spec = _iu.spec_from_file_location(
                        "_shared_mod",
                        pathlib.Path(__file__).resolve().parent / "_shared.py",
                    )
                    _shared_mod = _iu.module_from_spec(_spec)  # type: ignore[arg-type]
                    _spec.loader.exec_module(_shared_mod)  # type: ignore[union-attr]
                    extract_markdown = _shared_mod.extract_markdown
                md_text = extract_markdown(content)
                if not md_text:
                    stats["failed"] += 1
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(md_text, encoding="utf-8")
                stats["converted"] += 1
            except Exception as exc:
                logger.warning(
                    "pdf_to_markdown.extra_failed path=%s reason=%s",
                    pdf_path,
                    exc,
                )
                stats["failed"] += 1

    return stats


# ---------------------------------------------------------------------------
# CocoIndex v1 App — canonical pattern (R1-R4 conformance)
# ---------------------------------------------------------------------------
# When cocoindex IS installed, this module exports a real ``coco.App`` so
# `cocoindex update pdf_to_markdown_app` works end-to-end. When cocoindex
# is missing, the App is None and the run() function above is the only
# entry point.

if COCOINDEX_AVAILABLE:
    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from cocoindex import coco as coco_types

    @coco.fn(memo=True)
    def _process_one_pdf_memo(
        pdf_path: pathlib.Path,
        out_path: pathlib.Path,
    ) -> None:
        """Per-file CocoIndex transform — cached on (pdf_path, out_path)."""
        try:
            content = pdf_path.read_bytes()
            md = extract_markdown(content)
            if not md:
                logger.warning("pdf_to_markdown.empty_extract path=%s", pdf_path)
                return
            localfs.declare_file(out_path, md, create_parent_dirs=True)
        except OSError as exc:  # pragma: no cover
            logger.warning("pdf_to_markdown.os_error path=%s reason=%s", pdf_path, exc)

    @coco.fn
    def app_main(
        raw_root_str: str,
        md_root_str: str,
    ) -> None:
        """CocoIndex orchestration: walk raw_root, process each PDF."""
        raw_root = pathlib.Path(raw_root_str)
        md_root = pathlib.Path(md_root_str)
        if not raw_root.exists():
            logger.warning("pdf_to_markdown_app.raw_root_missing path=%s", raw_root)
            return
        for pdf_path in sorted(raw_root.rglob("*.pdf")):
            out_path = output_path_for(pdf_path, raw_root=raw_root, md_root=md_root)
            _process_one_pdf_memo(pdf_path, out_path)

    app = coco.App(
        coco.AppConfig(name="PdfToMarkdownV1"),
        app_main,
        raw_root_str=str(RAW_ROOT),
        md_root_str=str(MD_ROOT),
    )
else:
    app = None  # type: ignore[assignment]


def main() -> int:
    """CLI entry: ``python -m cocoindex_flows.pdf.pdf_to_markdown_app``."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    stats = run()
    logger.info("pdf_to_markdown.summary %s", stats)
    return 0 if stats["failed"] == 0 else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())


__all__ = [
    "COCOINDEX_AVAILABLE",
    "MD_ROOT",
    "RAW_ROOT",
    "app",
    "main",
    "run",
]
