"""gemini_hackathon.ocr_ensemble — the GCP-native 4-path consensus OCR extractor.

Phase 5 of the GCP-first refactor. Ports the orchestration *shape* from
`meaisinfhoghlaim/ocr/ensemble/ensembled_extractor.py`'s `EnsembledExtractor`
(the strongest architectural idea in that tree: fan a document out to N
independent extraction paths concurrently, land each path's output, then
vote a canonical winner) — verbatim on the parts worth keeping, rewritten
on the parts that were self-hosted-container-shaped.

The 4 paths (was: BAML/Docling, Unstract, qwen3-vl-8b, gemma-4-26B — 4
self-hosted HTTP services with zero GCP equivalent):

    Path 1 (document_ai)   Document AI Layout Parser — structured text +
                             layout, strongest on forms/tables
    Path 2 (gemini_vision)  Gemini 3.5 Flash via Vertex AI — strongest on
                             free-form reasoning + bilingual EN/GA content
    Path 3 (gemma4_vertex)  Gemma 4 26B-A4B via a Vertex AI Model Garden
                             endpoint (opt-in — skipped gracefully if
                             GEMMA_VERTEX_ENDPOINT_ID is unset, since it
                             needs a deployed endpoint unlike the other 3)
    Path 4 (pypdfium2)      the embedded PDF text layer, zero-cost —
                             the fastest possible ground truth when a PDF
                             already carries real text (typed exam papers,
                             not scans)

Honesty about the RAGAS vote: `meaisinfhoghlaim.evaluation.ragas_biiep_ensemble`
imports the real `ragas` package but its own `_heuristic_score()` never
actually calls it — every score in that source module is a length-based
stub (`len(text) > 100 -> 0.85`), not a real RAGAS faithfulness/relevance/
precision computation. This port keeps that honesty rather than
pretending to a "RAGAS score" the source never computed: `consensus_vote()`
below is a documented **pairwise text-similarity consensus** (the paths
that most agree with each other win — a real, if simple, signal) rather
than a fake RAGAS wrapper. Swap in the real `ragas` package behind the
same `PathScore` shape when there's a labelled eval set to justify it
(`meaisinfhoghlaim/evaluation/golden_baselines.py` has the pattern).

Reference: cianfhoghlaim/meaisinfhoghlaim/ocr/ensemble/ensembled_extractor.py
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from .ocr import Backend, CapabilityUnavailableError, is_backend_available, run_backend

logger = logging.getLogger(__name__)

PathName = Literal["document_ai", "gemini_vision", "gemma4_vertex", "pypdfium2"]

_PATH_BACKENDS: dict[PathName, Backend] = {
    "document_ai": Backend.DOCUMENT_AI,
    "gemini_vision": Backend.GEMINI_VISION,
    "gemma4_vertex": Backend.GEMMA_VERTEX,
    "pypdfium2": Backend.PYPDFIUM2_TEXTLAYER,
}

DEFAULT_PROMPT = (
    "Extract every word of text from this document page, preserving "
    "reading order, tables as markdown, and formulas as LaTeX. "
    "Output plain text only."
)


@dataclass
class EnsemblePathOutput:
    """One path's output (input to the consensus vote)."""

    path: PathName
    raw_response: str
    duration_ms: int = 0
    error: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.error is None and bool(self.raw_response.strip())


@dataclass
class EnsembleResult:
    """The 4-path ensemble result + the consensus-voted canonical row."""

    paths: list[EnsemblePathOutput] = field(default_factory=list)
    voted_path: PathName | None = None
    consensus_score: float = 0.0
    voted_text: str | None = None

    source_pdf: str | None = None
    content_hash: str | None = None
    ingested_at: str | None = None
    subject: str | None = None
    jurisdiction: str | None = None

    @property
    def consensus_passed(self) -> bool:
        """Whether the winning path's consensus score meets the production
        threshold (0.60 — lower than the source's 0.70 RAGAS threshold
        because a pairwise-similarity signal is weaker evidence than a
        real faithfulness/relevance/precision computation would be; see
        the module docstring)."""
        return self.consensus_score >= 0.60


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _now_iso() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_one_path(path: PathName, image_path: str, timeout_seconds: float) -> EnsemblePathOutput:
    """Run one path synchronously (called inside a thread by `_run_all_paths_async`)."""
    backend = _PATH_BACKENDS[path]
    if not is_backend_available(backend):
        return EnsemblePathOutput(
            path=path, raw_response="", error=f"{backend.value} not configured"
        )

    start = time.monotonic()
    try:
        text, _extras = run_backend(
            backend, image_path, prompt=DEFAULT_PROMPT, timeout_seconds=timeout_seconds
        )
        return EnsemblePathOutput(
            path=path, raw_response=text, duration_ms=int((time.monotonic() - start) * 1000)
        )
    except CapabilityUnavailableError as exc:
        return EnsemblePathOutput(path=path, raw_response="", error=str(exc))
    except Exception as exc:
        logger.exception("_run_one_path: %s failed", path)
        return EnsemblePathOutput(path=path, raw_response="", error=str(exc))


async def _run_all_paths_async(image_path: str, timeout_seconds: float) -> list[EnsemblePathOutput]:
    """Run the 4 paths concurrently via `asyncio.to_thread` (the backend
    calls are synchronous SDK calls — Document AI, Vertex AI, and
    pypdfium2 are all blocking I/O, so threads parallelise them without
    needing async client variants of every SDK).
    """
    tasks = [
        asyncio.to_thread(_run_one_path, path, image_path, timeout_seconds)
        for path in _PATH_BACKENDS
    ]
    return list(await asyncio.gather(*tasks))


def _pairwise_similarity(a: str, b: str) -> float:
    """A cheap, dependency-free text-similarity signal (normalised token
    Jaccard). Not RAGAS — see the module docstring's honesty note.
    """
    tokens_a = set(a.lower().split())
    tokens_b = set(b.lower().split())
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = len(tokens_a & tokens_b)
    union = len(tokens_a | tokens_b)
    return intersection / union if union else 0.0


def consensus_vote(paths: list[EnsemblePathOutput]) -> tuple[PathName | None, float, str | None]:
    """Pick the path whose text is, on average, most similar to every
    other successful path's text (the paths that agree with each other
    are more likely to be right than the one outlier). Returns
    `(winning_path, consensus_score, winning_text)`.

    Falls back to the single longest successful response when fewer than
    2 paths succeeded (no pair to compare).
    """
    succeeded = [p for p in paths if p.succeeded]
    if not succeeded:
        return None, 0.0, None
    if len(succeeded) == 1:
        only = succeeded[0]
        return only.path, 0.5, only.raw_response  # unverified — no peer to agree with

    scores: dict[PathName, float] = {}
    for candidate in succeeded:
        similarities = [
            _pairwise_similarity(candidate.raw_response, other.raw_response)
            for other in succeeded
            if other.path != candidate.path
        ]
        scores[candidate.path] = sum(similarities) / len(similarities) if similarities else 0.0

    winner = max(scores, key=lambda p: scores[p])
    winning_output = next(p for p in succeeded if p.path == winner)
    return winner, scores[winner], winning_output.raw_response


class EnsembledExtractor:
    """The GCP-native 4-path consensus extractor. Mirrors
    `meaisinfhoghlaim.ocr.ensemble.EnsembledExtractor`'s public shape
    (`.extract(pdf_path, ...)` -> `EnsembleResult`) so call sites porting
    from that module need minimal changes.
    """

    def __init__(self, *, timeout_seconds: float = 30.0) -> None:
        self.timeout_seconds = timeout_seconds

    def extract(
        self,
        pdf_path: str | Path,
        *,
        jurisdiction: str = "ireland",
        subject: str | None = None,
    ) -> EnsembleResult:
        """Run the 4-path ensemble on one whole PDF and return the
        consensus-voted result. All 4 backends accept multi-page PDFs
        natively (Document AI, Gemini's native PDF understanding, and
        pypdfium2 all operate on the full document) — no per-page
        rendering loop needed, unlike the single-capability `ocr.py`
        router's `extract_pdf_text()`.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        content_hash = _file_hash(pdf_path)
        ingested_at = _now_iso()

        paths = asyncio.run(_run_all_paths_async(str(pdf_path), self.timeout_seconds))
        voted_path, consensus_score, voted_text = consensus_vote(paths)

        return EnsembleResult(
            paths=paths,
            voted_path=voted_path,
            consensus_score=consensus_score,
            voted_text=voted_text,
            source_pdf=str(pdf_path),
            content_hash=content_hash,
            ingested_at=ingested_at,
            subject=subject,
            jurisdiction=jurisdiction,
        )


__all__ = [
    "DEFAULT_PROMPT",
    "EnsemblePathOutput",
    "EnsembleResult",
    "EnsembledExtractor",
    "PathName",
    "consensus_vote",
]
