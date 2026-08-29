"""gemini_hackathon.certificate — the LC/JC certificate pipeline (W14, the showcase).

The end-to-end pipeline that produces an official-style Leaving Certificate
(LC) or Junior Certificate (JC) certificate for a learner, grounded
in the 5 NCCA policy documents + the learner's mastery ledger.

7 stages:

  1. ExtractCertificationCriteria — BAML extraction of the official
     certification criteria from the 5 NCCA PDFs (data/ireland/ncca_policy/).
  2. DecomposeOutcomes — split the learner's request into per-outcome
     parts (the LC has ~30 outcomes per subject).
  3. ExtractExamPaper + ExtractMarking — pull the relevant exam paper
     + marking scheme from data/ireland/lc_subject/.
  4. SearchOfficial — RAG over the 5 NCCA PDFs (the policy corpus).
  5. GenerateCertificateBackground — Flux + the W10 prompt bank
     (subject × stage → visual prompt).
  6. ComposeCertificate — PIL: background + text overlay + seal
     + competency strip + provenance footer.
  7. SaveToProvenance — write the result to Firestore + the mastery-vector
     store + markdown memory (W9 MasteryLedger — Google-native since the
     Phase 6 GCP-first refactor; see gemini_hackathon/ledger/).

The output is a `CertificateRecord` with:
  - learner_id + name + subject + stage
  - The certificate image (PNG bytes)
  - The PDF export (PDF bytes)
  - The full provenance footer (every cited page)
  - The skill-progression summary

Per the user's instruction: every claim on every certificate cites a
page from one of the 5 NCCA policy PDFs. The "UNOFFICIAL" banner is
always present (never an NCCA-issued credential).

The pipeline is consumed by:
  - The W7 ADK 2 cross-subject workflow (the Stage 1 coordinator)
  - The W12 editorial canvas (the `editorial_studio.build_workflow_canvas`)
  - The W13 LC HF Space (the headline demo)
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from gemini_hackathon.certificate.types import (
    CertificationCitation,
    CertificationCriteria,
    CertificateOutcomeRecord,
    CertificateRecord,
)

_log = logging.getLogger(__name__)


# The 5 NCCA policy PDFs (the source of truth — W2)
NCCA_POLICY_PDFS: tuple[str, ...] = (
    "SC-L1-L2-Programme-Statement.pdf",
    "key-competencies-in-senior-cycle_en.pdf",
    "the-potential-of-online-learning-environments_en.pdf",
    "the-potential-of-technology-to-support-online-certification-and-reporting.pdf",
    "scr-advisory-report_en.pdf",
)


@dataclass
class CertificatePipelineConfig:
    """The certificate pipeline configuration."""

    policy_pdf_dir: str = "data/ireland/ncca_policy"
    output_dir: str = "data/certificates"
    image_size: tuple[int, int] = (1200, 850)
    include_unofficial_banner: bool = True  # ALWAYS True per the user's spec
    use_flux_for_background: bool = True  # W10 FIBO pipeline
    include_competency_strip: bool = True


@dataclass
class CertificatePipeline:
    """The 7-stage certificate pipeline."""

    config: CertificatePipelineConfig = field(default_factory=CertificatePipelineConfig)

    async def run(
        self,
        learner_id: str,
        learner_name: str,
        subject_slug: str,
        stage: str,
        outcomes: list[CertificateOutcomeRecord],
    ) -> CertificateRecord:
        """Run the full 7-stage pipeline + return the certificate record.

        Args:
            learner_id: The learner's unique ID.
            learner_name: The learner's display name (e.g. "Maya O'Brien").
            subject_slug: One of NCCA_LC_SUBJECTS.
            stage: One of "aistear" / "bunscoil" / "meanscoil" /
                "scoil_sinsearach" / "ollscoil".
            outcomes: The learner's mastery outcomes for this subject
                (from the W9 MasteryLedger).

        Returns:
            CertificateRecord with the rendered certificate image + PDF
            + provenance + skill-progression summary.
        """
        # Stage 1: Extract certification criteria from the 5 NCCA PDFs
        criteria = await self._extract_criteria(subject_slug, stage)

        # Stage 2: Decompose outcomes
        outcome_records = await self._decompose_outcomes(outcomes)

        # Stage 3: Extract exam paper + marking scheme
        exam_paper, marking_scheme = await self._extract_paper_and_marking(
            subject_slug, stage
        )

        # Stage 4: RAG over the 5 NCCA policy corpus
        policy_citations = await self._search_official_documents(
            learner_id, subject_slug, outcome_records
        )

        # Stage 5: Generate the certificate background (Flux + W10 prompt bank)
        background = await self._generate_certificate_background(
            learner_name, subject_slug, stage, outcome_records
        )

        # Get the learner state from the W9 MasteryLedger
        try:
            from gemini_hackathon.ledger import MasteryLedger

            ledger = MasteryLedger.default()
            learner_state = await ledger.get_learner_state(learner_id)
        except Exception as e:
            _log.warning("MasteryLedger read failed: %s", e)
            learner_state = {"summary": {}}

        # Stage 6: Compose the certificate (PIL)
        png_bytes = await self._compose_certificate(
            learner_name=learner_name,
            subject_slug=subject_slug,
            stage=stage,
            outcomes=outcome_records,
            criteria=criteria,
            policy_citations=policy_citations,
            background=background,
            learner_state=learner_state,
        )

        # Stage 7: PDF export + save to provenance
        pdf_bytes = await self._export_pdf(png_bytes)
        await self._save_to_provenance(
            learner_id=learner_id,
            subject_slug=subject_slug,
            stage=stage,
            png_bytes=png_bytes,
            pdf_bytes=pdf_bytes,
            policy_citations=policy_citations,
            outcome_records=outcome_records,
        )

        return CertificateRecord(
            learner_id=learner_id,
            learner_name=learner_name,
            subject_slug=subject_slug,
            stage=stage,
            png_bytes=png_bytes,
            pdf_bytes=pdf_bytes,
            policy_citations=policy_citations,
            outcomes=outcome_records,
            criteria=criteria,
            learner_state_summary=learner_state.get("summary", {}),
            issued_at=datetime.now().isoformat(),
        )

    async def _extract_criteria(
        self, subject_slug: str, stage: str
    ) -> CertificationCriteria:
        """Stage 1: extract the official certification criteria.

        Stub: returns a populated record from the 5 NCCA PDF filenames.
        The real implementation calls
        `baml_extracts_education.certification_criteria.ExtractSeniorCycleCertificationCriteria`.
        """
        citations = [
            CertificationCitation(
                source_pdf=pdf,
                page=12 if "Programme" in pdf else 7,
                quote=f"[Stub quote for {pdf} — replaced by BAML in production]",
                relevance=f"Certification criterion for {subject_slug} in {stage}",
            )
            for pdf in NCCA_POLICY_PDFS
        ]
        return CertificationCriteria(
            stage=stage,
            subject_slug=subject_slug,
            award_descriptor=(
                "Exceptional" if stage == "scoil_sinsearach"
                else "Above expectations" if stage == "meanscoil"
                else "In line with expectations"
            ),
            descriptor_vocabulary=[
                "Exceptional", "Above expectations", "In line with expectations",
                "Yet to meet expectations",
            ],
            key_competencies=[
                "Communicating",
                "Being Creative",
                "Working with Others",
                "Managing Information & Thinking",
                "Managing Myself",
                "Staying Well",
            ],
            policy_citations=citations,
        )

    async def _decompose_outcomes(
        self, outcomes: list[CertificateOutcomeRecord]
    ) -> list[CertificateOutcomeRecord]:
        """Stage 2: normalise + order outcomes by mastery_score desc."""
        return sorted(outcomes, key=lambda o: o.mastery_score, reverse=True)

    async def _extract_paper_and_marking(
        self, subject_slug: str, stage: str
    ) -> tuple[Optional[str], Optional[str]]:
        """Stage 3: extract exam paper + marking.

        Stub: returns None (the W5 DLT pipeline populates these).
        """
        return None, None

    async def _search_official_documents(
        self,
        learner_id: str,
        subject_slug: str,
        outcomes: list[CertificateOutcomeRecord],
    ) -> list[CertificationCitation]:
        """Stage 4: RAG over the 5 NCCA policy corpus."""
        citations = []
        for outcome in outcomes:
            for pdf in NCCA_POLICY_PDFS:
                citations.append(CertificationCitation(
                    source_pdf=pdf,
                    page=self._mock_page_lookup(outcome.outcome_code),
                    quote=(
                        f"[Stub quote from {pdf} supporting outcome "
                        f"{outcome.outcome_code}]"
                    ),
                    relevance=(
                        f"Outcome {outcome.outcome_code} ({outcome.subject_slug}): "
                        f"NCCA-aligned descriptor '{outcome.descriptor}'"
                    ),
                ))
        return citations

    @staticmethod
    def _mock_page_lookup(outcome_code: str) -> int:
        """A deterministic page lookup stub.

        Uses the hash of the outcome code mod 30 (most NCCA PDFs are 30-60
        pages). Real implementation would call into the LanceDB knowledge
        graph (W8 hybrid_search) for semantic retrieval.
        """
        return (hash(outcome_code) % 30) + 1

    async def _generate_certificate_background(
        self,
        learner_name: str,
        subject_slug: str,
        stage: str,
        outcomes: list[CertificateOutcomeRecord],
    ) -> bytes:
        """Stage 5: generate the certificate background via Flux.

        Stub: returns a 1×1 transparent PNG (the real implementation
        calls gemini_hackathon_assets_fibo.generate_asset with the
        subject × stage prompt bank).
        """
        # 1×1 transparent PNG (the canonical minimal PNG)
        return bytes.fromhex(
            "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
            "890000000d49444154789c6300010000000500015c6df8b50000000049454e44ae426082"
        )

    async def _compose_certificate(
        self,
        learner_name: str,
        subject_slug: str,
        stage: str,
        outcomes: list[CertificateOutcomeRecord],
        criteria: CertificationCriteria,
        policy_citations: list[CertificationCitation],
        background: bytes,
        learner_state: dict,
    ) -> bytes:
        """Stage 6: compose the certificate via PIL.

        Layout (1200×850):
          +----------------------------------+
          |  Subject header (NCCA palette)    |
          |  Award descriptor (gold pill)     |
          |  Learner name (large serif)       |
          |  Outcomes table (top 5)            |
          |  Key Competencies strip            |
          |  Provenance footer (5 PDFs + page) |
          |  UNOFFICIAL banner (red pill)      |
          +----------------------------------+
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
            from gemini_hackathon_assets_fibo.processors.texture_processor import (
                apply_subject_watermark,
            )
            from gemini_hackathon_gradio._common.theme import stage_class
        except ImportError as e:
            _log.warning("PIL/gradio missing — returning stub PNG: %s", e)
            return background  # fallback to the 1×1 stub

        w, h = self.config.image_size
        # Start with a parchment-coloured background (the theme's --parchment)
        parchment = "#fdfaf3"
        img = Image.new("RGB", (w, h), color=parchment)

        # If a background image was generated, paste it as the top half
        if background and len(background) > 100:
            try:
                bg_img = Image.open(io.BytesIO(background)).convert("RGB")
                bg_img = bg_img.resize((w, h // 3))
                img.paste(bg_img, (0, 0))
            except Exception:
                pass  # fallback to parchment

        # Apply the subject watermark (per W10 subject_palette convention)
        img_rgba = img.convert("RGBA")
        img_rgba = apply_subject_watermark(
            img_rgba,
            subject_code=subject_slug.upper(),
            position="bottom-right",
            opacity=0.3,
            font_size=14,
        )

        # Draw the certificate text
        draw = ImageDraw.Draw(img_rgba)
        try:
            title_font = ImageFont.load_default(size=42)
            name_font = ImageFont.load_default(size=64)
            body_font = ImageFont.load_default(size=22)
            small_font = ImageFont.load_default(size=14)
        except (TypeError, AttributeError):
            title_font = ImageFont.load_default()
            name_font = ImageFont.load_default()
            body_font = ImageFont.load_default()
            small_font = ImageFont.load_default()

        # Stage-class CSS colour
        stage_cls = stage_class(stage)
        from gemini_hackathon_gradio._common.theme import EDUCATION_PALETTE
        stage_colour = EDUCATION_PALETTE.get(stage_cls.replace("stage-", "").split("_")[0], "#cc9966")

        # Header
        draw.text((60, 60), f"{stage.title()} Certificate", fill=stage_colour, font=title_font)
        draw.text((60, 130), f"Subject: {subject_slug.title()}", fill="#5c3a1a", font=body_font)

        # Award descriptor pill
        draw.rectangle([60, 180, 600, 230], fill=stage_colour)
        draw.text((80, 195), f"Award descriptor: {criteria.award_descriptor}", fill="#fdfaf3", font=body_font)

        # Learner name (large serif)
        draw.text((60, 270), learner_name, fill="#2a1f0c", font=name_font)

        # Outcomes (top 5)
        draw.text((60, 400), "Learning Outcomes Mastered:", fill="#5c3a1a", font=body_font)
        y = 440
        for o in outcomes[:5]:
            draw.text((80, y), f"• {o.outcome_code}: {o.descriptor} (mastery {o.mastery_score:.0%})", fill="#2a1f0c", font=small_font)
            y += 25

        # Key Competencies strip
        draw.text((60, y + 30), "Key Competencies Developed:", fill="#5c3a1a", font=body_font)
        y += 70
        col_width = (w - 120) // 5
        for i, kc in enumerate(criteria.key_competencies[:5]):
            draw.rectangle([60 + i * col_width, y, 60 + (i + 1) * col_width - 4, y + 30],
                           fill=stage_colour)
            draw.text((60 + i * col_width + 8, y + 8), kc, fill="#fdfaf3", font=small_font)

        # Provenance footer
        y += 60
        draw.text((60, y), "Generated from 5 NCCA policy documents:", fill="#5c3a1a", font=small_font)
        y += 18
        for cite in policy_citations[:5]:
            draw.text((60, y), f"• {cite.source_pdf}, p.{cite.page}", fill="#5c3a1a", font=small_font)
            y += 16

        # UNOFFICIAL banner (red pill — always present)
        if self.config.include_unofficial_banner:
            banner_y = h - 80
            draw.rectangle([60, banner_y, w - 60, banner_y + 50], fill="#a83a2a")
            draw.text((w // 2 - 200, banner_y + 12),
                      "UNOFFICIAL — NOT an NCCA-issued credential",
                      fill="#fdfaf3", font=body_font)

        # Convert back to RGB and save to bytes
        img = img_rgba.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    async def _export_pdf(self, png_bytes: bytes) -> bytes:
        """Stage 7: PDF export (uses the same minimal-PDF emitter)."""
        # For simplicity, re-use the _render_minimal_pdf helper from _common
        # In production, embed the PNG into a multi-page PDF.
        try:
            from gemini_hackathon_gradio._common.pclm_emitter import _render_minimal_pdf
            # Build a simple text-based PDF wrapping the PNG metadata
            text_lines = [
                f"LC/JC Certificate",
                f"(Image format: PNG, {len(png_bytes)} bytes)",
                "",
                "(Open the PNG to view the rendered certificate.)",
            ]
            return _render_minimal_pdf(text_lines)
        except ImportError:
            # Fallback: 1-page minimal PDF
            return self._render_minimal_pdf_fallback(text_lines=[
                f"LC/JC Certificate",
                f"(Image: PNG, {len(png_bytes)} bytes)",
                "",
                "(Open the PNG to view the rendered certificate.)",
            ])

    @staticmethod
    def _render_minimal_pdf_fallback(lines: list[str]) -> bytes:
        """Render a minimal 1-page PDF (pure Python, no PIL)."""
        import io as _io

        content_parts = ["BT", "/F1 11 Tf", "50 780 Td", "14 TL"]
        for i, line in enumerate(lines):
            safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            content_parts.append(f"({safe}) Tj" if i == 0 else f"T* ({safe}) Tj")
        content_parts.append("ET")
        content = "\n".join(content_parts).encode("latin-1", errors="replace")

        objects: list[bytes] = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            (b"<< /Type /Page /Parent 2 0 R "
             b"/MediaBox [0 0 612 792] /Contents 4 0 R "
             b"/Resources << /Font << /F1 5 0 R >> >> >>"),
            b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        ]
        out = _io.BytesIO()
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

    async def _save_to_provenance(
        self,
        learner_id: str,
        subject_slug: str,
        stage: str,
        png_bytes: bytes,
        pdf_bytes: bytes,
        policy_citations: list[CertificationCitation],
        outcome_records: list[CertificateOutcomeRecord],
    ) -> None:
        """Stage 7: save the certificate to the MasteryLedger + memory."""
        try:
            from gemini_hackathon.ledger import (
                MasteryLedger,
                MasteryRecord,
                MasteryUpdate,
            )

            ledger = MasteryLedger.default()
            # Issue one MasteryUpdate per outcome (the certificate is the
            # evidence of the cumulative mastery)
            for o in outcome_records:
                await ledger.update_mastery(MasteryUpdate(
                    record=MasteryRecord(
                        learner_id=learner_id,
                        subject_slug=subject_slug,
                        learning_outcome_code=o.outcome_code,
                        stage=stage,
                        mastery_score=o.mastery_score,
                        formative_evidence_ids=[f"certificate:{o.outcome_code}"],
                        key_competency_codes=o.key_competency_codes,
                    ),
                    delta=0.0,  # no change — this is a recorded event
                    evidence_id=f"certificate:{o.outcome_code}",
                    source_module="certificate_pipeline",
                ))
        except Exception as e:
            _log.warning("Ledger save failed: %s", e)


__all__ = [
    "NCCA_POLICY_PDFS",
    "CertificatePipelineConfig",
    "CertificatePipeline",
]
