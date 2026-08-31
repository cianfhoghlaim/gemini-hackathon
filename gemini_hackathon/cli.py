"""``gemini_hackathon.cli`` — the canonical CLI entry point.

Console-script entry point referenced by ``pyproject.toml``::

    [project.scripts]
    gemini-hackathon = "gemini_hackathon.cli:main"

And the ``-m`` entry point via
:mod:`gemini_hackathon.__main__`. Both routes call :func:`main`.

Subcommands
===========

* ``theme``     — list / show / validate the 13 theming palettes.
* ``extract``   — run the BAML :func:`ExtractSourcePalette` extraction
                  on a PDF (in production; stub in tests + dev).
* ``pipeline``  — run the DLT pipelines
                  (``official_doc_fetcher`` /
                   ``safeguarding_fetcher`` /
                   ``pdf_page_metadata``).
* ``baml``      — run ``baml-cli generate`` / ``test`` / ``check``
                  against the ``baml_extracts/`` package.
* ``compare``   — run the Gemini-vs-Gemma4 extraction comparison
                  harness (writes to DuckDB ``model_comparisons``).
* ``serve``     — start the Hono + oRPC backend on port 8000 (the
                  Python backend that fronts the TanStack Start
                  frontend).

Dual-Profile Model Policy
=========================

Per the model-policy spec, the active :envvar:`MODEL_PROFILE`
governs which tiers are exposed. Every invocation prints the canonical
banner for the active profile:

  MODEL_PROFILE=hackathon (default):
    Tier 1 (primary)    : gemini-3.5-flash       (Vertex AI / AI Studio)
    Tier 2 (fallback)   : gemma-4-26b-a4b        (Unsloth Studio :8888)

  MODEL_PROFILE=dev (harness only; not exposed in submission):
    Tier 1 (primary)    : gemini-3.5-flash       (Vertex AI / AI Studio)
    Tier 2 (fallback)   : gemma-4-26b-a4b        (Unsloth Studio :8888)
    Tier 3 (dev)        : minimax-m3             (api.minimax.io)

Excluded models (Cloudflare Workers AI ``@cf/*`` and ``qwen3-coder-*``)
are documented in ``--help`` and hard-rejected at every ``call_llm()``
call.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, NoReturn

from gemini_hackathon.call_llm import (
    BACKOFF_BASE_SECONDS,
    HACKATHON_TIERS,
    DEV_TIERS,
    TIER_RETRY_BUDGETS,
)
from gemini_hackathon.model_registry import MODEL_REGISTRY, ModelProfile, model_for
from gemini_hackathon.theming import (
    SAFEGUARDING_SOURCES,
    Palette,
    list_all_palettes,
    load_palette,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Model-policy banner — sourced from the registry, not from constants.
# ---------------------------------------------------------------------------


def _format_banner(profile: ModelProfile) -> str:
    """Build the model-policy banner for the active profile."""
    tier_pairs = DEV_TIERS if profile == "dev" else HACKATHON_TIERS
    lines: list[str] = [
        "================================================================",
        "  gemini_hackathon — model policy (active profile: "
        f"{profile}{'' if profile == 'hackathon' else ' (NOT exposed in submission)'})",
        "  Source of truth: gemini_hackathon.model_registry.MODEL_REGISTRY",
        "================================================================",
    ]
    for i, (family, role) in enumerate(tier_pairs, start=1):
        entry = model_for(family, role, profile=profile)
        if entry is None:
            continue
        tier_label = f"Tier {i} ({role})"
        model_str = f"{entry.key:<30} ({entry.display_name})"
        backend_str = entry.backend
        lines.append(f"  {tier_label:24s} : {model_str} [{backend_str}]")
    lines.extend(
        [
            "----------------------------------------------------------------",
            f"  Retries per tier    : {dict(TIER_RETRY_BUDGETS)}",
            f"  Backoff base        : {BACKOFF_BASE_SECONDS}s (exponential)",
            "----------------------------------------------------------------",
            "  Excluded (hard-coded rejection):",
            "    * Cloudflare Workers AI  (@cf/* model strings)",
            "    * Qwen3-coder-*          (all model strings)",
            "================================================================",
        ]
    )
    return "\n".join(lines)


def _active_profile() -> ModelProfile:
    raw = os.environ.get("MODEL_PROFILE", "hackathon").strip().lower()
    return "dev" if raw == "dev" else "hackathon"


def _print_model_policy_banner(stream: Any = sys.stdout) -> None:
    print(_format_banner(_active_profile()), file=stream)


# ---------------------------------------------------------------------------
# Theming helpers (mirror of __init__.py exports)
# ---------------------------------------------------------------------------


def _short_palette_summary(p: dict[str, Any]) -> str:
    palette = p.get("palette", {})
    flag = p.get("flag", "")
    return (
        f"{p.get('sourceKey', '?'):40s} {flag:8s} "
        f"{p.get('jurisdiction', ''):20s} "
        f"primary={palette.get('primary', '')}"
    )


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gemini-hackathon",
        description=(
            "The gemini_hackathon CLI — theming + extraction + DLT + BAML + Hono backend "
            "surface for the BIEP Hackathon v3 public demo. See ARCHITECTURE.md.\n\n"
            "Model policy (every LLM call flows through gemini_hackathon.call_llm):\n"
            "  MODEL_PROFILE=hackathon (default): Tier 1 Gemini 3.5, Tier 2 Gemma 4.\n"
            "  MODEL_PROFILE=dev (harness only): adds minimax-m3 + Unsloth text set.\n\n"
            "Excluded (hard-coded rejection):\n"
            "  * Cloudflare Workers AI  (@cf/* model strings)\n"
            "  * Qwen3-coder-*          (all model strings)"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  gemini-hackathon theme list\n"
            "  gemini-hackathon theme show ncca.ie\n"
            "  gemini-hackathon extract --pdf-path /tmp/foo.pdf\n"
            "  gemini-hackathon pipeline run official_doc_fetcher\n"
            "  gemini-hackathon baml test\n"
            "  gemini-hackathon compare --pdf /tmp/lc_maths.pdf\n"
            "  gemini-hackathon serve --port 8000\n"
        ),
    )
    parser.add_argument("--version", action="version", version="gemini-hackathon 0.1.0")
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the model-policy banner on startup. Banner mentions "
        "the hackathon profile (gemini-3.5-flash + gemma-4-26b-a4b) by default.",
    )
    subparsers = parser.add_subparsers(dest="command", required=False, metavar="COMMAND")

    # ---- theme -----------------------------------------------------------
    theme_parser = subparsers.add_parser(
        "theme",
        help="Inspect + validate the theming palettes.",
        description="List, show, or validate the 13 canonical theming palettes.",
    )
    theme_sub = theme_parser.add_subparsers(dest="theme_action", metavar="ACTION")
    theme_sub.add_parser("list", help="List all 13 palettes.")
    theme_show = theme_sub.add_parser("show", help="Show one palette by source_key.")
    theme_show.add_argument("source_key", help="e.g. ncca.ie, aqa.org.uk")
    theme_sub.add_parser("count", help="Print the count of available palettes.")

    # ---- extract ---------------------------------------------------------
    extract_parser = subparsers.add_parser(
        "extract",
        help="Run the BAML ExtractSourcePalette extraction on a PDF.",
        description="Calls the BAML ExtractSourcePalette function (stub in dev).",
    )
    extract_parser.add_argument("--pdf-path", required=True, help="Path to the PDF.")
    extract_parser.add_argument("--source-name", default="", help="Optional display name.")

    # ---- pipeline --------------------------------------------------------
    pipeline_parser = subparsers.add_parser(
        "pipeline",
        help="Run the DLT pipelines.",
        description="Run the official_doc_fetcher, safeguarding_fetcher, or pdf_page_metadata DLT pipeline.",
    )
    pipeline_sub = pipeline_parser.add_subparsers(dest="pipeline_action", metavar="ACTION")
    pipeline_run = pipeline_sub.add_parser("run", help="Run one pipeline by name.")
    pipeline_run.add_argument(
        "name", choices=["official_doc_fetcher", "safeguarding_fetcher", "pdf_page_metadata", "all"]
    )

    # ---- baml ------------------------------------------------------------
    baml_parser = subparsers.add_parser(
        "baml",
        help="Run baml-cli generate/test/check.",
        description="Subcommands for baml-cli.",
    )
    baml_sub = baml_parser.add_subparsers(dest="baml_action", metavar="ACTION")
    baml_sub.add_parser("generate", help="Run baml-cli generate.")
    baml_sub.add_parser("test", help="Run baml-cli test.")
    baml_sub.add_parser("check", help="Run baml-cli check.")

    # ---- compare ---------------------------------------------------------
    compare_parser = subparsers.add_parser(
        "compare",
        help="Run the Gemini-vs-Gemma4 extraction comparison harness.",
        description="Runs the same BAML extraction under Gemini 3.5 and Gemma 4, scores with RAGAS, writes to DuckDB.",
    )
    compare_parser.add_argument("--pdf", required=True, help="Path to the PDF to compare on.")
    compare_parser.add_argument(
        "--duckdb", default="./data/gemini.duckdb", help="DuckDB output path."
    )

    # ---- serve -----------------------------------------------------------
    serve_parser = subparsers.add_parser(
        "serve",
        help="Spawn the Python backend (python -m gemini_hackathon.backend) on the given port.",
        description=(
            "Spawn the canonical Python backend (`python -m gemini_hackathon.backend`) "
            "and stream its stdout/stderr to the parent process. The backend serves "
            "/api/health, /api/models, /api/chat/completions, /api/themes, "
            "/api/observability/health, and the /api/agents/* + /api/assets/* "
            "session-tool routes."
        ),
    )
    serve_parser.add_argument("--port", type=int, default=8000, help="Port to bind.")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host to bind.")

    return parser


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------


def _cmd_theme(args: argparse.Namespace) -> int:
    action = args.theme_action
    if action == "list":
        palettes = list_all_palettes()
        for p in palettes:
            print(_short_palette_summary(p))
        return 0
    if action == "show":
        pal = load_palette(args.source_key)
        if pal is None:
            print(f"Palette not found: {args.source_key}", file=sys.stderr)
            return 1
        print(f"source_key     = {pal.source_key}")
        print(f"source_name    = {pal.source_name}")
        print(f"jurisdiction   = {pal.jurisdiction}")
        print(f"level          = {pal.level}")
        print(f"primary        = {pal.primary}")
        print(f"secondary      = {pal.secondary}")
        print(f"accent         = {pal.accent}")
        print(f"background     = {pal.background}")
        print(f"text           = {pal.text}")
        print(f"heading_font   = {pal.heading_font}")
        print(f"body_font      = {pal.body_font}")
        print(f"flag           = {pal.flag}")
        return 0
    if action == "count":
        print(len(list_all_palettes()))
        return 0
    return 1


def _cmd_extract(args: argparse.Namespace) -> int:
    from gemini_hackathon.theming import extract_source_palette_from_pdf

    result = extract_source_palette_from_pdf(args.pdf_path, args.source_name)
    print(json.dumps(result, indent=2))
    return 0


def _cmd_pipeline(args: argparse.Namespace) -> int:
    if args.pipeline_action == "run":
        targets = (
            ["official_doc_fetcher", "safeguarding_fetcher", "pdf_page_metadata"]
            if args.name == "all"
            else [args.name]
        )
        for t in targets:
            print(f"Running pipeline: {t}")
            rc = subprocess.call([sys.executable, "-m", f"dlt_pipelines.{t}"])
            if rc != 0:
                print(f"Pipeline {t} exited with code {rc}", file=sys.stderr)
                return rc
        return 0
    return 1


def _cmd_baml(args: argparse.Namespace) -> int:
    if args.baml_action is None:
        return 1
    cmd = ["baml-cli", args.baml_action]
    print(f"Running: {' '.join(cmd)}")
    return subprocess.call(cmd)


def _cmd_compare(args: argparse.Namespace) -> int:
    """Run the Gemini-vs-Gemma4 comparison harness."""
    from gemini_hackathon.compare import run_comparison

    result = run_comparison(pdf_path=args.pdf, duckdb_path=args.duckdb)
    print(json.dumps(result, indent=2, default=str))
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    """Spawn the canonical Python backend (``python -m gemini_hackathon.backend``).

    Per :mod:`gemini_hackathon.backend`'s docstring (line 27), the
    canonical invocation is ``python -m gemini_hackathon.backend`` which
    serves ``/api/health``, ``/api/models``, ``/api/chat/completions``,
    ``/api/themes``, ``/api/observability/health``, and the
    ``/api/agents/*`` + ``/api/assets/*`` session-tool routes.

    The previous implementation used ``http.server.SimpleHTTPRequestHandler``
    which only serves static files — none of the ``/api/*`` routes were
    reachable. This wrapper spawns the real backend as a subprocess with
    stdout/stderr piped to the parent so the operator sees the backend's
    logs in their terminal.
    """
    cmd = [
        sys.executable,
        "-m",
        "gemini_hackathon.backend",
        "--host",
        args.host,
        "--port",
        str(args.port),
    ]
    print(f"gemini-hackathon backend spawning: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd)
    try:
        return proc.wait()
    except KeyboardInterrupt:
        print(
            "\ngemini-hackathon: KeyboardInterrupt — terminating backend subprocess",
            file=sys.stderr,
        )
        proc.terminate()
        try:
            proc.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        return 130


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not args.quiet:
        _print_model_policy_banner()

    command = args.command
    if command is None:
        parser.print_help()
        return 0
    if command == "theme":
        return _cmd_theme(args)
    if command == "extract":
        return _cmd_extract(args)
    if command == "pipeline":
        return _cmd_pipeline(args)
    if command == "baml":
        return _cmd_baml(args)
    if command == "compare":
        return _cmd_compare(args)
    if command == "serve":
        return _cmd_serve(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
