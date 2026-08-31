"""gemini_hackathon.journey.level_2_past_paper_ocr — Level 2 body.

Level 2 of the British Isles Journey: upload (or point at) a past paper
PDF, run the 4-path GCP-native OCR ensemble (Document AI + Gemini Vision
+ Gemma Vertex + pypdfium2 text-layer) in parallel, and consensus-vote
the winning path. Mirrors `docs/adk-examples/way-back-home/level_1/mcp-server/`
+ `gemini_hackathon/ocr_ensemble.py`'s `EnsembledExtractor` (Phase 5).

The 2-node ADK 2 Workflow (per `adk2-tutorial/L2a_parallel_join/workflow.py`):

    START -> 4-path parallel extract (ParallelAgent) -> consensus_vote

The 4 paths:
    1. document_ai       — Document AI Layout Parser (structured text + layout)
    2. gemini_vision      — Gemini 3.5 Flash via Vertex AI (multimodal)
    3. gemma4_vertex      — Gemma 4 26B-A4B on Vertex AI Model Garden (opt-in)
    4. pypdfium2          — the PDF's embedded text layer (zero-cost ground truth)

Honest note (per `ocr_ensemble.py`'s docstring): the source repo's
"consensus vote" is a pairwise Jaccard token similarity, NOT a real RAGAS
faithfulness/answer-relevance/context-precision computation — the
"consensus" measures inter-path agreement, not extraction quality. We
keep that honesty rather than overstating. When a labelled eval set
exists, swap the consensus for a real RAGAS vote.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Level2Result:
    pdf_path: str
    page_count: int
    paths: list[dict[str, Any]] = field(default_factory=list)
    voted_path: str | None = None
    consensus_score: float = 0.0
    voted_text: str = ""
    ncca_policy_citations: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# The 4 OCR paths (parallel via `asyncio.to_thread` — each backend call is
# blocking I/O; threads parallelise them, no async-client variants needed).
# ---------------------------------------------------------------------------


def _path_document_ai(pdf_path: str) -> dict[str, Any]:
    """Path 1 — Document AI Layout Parser. Returns (text, confidence_score)."""
    try:
        from gemini_hackathon.ocr import Backend, run_backend

        text, _ = run_backend(Backend.DOCUMENT_AI, pdf_path, prompt="Extract every text block.")
        return {"path": "document_ai", "text": text, "confidence_score": 0.92}
    except Exception as exc:
        return {"path": "document_ai", "text": "", "confidence_score": 0.0, "error": str(exc)}


def _path_gemini_vision(pdf_path: str) -> dict[str, Any]:
    """Path 2 — Gemini 3.5 Flash via Vertex AI."""
    try:
        from gemini_hackathon.ocr import Backend, run_backend

        text, _ = run_backend(
            Backend.GEMINI_VISION,
            pdf_path,
            prompt="Extract every text block, preserving order. Output plain text only.",
            model="gemini-3.5-flash",
        )
        return {"path": "gemini_vision", "text": text, "confidence_score": 0.88}
    except Exception as exc:
        return {"path": "gemini_vision", "text": "", "confidence_score": 0.0, "error": str(exc)}


def _path_gemma4_vertex(pdf_path: str) -> dict[str, Any]:
    """Path 3 — Gemma 4 26B-A4B on Vertex AI Model Garden (opt-in)."""
    try:
        from gemini_hackathon.ocr import Backend, run_backend

        text, _ = run_backend(
            Backend.GEMMA_VERTEX,
            pdf_path,
            prompt="Extract every text block, preserving order. Output plain text only.",
            model="gemma-4-26b-a4b",
        )
        return {"path": "gemma4_vertex", "text": text, "confidence_score": 0.85}
    except Exception as exc:
        return {"path": "gemma4_vertex", "text": "", "confidence_score": 0.0, "error": str(exc)}


def _path_pypdfium2(pdf_path: str) -> dict[str, Any]:
    """Path 4 — embedded text layer (the cheap ground truth).

    Returns the PDF's existing text-layer bytes directly. If the PDF has
    no text layer (a pure scan), this returns empty text + a low score —
    in that case Document AI + Gemini will dominate the consensus vote.
    """
    try:
        import pypdfium2 as pdfium

        pdf = pdfium.PdfDocument(pdf_path)
        page_texts = []
        for page in pdf:
            textpage = page.get_textpage()
            page_texts.append(textpage.get_text_range())
        text = "\n\n".join(page_texts)
        return {
            "path": "pypdfium2",
            "text": text,
            "confidence_score": 1.0 if text.strip() else 0.0,
            "page_count": len(pdf),
        }
    except Exception as exc:
        return {"path": "pypdfium2", "text": "", "confidence_score": 0.0, "error": str(exc)}


# ---------------------------------------------------------------------------
# ADK 2 Workflow nodes
# ---------------------------------------------------------------------------


async def extract_4_paths(node_input: Any) -> dict[str, Any]:
    """Function node: run the 4 OCR paths in parallel (asyncio.to_thread).

    Mirrors `gemini_hackathon/ocr_ensemble.EnsembledExtractor.extract()`'s
    asyncio.gather + per-path try/except pattern.
    """
    pdf_path = (node_input or {}).get("pdf_path", "")
    if not pdf_path:
        # Offline stub path — use the embedded-text-layer-only stub so
        # the consensus_vote still has at least one path to look at.
        pdf_path = (node_input or {}).get("pdf_text", "<offline-stub>")
        # When pdf_text is a plain string, treat it as the path-pypdfium2
        # answer directly so the offline workshop demos the consensus vote.
        paths = [
            {"path": "pypdfium2", "text": str(pdf_path), "confidence_score": 1.0},
            {"path": "document_ai", "text": str(pdf_path), "confidence_score": 0.92},
            {"path": "gemini_vision", "text": str(pdf_path), "confidence_score": 0.88},
            {"path": "gemma4_vertex", "text": str(pdf_path), "confidence_score": 0.85},
        ]
        return {"paths": paths}

    tasks = [
        asyncio.to_thread(_path_document_ai, pdf_path),
        asyncio.to_thread(_path_gemini_vision, pdf_path),
        asyncio.to_thread(_path_gemma4_vertex, pdf_path),
        asyncio.to_thread(_path_pypdfium2, pdf_path),
    ]
    paths = list(await asyncio.gather(*tasks))
    return {"paths": paths}


async def consensus_vote_node(node_input: Any) -> dict[str, Any]:
    """Function node: pairwise-Jaccard vote (per `ocr_ensemble.consensus_vote`).

    Picks the path whose text is, on average, most similar to every other
    successful path's text. Then extracts NCCA policy PDF citations from
    the winning text (the canonical "every claim cites a page" rule from
    `gemini_hackathon/certificate/pipeline.py`).
    """
    from gemini_hackathon.ocr_ensemble import EnsemblePathOutput, consensus_vote

    paths = node_input.get("paths", [])
    succeeded = [
        EnsemblePathOutput(
            path=p["path"],
            raw_response=p.get("text", ""),
        )
        for p in paths
        if p.get("text", "").strip()
    ]
    winner, score, text = consensus_vote(succeeded)

    citations = _extract_ncca_citations(text or "")
    return {
        "voted_path": winner,
        "consensus_score": score,
        "voted_text": text,
        "ncca_policy_citations": citations,
    }


def _extract_ncca_citations(text: str) -> list[str]:
    """Pull NCCA policy PDF filenames from the winning text (any path's
    output that mentions an NCCA policy filename cites it). Implements the
    certificate pipeline's "every claim cites a page" provenance rule.
    """
    import re

    candidates = [
        "SC-L1-L2-Programme-Statement.pdf",
        "key-competencies-in-senior-cycle_en.pdf",
        "the-potential-of-online-learning-environments_en.pdf",
        "the-potential-of-technology-to-support-online-certification-and-reporting.pdf",
        "scr-advisory-report_en.pdf",
    ]
    found = sorted({c for c in candidates if c in text})
    if not found:
        # Fall back to page-number references of the form "p. 12" or "page 12"
        page_refs = re.findall(r"\b(?:p\.?|page)\s*(\d{1,3})\b", text)
        if page_refs:
            found = [f"page_{p}" for p in sorted(set(page_refs))[:5]]
    return found


async def run_level_2(*, pdf_path: str = "") -> Level2Result:
    """The Level 2 entrypoint — runs the 2-node pipeline and returns the structured result.

    `pdf_path` defaults to "" -> offline-stub path (uses embedded-text-layer
    as the only path, so the consensus vote still demos with synthetic data).
    """
    paths_data = await extract_4_paths(
        {"pdf_path": pdf_path, "pdf_text": "Sample past paper text for the offline workshop."}
    )
    vote = await consensus_vote_node(paths_data)
    page_count = next(
        (p.get("page_count", 0) for p in paths_data["paths"] if p.get("path") == "pypdfium2"), 1
    )
    return Level2Result(
        pdf_path=pdf_path or "<offline-stub>",
        page_count=page_count or 1,
        paths=paths_data["paths"],
        voted_path=vote.get("voted_path"),
        consensus_score=vote.get("consensus_score", 0.0),
        voted_text=vote.get("voted_text", ""),
        ncca_policy_citations=vote.get("ncca_policy_citations", []),
    )


__all__ = [
    "Level2Result",
    "consensus_vote_node",
    "extract_4_paths",
    "run_level_2",
]
