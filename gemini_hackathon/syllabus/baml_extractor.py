"""gemini_hackathon.syllabus.baml_extractor — BAML-backed syllabus extraction.

Wraps the lifted BAML functions from
`baml_extracts_education/stages/leaving_cycle.baml` (the canonical
LC6 extraction template — Phase 1.2) + the 8 per-subject extensions
from `baml_extracts_education/subjects/*.baml` (Phase 4).

Routes through the BAML client registry (`baml_extracts/clients.baml`)
which already has the `BIEPV3Extract` client pointing at Vertex AI
Gemini 3.5 Flash.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from .extractor import (
    ExtractedSyllabus,
    ExtractionMethod,
    SyllabusExtractionError,
    SyllabusExtractor,
)

logger = logging.getLogger(__name__)


class BAMLSyllabusExtractor:
    """The BAML-backed syllabus extractor (uses the lifted LC6 + per-subject BAML)."""

    method: ExtractionMethod = ExtractionMethod.BAML

    def extract(
        self,
        *,
        subject: str,
        level: str = "scoil_sinsearach",
        language: str = "EN",
        source_pdf_path: str | None = None,
        source_pdf_url: str | None = None,
    ) -> ExtractedSyllabus:
        """Extract the syllabus via BAML.

        Uses the per-subject BAML extension when available (the 8
        per-subject files from Phase 4), otherwise falls back to the
        canonical ExtractCurriculumSyllabus from leaving_cycle.baml.
        """
        started = time.monotonic()
        try:
            from baml_client.sync_client import b  # type: ignore
        except ImportError as exc:
            raise SyllabusExtractionError(
                f"BAML client not installed: {exc}. Run `uv run baml-cli generate` first."
            ) from exc

        # Read the source text (PDF → text via llama-swap OCR or direct text)
        pdf_text = _read_source_text(source_pdf_path=source_pdf_path, source_pdf_url=source_pdf_url)

        # Try the per-subject BAML extension first
        per_subject_fn = _per_subject_baml_fn(subject=subject)
        if per_subject_fn is not None:
            logger.info("baml_extractor: using per-subject BAML for subject=%s", subject)
            try:
                if subject == "gaeilge":
                    # Gaeilge takes both EN + GA text
                    doc = per_subject_fn(pdf_text_ga=pdf_text, pdf_text_en=None)
                else:
                    doc = per_subject_fn(pdf_text=pdf_text, language=language)
            except Exception as exc:
                logger.warning(
                    "baml_extractor: per-subject BAML failed (%s); falling back to canonical",
                    exc,
                )
                doc = b.ExtractCurriculumSyllabus(
                    pdf_text=pdf_text, subject=subject, language=language,
                )
        else:
            logger.info("baml_extractor: using canonical LC6 BAML for subject=%s", subject)
            doc = b.ExtractCurriculumSyllabus(
                pdf_text=pdf_text, subject=subject, language=language,
            )

        latency_ms = int((time.monotonic() - started) * 1000)
        return _baml_to_extracted(
            doc, extraction_method=ExtractionMethod.BAML, latency_ms=latency_ms,
        )


def _per_subject_baml_fn(*, subject: str):
    """Return the per-subject BAML function for the given subject, or None."""
    try:
        from baml_client.sync_client import b  # type: ignore
    except ImportError:
        return None
    fn_name = f"Extract{subject.capitalize().replace('_', '')}Syllabus"
    # Special-case gaeilge (special capitalisation in BAML)
    if subject == "gaeilge":
        fn_name = "ExtractGaeilgeSyllabus"
    if subject == "english":
        fn_name = "ExtractEnglishSyllabus"
    if subject == "chemistry":
        fn_name = "ExtractChemistrySyllabus"
    if subject == "geography":
        fn_name = "ExtractGeographySyllabus"
    if subject == "physics":
        fn_name = "ExtractPhysicsSyllabus"
    if subject == "biology":
        fn_name = "ExtractBiologySyllabus"
    if subject == "computer_science":
        fn_name = "ExtractComputerScienceSyllabus"
    if subject == "mathematics":
        fn_name = "ExtractMathsSyllabus"
    return getattr(b, fn_name, None)


def _read_source_text(*, source_pdf_path: str | None, source_pdf_url: str | None) -> str:
    """Read the source text from a PDF path or URL.

    Uses pypdf for local files + httpx + pypdf for URLs. Falls back
    to a stub string if neither is available.
    """
    if source_pdf_path:
        try:
            from pypdf import PdfReader  # type: ignore
        except ImportError:
            return f"[stub text — pypdf not installed; would read {source_pdf_path}]"
        try:
            reader = PdfReader(source_pdf_path)
            return "\n\n".join(p.extract_text() or "" for p in reader.pages)
        except Exception as exc:
            logger.warning("baml_extractor: pypdf read failed (%s)", exc)
            return f"[stub text — pypdf read failed for {source_pdf_path}]"
    if source_pdf_url:
        try:
            import httpx  # type: ignore
            from pypdf import PdfReader  # type: ignore
            import io
        except ImportError:
            return f"[stub text — httpx/pypdf not installed; would fetch {source_pdf_url}]"
        try:
            r = httpx.get(source_pdf_url, timeout=30.0)
            r.raise_for_status()
            reader = PdfReader(io.BytesIO(r.content))
            return "\n\n".join(p.extract_text() or "" for p in reader.pages)
        except Exception as exc:
            logger.warning("baml_extractor: URL fetch failed (%s)", exc)
            return f"[stub text — fetch failed for {source_pdf_url}]"
    return "[stub text — no source_pdf_path or source_pdf_url provided]"


def _baml_to_extracted(doc: Any, *, extraction_method: ExtractionMethod, latency_ms: int) -> ExtractedSyllabus:
    """Convert a BAML response to the unified ExtractedSyllabus."""
    # The BAML response is a Pydantic model. We extract the fields.
    if hasattr(doc, "model_dump"):
        d = doc.model_dump()
    elif isinstance(doc, dict):
        d = doc
    else:
        d = vars(doc)

    module_topics = d.get("module_topics", []) or []
    prescribed_texts = d.get("prescribed_texts", []) or []
    formulas = d.get("formulas", []) or []

    return ExtractedSyllabus(
        subject=str(d.get("subject", "")),
        language=str(d.get("language", "EN")),
        module_topics=module_topics,
        total_learning_outcomes=int(d.get("total_learning_outcomes", 0) or 0),
        cross_curricular=list(d.get("cross_curricular", []) or []),
        assessment_objectives=list(d.get("assessment_objectives", []) or []),
        prescribed_texts=prescribed_texts,
        formulas=formulas,
        extraction_method=extraction_method,
        extraction_latency_ms=latency_ms,
        extraction_confidence=0.95,  # BAML is structured output, high confidence
    )


__all__ = ["BAMLSyllabusExtractor"]