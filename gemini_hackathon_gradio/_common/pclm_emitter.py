"""gemini_hackathon_gradio._common.pclm_emitter — PCLM-XML + minimal-PDF emitter.

Lifted from `sruth/spaces/an_scrudu/pclm.py` and generalised for the
5 educational stages (Aistear → Bunscoil → MeanScoil → Scoil
Sinsearach → Ollscoil).

PCLM (Paper Common Layout Markup) is a Department-of-Education-flavoured
XML schema used for Irish past papers. This emitter produces a minimal
PCLM document from a marking-scheme extraction record. The user can
download the PCLM-XML or a minimal-PDF rendering and ingest it into
the official document factory.

This is a *simplified* emitter, scoped to the editorial canvas demo.
The full PCLM schema in `oideachais/document_factory/curriculum_document.py`
has 4-5x more tags; we emit a subset that round-trips with the
extraction (topic_code, topic_label, marking_points, paper_section).

For the LC/JC certificate pipeline (W14), the same emitter is reused
with a different output profile — the certificate metadata replaces
the marking-scheme metadata, and the PDF rendering uses the parchment
CSS class from the British Isles education theme.

Supports both the **nested** shape (canonical Pydantic
`MarkingSchemeExtraction`) and the **flat** shape (legacy sruth
`CircularExtraction`) via duck-typing.
"""

from __future__ import annotations

import io
from typing import Protocol
from xml.etree import ElementTree as ET


PCLM_NS = "https://oideachais.ie/pclm/1.0"


class _MarkingSchemeLike(Protocol):
    """Protocol for any marking-scheme extraction record.

    Tolerates both the nested (canonical) and flat (legacy) shapes.
    """

    # Nested (canonical)
    circular: object  # .circular_number, .issued_year, .issuing_body, .title_en, .title_ga, .subject, .level
    scheme: object  # .total_marking_points, .topics, .estimated_paper_duration_min, .has_orale, .has_coursework
    # Flat (legacy) — also supported
    topics: list
    # Required
    raw_text_excerpt: str
    extraction_confidence: float
    source_model: str


_NESTED_FIELD_MAP: dict[str, tuple[str, str]] = {
    "circular_number": ("circular", "circular_number"),
    "issued_year": ("circular", "issued_year"),
    "issuing_body": ("circular", "issuing_body"),
    "title_en": ("circular", "title_en"),
    "title_ga": ("circular", "title_ga"),
    "subject": ("circular", "subject"),
    "level": ("circular", "level"),
    "total_marking_points": ("scheme", "total_marking_points"),
    "estimated_paper_duration_min": ("scheme", "estimated_paper_duration_min"),
    "has_orale": ("scheme", "has_orale"),
    "has_coursework": ("scheme", "has_coursework"),
    "topics": ("scheme", "topics"),
}


def _c(extraction: _MarkingSchemeLike, attr: str, default: object = None) -> object:
    """Read `attr` from either the nested or flat shape (duck-typed)."""
    if attr in _NESTED_FIELD_MAP:
        container_name, sub_attr = _NESTED_FIELD_MAP[attr]
        container = getattr(extraction, container_name, None)
        if container is not None and hasattr(container, sub_attr):
            return getattr(container, sub_attr)
    return getattr(extraction, attr, default)


def emit_pclm_xml(extraction: _MarkingSchemeLike) -> str:
    """Emit a PCLM XML document for the given extraction.

    Returns:
        The XML as a string (UTF-8, pretty-printed).
    """
    ET.register_namespace("", PCLM_NS)
    root = ET.Element(f"{{{PCLM_NS}}}examination")
    root.set("circular_number", str(_c(extraction, "circular_number")))
    root.set("issued_year", str(_c(extraction, "issued_year")))
    root.set("subject", str(_c(extraction, "subject", "")))
    root.set("level", str(_c(extraction, "level", "")))

    title = ET.SubElement(root, f"{{{PCLM_NS}}}title")
    title_en = ET.SubElement(title, f"{{{PCLM_NS}}}en")
    title_en.text = str(_c(extraction, "title_en", ""))
    title_ga = _c(extraction, "title_ga")
    if title_ga:
        title_ga_e = ET.SubElement(title, f"{{{PCLM_NS}}}ga")
        title_ga_e.text = str(title_ga)

    issuing = ET.SubElement(root, f"{{{PCLM_NS}}}issuingBody")
    issuing.text = str(_c(extraction, "issuing_body", ""))

    scheme = ET.SubElement(root, f"{{{PCLM_NS}}}markingScheme")
    scheme.set("totalMarks", str(_c(extraction, "total_marking_points", 0)))
    scheme.set("durationMin", str(_c(extraction, "estimated_paper_duration_min", 0)))
    if _c(extraction, "has_orale"):
        scheme.set("hasOrale", "true")
    if _c(extraction, "has_coursework"):
        scheme.set("hasCoursework", "true")

    for topic in _c(extraction, "topics", []) or []:
        t_elem = ET.SubElement(scheme, f"{{{PCLM_NS}}}topic")
        t_elem.set("code", topic.topic_code)
        t_elem.set("section", topic.paper_section)
        t_elem.set("marks", str(topic.marking_points))
        lbl = ET.SubElement(t_elem, f"{{{PCLM_NS}}}label")
        lbl.text = topic.topic_label

    excerpt = ET.SubElement(root, f"{{{PCLM_NS}}}excerpt")
    excerpt.text = str(getattr(extraction, "raw_text_excerpt", ""))

    confidence = ET.SubElement(root, f"{{{PCLM_NS}}}extractionConfidence")
    confidence.text = f"{extraction.extraction_confidence:.3f}"

    source = ET.SubElement(root, f"{{{PCLM_NS}}}sourceModel")
    source.text = str(getattr(extraction, "source_model", "unknown"))

    # Pretty-print
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode")


def emit_pclm_pdf_bytes(extraction: _MarkingSchemeLike) -> bytes:
    """Emit a minimal PDF containing the PCLM text. Pure-Python, no deps.

    1-page PDF with the headline data only. Used by the editorial
    canvas (W12) and the certificate pipeline (W14).
    """
    text_lines: list[str] = [
        f"PCLM Marking Scheme - {_c(extraction, 'subject', '')} {_c(extraction, 'issued_year', 0)}",
        "",
        f"Title: {_c(extraction, 'title_en', '')}",
        f"Issuing body: {_c(extraction, 'issuing_body', '')}",
        f"Level: {_c(extraction, 'level', '')}",
        f"Total marks: {_c(extraction, 'total_marking_points', 0)}",
        f"Duration: {_c(extraction, 'estimated_paper_duration_min', 0)} min",
        "",
        "Topics:",
    ]
    for t in _c(extraction, "topics", []) or []:
        text_lines.append(
            f"  {t.topic_code} {t.topic_label} - {t.marking_points} marks ({t.paper_section})"
        )
    text_lines.extend(
        [
            "",
            f"Extraction confidence: {extraction.extraction_confidence:.2f}",
            f"Source model: {extraction.source_model}",
            "",
            "Excerpt:",
            getattr(extraction, "raw_text_excerpt", ""),
        ]
    )
    return _render_minimal_pdf(text_lines)


def _render_minimal_pdf(lines: list[str]) -> bytes:
    """Render a list of text lines as a 1-page PDF. Pure-Python."""
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
