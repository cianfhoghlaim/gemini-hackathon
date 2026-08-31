"""gemini_hackathon_gradio._common.hlml_emitter — HLML + minimal-PDF emitter.

HLML (Heatmap Layout Markup) is a gemini_hackathon-internal format for
representing a topic-distribution heatmap. It's a sibling of PCLM but
for heatmaps rather than marking schemes.

The format is a simple JSON wrapper around a 2D matrix:

    {
        "hlml_version": "1.0",
        "exam_id": "LC-CHEM-2024",
        "topics": ["Atomic Structure", "Bonding", ...],
        "years": [2019, 2020, 2021, 2022, 2023, 2024],
        "matrix": [[10, 12, ...], [5, 7, ...], ...],
        "max_value": 25,
        "color_stops": [
            {"ratio": 0.0, "hex": "#1a3a2a"},
            ...
        ]
    }

The renderer (`gemini_hackathon/gradio/an_scrudu/heatmap.py`) consumes
this and emits an HTML heatmap. The PDF emitter below renders the
same data as a 1-page PDF (used by the editorial canvas downloads).
"""

from __future__ import annotations

import io
import json
from typing import Any

HLML_VERSION = "1.0"


def emit_hlml_json(
    *,
    exam_id: str,
    topics: list[str],
    years: list[int],
    matrix: list[list[int]],
    color_stops: list[dict[str, Any]],
) -> str:
    """Emit the HLML JSON document for a topic × year heatmap.

    Returns:
        A JSON string (UTF-8, pretty-printed).
    """
    if len(topics) != len(matrix):
        raise ValueError(f"len(topics)={len(topics)} != len(matrix)={len(matrix)}")
    if matrix and len(years) != len(matrix[0]):
        raise ValueError(
            f"len(years)={len(years)} != len(matrix[0])={len(matrix[0]) if matrix else 0}"
        )
    max_value = max((cell for row in matrix for cell in row), default=0)
    doc: dict[str, Any] = {
        "hlml_version": HLML_VERSION,
        "exam_id": exam_id,
        "topics": topics,
        "years": years,
        "matrix": matrix,
        "max_value": max_value,
        "color_stops": color_stops,
    }
    return json.dumps(doc, indent=2, ensure_ascii=False)


def emit_hlml_pdf_bytes(
    *,
    exam_id: str,
    topics: list[str],
    years: list[int],
    matrix: list[list[int]],
) -> bytes:
    """Emit a 1-page PDF rendering of the heatmap as an ASCII table.

    Pure-Python PDF emitter (no PIL / reportlab dependency).
    """
    text_lines: list[str] = [
        f"HLML Heatmap - {exam_id}",
        "",
        "Year:    " + "  ".join(f"{y:>4}" for y in years),
        "-" * (8 + 6 * len(years)),
    ]
    for topic, row in zip(topics, matrix, strict=False):
        cells = "  ".join(f"{c:>4}" for c in row)
        topic_trunc = topic[:8].ljust(8)
        text_lines.append(f"{topic_trunc}: {cells}")
    text_lines.extend(
        [
            "",
            f"Total cells: {sum(len(r) for r in matrix)}",
            f"Max value: {max((c for r in matrix for c in r), default=0)}",
        ]
    )
    return _render_minimal_pdf_table(text_lines)


def _render_minimal_pdf_table(lines: list[str]) -> bytes:
    """Render the heatmap text as a 1-page PDF."""
    content_parts: list[str] = ["BT", "/F1 11 Tf", "50 780 Td", "14 TL"]
    for i, line in enumerate(lines):
        safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        if i == 0:
            content_parts.append(f"({safe}) Tj")
        else:
            content_parts.append(f"T* ({safe}) Tj")
    content_parts.append("ET")
    content = "\n".join(content_parts).encode("latin-1", errors="replace")

    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R "
            b"/MediaBox [0 0 612 792] /Contents 4 0 R "
            b"/Resources << /Font << /F1 5 0 R >> >> >>"
        ),
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: list[int] = []
    for i, obj in enumerate(objects, 1):
        offsets.append(out.tell())
        out.write(f"{i} 0 obj\n".encode())
        out.write(obj)
        out.write(b"\nendobj\n")
    xref_offset = out.tell()
    out.write(f"xref\n0 {len(objects) + 1}\n".encode())
    out.write(b"0000000000 65535 f \n")
    for off in offsets:
        out.write(f"{off:010d} 00000 n \n".encode())
    out.write(b"trailer\n")
    out.write(f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode())
    out.write(f"startxref\n{xref_offset}\n%%EOF\n".encode())
    return out.getvalue()
