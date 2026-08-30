"""cocoindex_flows.pdf.benchmark — head-to-head benchmark of PDF backends.

Phase 2b benchmark (see AGENTS.md). Compares:
  - pypdfium2 (text-only, Apache-2.0, ~3s/100pages)
  - PyMuPDF/fitz (text+layout, AGPL-3.0, ~3s/100pages)
  - pypdf (pure-Python, BSD, ~500s/100pages — slow)

Run::

    python -m cocoindex_flows.pdf.benchmark <pdf_path>
"""

from __future__ import annotations

import argparse
import json
import logging
import pathlib
import sys
import time
from typing import Any

logger = logging.getLogger(__name__)


def _time_one(label: str, fn, *args: Any, **kwargs: Any) -> dict[str, Any]:
    """Run ``fn(*args, **kwargs)`` once + time it."""
    started = time.monotonic()
    result = fn(*args, **kwargs)
    elapsed_ms = int((time.monotonic() - started) * 1000)
    char_count = len(result) if isinstance(result, str) else 0
    return {
        "backend": label,
        "elapsed_ms": elapsed_ms,
        "output_chars": char_count,
        "ok": True,
    }


def benchmark_pdf(pdf_path: pathlib.Path) -> dict[str, Any]:
    """Run all available backends on one PDF and return the timing table."""
    content = pdf_path.read_bytes()
    results: list[dict[str, Any]] = []

    # pypdfium2 (always available)
    try:
        import pypdfium2  # noqa: F401

        from cocoindex_flows.pdf._shared import extract_markdown as pd_md

        results.append(_time_one("pypdfium2", pd_md, content))
    except ImportError as exc:
        results.append({"backend": "pypdfium2", "ok": False, "reason": str(exc)})

    # PyMuPDF / fitz (optional)
    try:
        import fitz  # type: ignore[import-not-found]

        def _fitz_extract(content: bytes) -> str:
            doc = fitz.open(stream=content, filetype="pdf")
            parts: list[str] = []
            for i, page in enumerate(doc):
                parts.append(f"## Page {i + 1}\n\n{page.get_text() or ''}\n")
            return "\n".join(parts)

        results.append(_time_one("pymupdf", _fitz_extract, content))
    except ImportError as exc:
        results.append({"backend": "pymupdf", "ok": False, "reason": str(exc)})

    # pypdf (always available — slow but pure-Python)
    try:
        import pypdf  # type: ignore[import-not-found]

        def _pypdf_extract(content: bytes) -> str:
            from io import BytesIO

            reader = pypdf.PdfReader(BytesIO(content))
            parts: list[str] = []
            for i, page in enumerate(reader.pages):
                parts.append(f"## Page {i + 1}\n\n{page.extract_text() or ''}\n")
            return "\n".join(parts)

        results.append(_time_one("pypdf", _pypdf_extract, content))
    except ImportError as exc:
        results.append({"backend": "pypdf", "ok": False, "reason": str(exc)})

    return {
        "pdf_path": str(pdf_path),
        "pdf_size_bytes": len(content),
        "backends": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark PDF extraction backends.")
    parser.add_argument("pdf_path", type=pathlib.Path)
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = parser.parse_args()

    if not args.pdf_path.exists():
        print(f"PDF not found: {args.pdf_path}", file=sys.stderr)
        return 1

    result = benchmark_pdf(args.pdf_path)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"PDF: {result['pdf_path']}  ({result['pdf_size_bytes']} bytes)")
        for backend in result["backends"]:
            if backend.get("ok"):
                print(
                    f"  {backend['backend']:12s}  {backend['elapsed_ms']:6d} ms  "
                    f"{backend['output_chars']:7d} chars"
                )
            else:
                print(f"  {backend['backend']:12s}  SKIPPED ({backend.get('reason')})")
    return 0


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())


__all__ = ["benchmark_pdf", "main"]