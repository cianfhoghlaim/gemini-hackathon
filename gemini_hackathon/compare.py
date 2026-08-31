"""Gemini-vs-Gemma4 comparison harness.

Runs the same BAML extraction under the active profile's text models,
scores each output with RAGAS, and writes the verdicts to a DuckDB
``model_comparisons`` table. In the hackathon profile this is Gemini 3.5
vs Gemma 4 26B-A4B; in dev profile the wider Unsloth text set joins.

This is the load-bearing artefact for "compare gemini vs different types
of gemma models" — the same BAML function is invoked under each entry,
the output is scored on the rubric in ``baml_extracts/extract_palette.baml``,
and the table is rendered both server-side (DuckDB) and client-side
(DuckDB-WASM via HTTP range requests) in the web UI.

Reference: openspec/changes/2026-08-24-gemini-hackathon-public-v1/specs/model-policy/spec.md
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .call_llm import call_llm, reset_router
from .model_registry import (
    MODEL_REGISTRY,
    ModelFamily,
    ModelProfile,
    public_model_roster,
)


@dataclass(frozen=True)
class ComparisonRow:
    pdf_sha256: str
    pdf_path: str
    prompt_template: str
    model_key: str
    model_alias: str | None
    backend: str
    profile: str
    family: ModelFamily
    role: str
    content: str
    latency_ms: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    ragas_score: float
    ragas_breakdown: dict[str, float]
    captured_at: str  # ISO datetime

    def to_duckdb_row(self) -> dict[str, Any]:
        d = asdict(self)
        d["ragas_breakdown"] = json.dumps(self.ragas_breakdown)
        return d


# The canonical prompt that drives every comparison. Sourced from the
# BAML extract_palette schema so both models are graded against the
# same rubric.
COMPARISON_PROMPT_TEMPLATE: str = (
    "You are an expert brand analyst. Given the following official document "
    "page text, return JSON with these fields exactly:\n"
    "  source_key, source_name, jurisdiction, level,\n"
    "  primary (hex), secondary (hex), accent (hex),\n"
    "  background (hex), text (hex), heading_font, body_font,\n"
    "  flag (emoji or empty string).\n"
    "Reply with ONLY the JSON object.\n\n"
    "DOCUMENT TEXT:\n{document_text}\n"
)


def _hash_pdf(path: str) -> str:
    """SHA-256 of the PDF bytes (used as a stable comparison key)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _extract_pdf_text(path: str, max_chars: int = 12_000) -> str:
    """Best-effort text extraction. Falls back to the empty string."""
    try:
        import pypdf  # type: ignore[import-not-found]

        reader = pypdf.PdfReader(path)
        chunks: list[str] = []
        total = 0
        for page in reader.pages:
            text = page.extract_text() or ""
            chunks.append(text)
            total += len(text)
            if total >= max_chars:
                break
        return "".join(chunks)[:max_chars]
    except Exception as e:
        return f"<text extraction failed: {type(e).__name__}: {e}>"


def _score_with_ragas(
    content: str, ground_truth: dict[str, Any] | None
) -> tuple[float, dict[str, float]]:
    """RAGAS-style fidelity scoring.

    A full RAGAS eval requires an LLM judge. For the hackathon harness we
    ship a deterministic schema-fidelity scorer: it checks that every
    required field is present + non-empty + plausibly-typed (hex for colours,
    non-empty for fonts). The numeric score is the fraction of fields
    that pass. The full RAGAS judge wiring is a Phase 4 follow-up.

    Returns:
        (overall_score, breakdown_dict)
    """
    required = [
        "source_key",
        "source_name",
        "jurisdiction",
        "level",
        "primary",
        "secondary",
        "accent",
        "background",
        "text",
        "heading_font",
        "body_font",
    ]
    breakdown: dict[str, float] = {}
    if not content.strip():
        return 0.0, dict.fromkeys(required, 0.0)

    # Try to extract the JSON object.
    parsed: dict[str, Any] = {}
    try:
        # Strip code fences if present.
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = "\n".join(cleaned.split("\n")[1:])
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
        parsed = json.loads(cleaned)
    except Exception:
        pass

    for field_name in required:
        present = field_name in parsed and bool(parsed[field_name])
        if present and field_name in {"primary", "secondary", "accent", "background", "text"}:
            val = str(parsed[field_name])
            present = val.startswith("#") and len(val) in (4, 7)
        breakdown[field_name] = 1.0 if present else 0.0

    overall = sum(breakdown.values()) / max(1, len(breakdown))
    return overall, breakdown


def run_comparison(
    pdf_path: str,
    duckdb_path: str = "./data/gemini.duckdb",
    profile: ModelProfile | None = None,
) -> dict[str, Any]:
    """Run the harness end-to-end.

    Steps:
        1. Hash the PDF.
        2. Extract text (pypdf; truncated to 12k chars).
        3. For every ``text_llm`` entry in the active profile, call
           :func:`call_llm` with the same prompt template + same
           extraction message.
        4. Score each response with the RAGAS-fidelity scorer.
        5. Write the rows to DuckDB ``model_comparisons`` (if available).

    Returns:
        A dict with the rows + summary statistics, suitable for JSON
        serialisation in the ``compare`` CLI subcommand.
    """
    active = profile or _active_profile()
    reset_router()

    pdf_sha = _hash_pdf(pdf_path)
    document_text = _extract_pdf_text(pdf_path)
    prompt = COMPARISON_PROMPT_TEMPLATE.format(document_text=document_text)

    text_entries = [e for e in MODEL_REGISTRY.for_profile(active) if e.family == "text_llm"]

    rows: list[ComparisonRow] = []
    for entry in text_entries:
        # Pin the call to this exact entry so we don't fall through.
        try:
            response = call_llm(
                [{"role": "user", "content": prompt}],
                profile=active,
                family="text_llm",
                role=entry.role,
            )
        except Exception:
            continue

        score, breakdown = _score_with_ragas(response.content, ground_truth=None)
        rows.append(
            ComparisonRow(
                pdf_sha256=pdf_sha,
                pdf_path=pdf_path,
                prompt_template=COMPARISON_PROMPT_TEMPLATE,
                model_key=entry.key,
                model_alias=response.model,
                backend=response.backend,
                profile=active,
                family=response.family,
                role=response.role,
                content=response.content,
                latency_ms=response.latency_ms,
                tokens_in=response.tokens_in,
                tokens_out=response.tokens_out,
                cost_usd=response.cost_usd,
                ragas_score=score,
                ragas_breakdown=breakdown,
                captured_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )
        )

    _write_to_duckdb(rows, duckdb_path)

    # The public roster is always the hackathon profile, regardless of
    # what was actually compared. This is what docs and UI render.
    public = [
        {
            "key": e.key,
            "family": e.family,
            "backend": e.backend,
            "tier": e.tier,
            "display_name": e.display_name,
        }
        for e in public_model_roster()
    ]
    return {
        "profile": active,
        "pdf_path": pdf_path,
        "pdf_sha256": pdf_sha,
        "rows": [r.to_duckdb_row() for r in rows],
        "summary": {
            "public_roster": public,
            "models_compared": len(rows),
            "best_score": max((r.ragas_score for r in rows), default=0.0),
            "fastest_latency_ms": min((r.latency_ms for r in rows), default=0),
        },
    }


def _active_profile() -> ModelProfile:
    raw = os.environ.get("MODEL_PROFILE", "hackathon").strip().lower()
    return "dev" if raw == "dev" else "hackathon"


def _write_to_duckdb(rows: list[ComparisonRow], duckdb_path: str) -> None:
    """Persist rows to DuckDB (best-effort; skipped if duckdb not installed)."""
    if not rows:
        return
    try:
        import duckdb  # type: ignore[import-not-found]
    except ImportError:
        return
    Path(duckdb_path).parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(duckdb_path)
    try:
        con.execute("""
            CREATE TABLE IF NOT EXISTS model_comparisons (
                pdf_sha256 TEXT NOT NULL,
                pdf_path TEXT NOT NULL,
                prompt_template TEXT,
                model_key TEXT NOT NULL,
                model_alias TEXT,
                backend TEXT,
                profile TEXT,
                family TEXT,
                role TEXT,
                content TEXT,
                latency_ms INTEGER,
                tokens_in INTEGER,
                tokens_out INTEGER,
                cost_usd DOUBLE,
                ragas_score DOUBLE,
                ragas_breakdown TEXT,
                captured_at TIMESTAMP
            )
        """)
        cols = (
            "pdf_sha256, pdf_path, prompt_template, model_key, model_alias, "
            "backend, profile, family, role, content, latency_ms, tokens_in, "
            "tokens_out, cost_usd, ragas_score, ragas_breakdown, captured_at"
        )
        placeholders = ",".join(["?"] * 17)
        for r in rows:
            con.execute(
                f"INSERT INTO model_comparisons ({cols}) VALUES ({placeholders})",
                [
                    r.pdf_sha256,
                    r.pdf_path,
                    r.prompt_template,
                    r.model_key,
                    r.model_alias,
                    r.backend,
                    r.profile,
                    r.family,
                    r.role,
                    r.content,
                    r.latency_ms,
                    r.tokens_in,
                    r.tokens_out,
                    r.cost_usd,
                    r.ragas_score,
                    r.ragas_breakdown,
                    r.captured_at,
                ],
            )
    finally:
        con.close()


__all__ = [
    "COMPARISON_PROMPT_TEMPLATE",
    "ComparisonRow",
    "run_comparison",
]
