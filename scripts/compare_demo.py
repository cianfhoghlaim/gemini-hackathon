"""Quick demo of the Gemini-vs-Gemma4 comparison harness.

Generates a synthetic PDF, runs the harness against it, and prints the
result. With both Gemini + Gemma backends stubbed (no network) this
verifies the DuckDB write path end-to-end.

Usage:
    python scripts/compare_demo.py
    mise run compare:demo
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


def main() -> int:
    # Write a stub PDF.
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"%PDF-1.4\n%fake\n%%EOF\n")
        pdf = f.name

    # Stub call_llm so no network is needed.
    from gemini_hackathon import call_llm as call_llm_mod
    from gemini_hackathon import compare as compare_mod
    from gemini_hackathon.call_llm import LLMResponse, TierAttempt

    good_json = json.dumps({
        "source_key": "demo", "source_name": "Demo", "jurisdiction": "Ireland",
        "level": "LC", "primary": "#00733B", "secondary": "#0E2D5C",
        "accent": "#F7B81C", "background": "#FFFFFF", "text": "#1A1A1A",
        "heading_font": "Merriweather", "body_font": "Inter",
    })

    def stub_call_llm(messages, **kwargs):
        return LLMResponse(
            content=good_json,
            model="gemini-3.5-flash",
            backend="vertex",
            tier=1,
            family="text_llm",
            role="default",
            latency_ms=10,
            tokens_in=128, tokens_out=64, cost_usd=0.0001,
            attempts=[TierAttempt(
                tier=1, family="text_llm", role="default",
                model="gemini-3.5-flash", backend="vertex",
                latency_ms=10, succeeded=True,
            )],
        )

    original_call_llm = call_llm_mod.call_llm
    call_llm_mod.call_llm = stub_call_llm
    compare_mod.call_llm = stub_call_llm
    try:
        with tempfile.TemporaryDirectory() as tmp:
            duckdb_path = os.path.join(tmp, "demo.duckdb")
            result = compare_mod.run_comparison(
                pdf_path=pdf,
                duckdb_path=duckdb_path,
                profile="hackathon",
            )
            print(json.dumps(result, indent=2, default=str))

            import duckdb
            con = duckdb.connect(duckdb_path, read_only=True)
            print("\n=== DuckDB state ===")
            for row in con.execute("""
                SELECT model_key, ragas_score, latency_ms, tokens_in, tokens_out
                FROM model_comparisons
                ORDER BY ragas_score DESC
            """).fetchall():
                print(f"  {row[0]:30s}  score={row[1]:.2f}  latency={row[2]}ms  in={row[3]}  out={row[4]}")
            con.close()
            print(f"\nDuckDB file: {duckdb_path}")
    finally:
        call_llm_mod.call_llm = original_call_llm
        os.unlink(pdf)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
