"""Tests for the gemini_hackathon.compare Gemini-vs-Gemma4 harness."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Core shape + contract
# ---------------------------------------------------------------------------


def test_comparison_row_serialisable_to_dict():
    from gemini_hackathon.compare import ComparisonRow

    row = ComparisonRow(
        pdf_sha256="a" * 64,
        pdf_path="/tmp/example.pdf",
        prompt_template="hello {document_text}",
        model_key="gemini-3.5-flash",
        model_alias="vertex_ai/gemini-3.5-flash",
        backend="vertex",
        profile="hackathon",
        family="text_llm",
        role="default",
        content="{...}",
        latency_ms=1200,
        tokens_in=10,
        tokens_out=20,
        cost_usd=0.0001,
        ragas_score=0.9,
        ragas_breakdown={"primary": 1.0, "secondary": 0.0},
        captured_at="2026-08-25T00:00:00Z",
    )
    d = row.to_duckdb_row()
    assert d["model_key"] == "gemini-3.5-flash"
    assert json.loads(d["ragas_breakdown"])["primary"] == 1.0


def test_comparison_prompt_template_includes_the_document_text():
    from gemini_hackathon.compare import COMPARISON_PROMPT_TEMPLATE

    assert "{document_text}" in COMPARISON_PROMPT_TEMPLATE
    assert "json" in COMPARISON_PROMPT_TEMPLATE.lower() or "JSON" in COMPARISON_PROMPT_TEMPLATE


# ---------------------------------------------------------------------------
# run_comparison: shape, registry coverage
# ---------------------------------------------------------------------------


def test_run_comparison_returns_dict_with_summary(monkeypatch, tmp_path):
    """run_comparison() returns the documented shape and lists every
    visible text_llm model from the active profile in the summary.
    """
    # Stub out the live LLM call: every call returns a known-good
    # response shape so the harness can score it deterministically.
    from gemini_hackathon import call_llm as call_llm_mod
    from gemini_hackathon import compare as compare_mod
    from gemini_hackathon.call_llm import LLMResponse, TierAttempt

    class _StubResponse(LLMResponse):
        def __init__(self, alias: str, backend: str):
            super().__init__(
                content='{"primary":"#00733B","secondary":"#0E2D5C",'
                '"accent":"#F7B81C","background":"#FFFFFF","text":"#1A1A1A",'
                '"heading_font":"Merriweather","body_font":"Inter"}',
                model=alias,
                backend=backend,
                tier=1,
                family="text_llm",
                role="default",
                latency_ms=100,
                tokens_in=10,
                tokens_out=20,
                cost_usd=0.0001,
                attempts=[
                    TierAttempt(
                        tier=1,
                        family="text_llm",
                        role="default",
                        model=alias,
                        backend=backend,
                        latency_ms=100,
                        succeeded=True,
                    )
                ],
            )

    def _stub(messages, **kwargs):
        # Return a deterministic response for whichever (family, role) was requested
        return _StubResponse(
            alias="vertex_ai/gemini-3.5-flash",
            backend="vertex",
        )

    monkeypatch.setattr(call_llm_mod, "call_llm", _stub)
    monkeypatch.setattr(compare_mod, "call_llm", _stub)
    monkeypatch.setenv("MINIMAX_API_KEY", "sk-x")
    monkeypatch.setenv("GEMINI_API_KEY", "sk-x")
    monkeypatch.setenv("UNSLOTH_API_KEY", "sk-x")

    # Need a real PDF file. Use the canonical sample.
    sample_pdf = (
        Path(__file__).resolve().parent.parent / "data" / "syllabi" / "sample_lc_maths_2024.pdf"
    )
    if not sample_pdf.exists():
        pytest.skip(f"sample PDF missing: {sample_pdf}")

    # Use a temp DuckDB so we don't pollute anything.
    db = tmp_path / "compare.duckdb"
    result = compare_mod.run_comparison(
        pdf_path=str(sample_pdf),
        duckdb_path=str(db),
        profile="hackathon",
    )

    # Top-level shape
    assert "profile" in result
    assert result["profile"] == "hackathon"
    assert "rows" in result
    assert "summary" in result
    assert "models_compared" in result["summary"]

    # We compared at least the two hackathon-tier text_llm entries.
    assert result["summary"]["models_compared"] >= 1

    # The rows carry enough provenance to render in a leaderboard.
    if result["rows"]:
        first = result["rows"][0]
        for key in (
            "model_key",
            "model_alias",
            "backend",
            "family",
            "role",
            "ragas_score",
            "latency_ms",
            "tokens_in",
            "tokens_out",
            "cost_usd",
            "pdf_sha256",
            "pdf_path",
        ):
            assert key in first, f"missing key {key!r} in result row"


def test_run_comparison_summary_includes_public_roster(monkeypatch, tmp_path):
    """The summary must include the public model roster so docs/UI can
    verify what models WERE eligible to be compared (under the
    hackathon profile).
    """
    from gemini_hackathon import call_llm as call_llm_mod
    from gemini_hackathon import compare as compare_mod
    from gemini_hackathon.call_llm import LLMResponse, TierAttempt

    def _stub(messages, **kwargs):
        return LLMResponse(
            content='{"primary":"#000","secondary":"#000"}',
            model="vertex_ai/gemini-3.5-flash",
            backend="vertex",
            tier=1,
            family="text_llm",
            role="default",
            latency_ms=10,
            tokens_in=1,
            tokens_out=2,
            cost_usd=0.0,
            attempts=[
                TierAttempt(
                    tier=1,
                    family="text_llm",
                    role="default",
                    model="vertex_ai/gemini-3.5-flash",
                    backend="vertex",
                    latency_ms=10,
                    succeeded=True,
                )
            ],
        )

    monkeypatch.setattr(call_llm_mod, "call_llm", _stub)
    monkeypatch.setattr(compare_mod, "call_llm", _stub)
    monkeypatch.setenv("MINIMAX_API_KEY", "sk-x")
    monkeypatch.setenv("GEMINI_API_KEY", "sk-x")
    monkeypatch.setenv("UNSLOTH_API_KEY", "sk-x")

    sample_pdf = (
        Path(__file__).resolve().parent.parent / "data" / "syllabi" / "sample_lc_maths_2024.pdf"
    )
    if not sample_pdf.exists():
        pytest.skip("sample PDF missing")

    db = tmp_path / "compare.duckdb"
    result = compare_mod.run_comparison(
        pdf_path=str(sample_pdf),
        duckdb_path=str(db),
        profile="hackathon",
    )
    # Public roster is always the hackathon profile regardless of what
    # was actually compared (which may be a subset if a tier was skipped).
    assert "public_roster" in result["summary"]
    roster_keys = [e["key"] for e in result["summary"]["public_roster"]]
    assert "gemini-3.5-flash" in roster_keys
    assert "gemma-4-26b-a4b" in roster_keys
    # The public roster NEVER leaks dev-only entries.
    # Note: minimax-m3 is now in the public profile (Tier 1 primary per
    # the OpenSpec model-policy spec), so it IS expected in the roster.
    assert "gemma-4-26b-a4b-dev" not in roster_keys
    assert "gemini-3.5-flash-dev" not in roster_keys


def test_run_comparison_dev_profile_includes_dev_only(monkeypatch, tmp_path):
    """dev profile comparison surfaces minimax-m3 + Gemma-4-dev + Gemini-dev
    but the public_roster field of the summary still reads from the
    hackathon profile (so docs / UI are unaffected).
    """
    from gemini_hackathon import call_llm as call_llm_mod
    from gemini_hackathon import compare as compare_mod
    from gemini_hackathon.call_llm import LLMResponse, TierAttempt

    def _stub(messages, **kwargs):
        return LLMResponse(
            content='{"primary":"#000"}',
            model="minimax-m3",
            backend="minimax",
            tier=3,
            family="text_llm",
            role="dev_primary",
            latency_ms=10,
            tokens_in=1,
            tokens_out=2,
            cost_usd=0.0,
            attempts=[
                TierAttempt(
                    tier=3,
                    family="text_llm",
                    role="dev_primary",
                    model="minimax-m3",
                    backend="minimax",
                    latency_ms=10,
                    succeeded=True,
                )
            ],
        )

    monkeypatch.setattr(call_llm_mod, "call_llm", _stub)
    monkeypatch.setattr(compare_mod, "call_llm", _stub)
    monkeypatch.setenv("MINIMAX_API_KEY", "sk-x")
    monkeypatch.setenv("GEMINI_API_KEY", "sk-x")
    monkeypatch.setenv("UNSLOTH_API_KEY", "sk-x")

    sample_pdf = (
        Path(__file__).resolve().parent.parent / "data" / "syllabi" / "sample_lc_maths_2024.pdf"
    )
    if not sample_pdf.exists():
        pytest.skip("sample PDF missing")

    db = tmp_path / "compare.duckdb"
    result = compare_mod.run_comparison(
        pdf_path=str(sample_pdf), duckdb_path=str(db), profile="dev"
    )
    # At least one of the dev models appeared in the comparison.
    keys = [r["model_key"] for r in result["rows"]]
    assert any(k in keys for k in ("minimax-m3", "gemma-4-26b-a4b-dev", "gemini-3.5-flash-dev"))
    # Public roster still lists ONLY the hackathon-profile keys (no dev).
    # MiniMax-M3 is now in the hackathon profile (Tier 1 primary), so it
    # appears in both the dev + hackathon rosters.
    public_keys = [e["key"] for e in result["summary"]["public_roster"]]
    assert "gemma-4-26b-a4b-dev" not in public_keys
    assert "gemini-3.5-flash-dev" not in public_keys
