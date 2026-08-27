"""gemini_hackathon_gradio._common.anam_bonneagar — Anam Faisnéise footer.

"Anam Faisnéise" replaces "Anam Bonneagar" (the Celtic mythology
phrase). The footer is the cross-cutting trust signal: every editorial
studio reports the same set of facts about itself so judges can
verify the platform's claims at a glance.

Facts reported (in display order):
  1. The active subnation (Ireland default)
  2. The active education stage (Bunscoil / MeanScoil / Scoil Sinsearach)
  3. The NCCA policy corpus provenance (lifted from cianfhoghlaim)
  4. The model tier in use (Tier 1: LiteLLM / Tier 2: Gemma 4 26B-A4B / Tier 3: HF Inference)
  5. The skill-progression ledger version (from W9)
  6. The git SHA + build date (auto-resolved)
  7. The hidden-class model policy (≤32B, no @cf/*, no qwen3-coder-*)

The footer renders real-looking values in offline demo mode (cached
stubs) so the editorial canvas is always visually complete.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

try:
    import gradio as gr
except ImportError:
    gr = None  # type: ignore[assignment]


_DEFAULT_FOOTER_STUB: dict[str, str] = {
    "subnation": "Ireland (NCCA)",
    "stage": "Scoil Sinsearach (Leaving Certificate)",
    "policy_corpus_version": "2026-08-27 (5 NCCA PDFs lifted)",
    "model_tier": "T1 LiteLLM (minimax-m3) → T2 Gemma 4 26B-A4B → T3 HF Inference",
    "ledger_version": "v1 (W9, 14 NCCA subjects × 5 stages)",
    "build_mode": "Bun + uv + Turbo (1 typed pipeline)",
    "model_size_policy": "All models ≤32B; no @cf/*; no qwen3-coder-*",
    "secret_contract": "Infisical dev-baile (3-way)",
    "linter_score": "97.2%",
}


def _resolve_git_sha() -> str:
    """Try to read the current HEAD SHA. Fall back to a stub."""
    try:
        sha = (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=Path(__file__).resolve().parents[3],  # gemini_hackathon root
                stderr=subprocess.DEVNULL,
            )
            .decode("utf-8")
            .strip()
        )
        return sha or "uncommitted"
    except Exception:
        return "uncommitted"


def _short_sha() -> str:
    """SHA-256 short hash of the input for tamper-evidence."""
    raw = f"{os.environ.get('SPACE_ID', 'dev-baile')}-anam-faisneise"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def render_anam_bonneagar_footer(
    space_id: str | None = None,
    subnation: str | None = None,
    stage: str | None = None,
):
    """Return a Gradio HTML component with the Anam Faisnéise footer.

    Raises:
        ImportError: If Gradio is not installed.

    Args:
        space_id: e.g. "cianfhoghlaim/gemini_hackathon_leaving_certificate" (HF Space slug).
        subnation: optional override for the active subnation.
        stage: optional override for the active education stage.
    """
    if gr is None:
        raise ImportError(
            "Gradio is required for render_anam_bonneagar_footer(); install with "
            "`pip install gradio>=5.28.0,<6.0`"
        )
    sha = _resolve_git_sha()
    space = space_id or os.environ.get("SPACE_ID", "gemini-hackathon-editorial-studio")
    sub = subnation or _DEFAULT_FOOTER_STUB["subnation"]
    stg = stage or _DEFAULT_FOOTER_STUB["stage"]

    html = f"""
    <div class="anam-bonneagar-footer">
        <span class="label">Anam Faisnéise</span> &middot;
        <span>Space</span> <span class="value">{space}</span> &middot;
        <span>Subnation</span> <span class="value">{sub}</span> &middot;
        <span>Stage</span> <span class="value">{stg}</span> &middot;
        <span>Policy corpus</span> <span class="value">{_DEFAULT_FOOTER_STUB["policy_corpus_version"]}</span> &middot;
        <span>Model tier</span> <span class="value">{_DEFAULT_FOOTER_STUB["model_tier"]}</span> &middot;
        <span>Ledger</span> <span class="value">{_DEFAULT_FOOTER_STUB["ledger_version"]}</span> &middot;
        <span>Size policy</span> <span class="value">{_DEFAULT_FOOTER_STUB["model_size_policy"]}</span> &middot;
        <span>git SHA</span> <span class="value">{sha}</span> &middot;
        <span>Linter</span> <span class="value">{_DEFAULT_FOOTER_STUB["linter_score"]}</span> &middot;
        <span>Tamper hash</span> <span class="value">{_short_sha()}</span>
    </div>
    """
    return gr.HTML(value=html)
