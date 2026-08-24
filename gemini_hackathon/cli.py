"""``gemini_hackathon.cli`` — the canonical CLI entry point.

The :mod:`gemini_hackathon.cli` module is the console-script entry
point referenced by ``pyproject.toml``::

    [project.scripts]
    gemini-hackathon = "gemini_hackathon.cli:main"

And also the ``-m`` entry point via
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
* ``serve``     — start the Hono + oRPC backend on port 8000 (the
                  Python backend that fronts the TanStack Start
                  frontend).

3-Tier Model Policy
===================

Per the model-policy spec every invocation prints the canonical
3-tier model policy banner to ``stdout``::

    Tier 1 (primary)   : minimax-m3                       (api.minimax.io)
    Tier 2 (fallback)  : unsloth/gemma-4-26B-A4B-it-GGUF (local llama.cpp)
    Tier 3 (last resort): vertex_ai/gemini-3.5-flash     (Vertex AI)

The banner is suppressed with ``--quiet``. Excluded models
(``@cf/...`` and ``qwen3-coder-*``) are documented in ``--help``
output via the :class:`_HelpAction` print-on-help callback.
"""

from __future__ import annotations

import argparse
import http.server
import json
import logging
import os
import socketserver
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, NoReturn

from gemini_hackathon.call_llm import (
    BACKOFF_BASE_SECONDS,
    TIER_1_MODEL,
    TIER_2_MODEL,
    TIER_3_MODEL,
    TIER_ORDER,
    TIER_RETRY_BUDGETS,
)
from gemini_hackathon.theming import (
    SAFEGUARDING_SOURCES,
    Palette,
    list_all_palettes,
    load_palette,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 3-tier model policy banner
# ---------------------------------------------------------------------------

MODEL_POLICY_BANNER: str = (
    "================================================================\n"
    "  gemini_hackathon — 3-tier LLM model policy\n"
    "  (see openspec/changes/2026-08-24-gemini-hackathon-public-v1/\n"
    "   specs/model-policy/spec.md for the canonical contract)\n"
    "================================================================\n"
    f"  Tier 1 (primary)    : {TIER_1_MODEL:<34}  (api.minimax.io)\n"
    f"  Tier 2 (fallback)   : {TIER_2_MODEL:<34}  (local llama.cpp)\n"
    f"  Tier 3 (last resort): {TIER_3_MODEL:<34}  (Vertex AI Gemini)\n"
    "----------------------------------------------------------------\n"
    f"  Retries per tier    : {dict(TIER_RETRY_BUDGETS)}\n"
    f"  Backoff base       : {BACKOFF_BASE_SECONDS}s (exponential)\n"
    "----------------------------------------------------------------\n"
    "  Excluded (hard-coded rejection):\n"
    "    * Cloudflare Workers AI  (@cf/* model strings)\n"
    "    * Qwen3-coder-*          (all model strings)\n"
    "================================================================"
)


def _print_model_policy_banner(stream: Any = sys.stdout) -> None:
    """Print the 3-tier model policy banner to ``stream``.

    Args:
        stream: The output stream (default ``sys.stdout``).
    """
    print(MODEL_POLICY_BANNER, file=stream)


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build the canonical :class:`argparse.ArgumentParser`.

    The parser exposes 5 subcommands (``theme`` / ``extract`` /
    ``pipeline`` / ``baml`` / ``serve``) plus the global
    ``--quiet`` flag (suppresses the model-policy banner) and the
    ``--version`` flag (prints the package version).

    The 3-tier model policy (Tier 1 ``minimax-m3`` / Tier 2
    ``unsloth/gemma-4-26B-A4B-it-GGUF`` / Tier 3
    ``vertex_ai/gemini-3.5-flash``) is documented in the
    ``--help`` output below, AND printed to ``stdout`` on every
    invocation (suppress with ``--quiet``). Cloudflare Workers AI
    (``@cf/*``) and Qwen3-coder (``qwen3-coder-*``) model strings
    are hard-coded rejections per
    ``openspec/changes/2026-08-24-gemini-hackathon-public-v1/specs/model-policy/spec.md``.
    """
    parser = argparse.ArgumentParser(
        prog="gemini-hackathon",
        description=(
            "The gemini_hackathon CLI — the theming + extraction + "
            "DLT + BAML + Hono backend surface for the BIEP Hackathon "
            "v3 public demo. See ARCHITECTURE.md for the full layout.\n\n"
            "3-tier model policy (every LLM call flows through here):\n"
            f"  Tier 1 (primary)    : {TIER_1_MODEL:<34}  (api.minimax.io)\n"
            f"  Tier 2 (fallback)   : {TIER_2_MODEL:<34}  (local llama.cpp)\n"
            f"  Tier 3 (last resort): {TIER_3_MODEL:<34}  (Vertex AI Gemini)\n\n"
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
            "  gemini-hackathon serve --port 8000\n"
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version="gemini-hackathon 0.1.0",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the 3-tier model policy banner on startup.",
    )

    subparsers = parser.add_subparsers(dest="command", required=False, metavar="COMMAND")

    # ---- theme subcommand ------------------------------------------------
    theme_parser = subparsers.add_parser(
        "theme",
        help="Inspect + validate the theming palettes.",
        description="List, show, or validate the 13 canonical theming palettes.",
    )
    theme_sub = theme_parser.add_subparsers(dest="theme_action", metavar="ACTION")

    # theme list
    theme_sub.add_parser(
        "list",
        help="List all 13 palettes (8 jurisdictions + 5 safeguarding).",
    )
    # theme show <source-key>
    theme_show = theme_sub.add_parser(
        "show",
        help="Show a single palette (CSS variables + source metadata).",
    )
    theme_show.add_argument(
        "source_key",
        help="The source key (e.g. 'ncca.ie', 'gov.ie/education').",
    )
    # theme validate <source-key>
    theme_validate = theme_sub.add_parser(
        "validate",
        help="Validate that a palette has all required fields.",
    )
    theme_validate.add_argument(
        "source_key",
        help="The source key to validate.",
    )

    # ---- extract subcommand ---------------------------------------------
    extract_parser = subparsers.add_parser(
        "extract",
        help="Run BAML extraction on a PDF (theming palette).",
        description=(
            "Run the BAML ExtractSourcePalette function on the given PDF. "
            "In production this hits the BAML runtime; in tests/dev it "
            "returns a deterministic stub."
        ),
    )
    extract_parser.add_argument(
        "--pdf-path",
        required=True,
        help="Absolute path to the PDF to extract from.",
    )
    extract_parser.add_argument(
        "--source-name",
        default="",
        help="Optional human-readable source name (e.g. 'NCCA').",
    )

    # ---- pipeline subcommand --------------------------------------------
    pipeline_parser = subparsers.add_parser(
        "pipeline",
        help="Run the DLT pipelines (official_doc / safeguarding / pdf_metadata).",
        description=(
            "Run one of the 3 DLT pipelines. Each pipeline writes to the "
            "canonical DuckDB file at ./gemini_hackathon.duckdb."
        ),
    )
    pipeline_sub = pipeline_parser.add_subparsers(dest="pipeline_action", metavar="ACTION")
    pipeline_sub.add_parser(
        "list",
        help="List the 3 available pipelines.",
    )
    pipeline_run = pipeline_sub.add_parser(
        "run",
        help="Run a single pipeline.",
    )
    pipeline_run.add_argument(
        "name",
        choices=("official_doc_fetcher", "safeguarding_fetcher", "pdf_page_metadata", "all"),
        help="The pipeline to run (or 'all' for the full chain).",
    )

    # ---- baml subcommand -------------------------------------------------
    baml_parser = subparsers.add_parser(
        "baml",
        help="Run baml-cli (generate / test / check).",
        description="Run the BAML CLI against the baml_extracts/ package.",
    )
    baml_sub = baml_parser.add_subparsers(dest="baml_action", metavar="ACTION")
    baml_sub.add_parser(
        "generate",
        help="Run `baml-cli generate` to (re)build the baml_client/ packages.",
    )
    baml_sub.add_parser(
        "test",
        help="Run `baml-cli test` against the baml_extracts/ package.",
    )
    baml_sub.add_parser(
        "check",
        help="Run `baml-cli check` (lint the .baml files).",
    )

    # ---- serve subcommand -----------------------------------------------
    serve_parser = subparsers.add_parser(
        "serve",
        help="Start the Hono + oRPC backend on port 8000 (Python).",
        description=(
            "Start the Python backend that fronts the TanStack Start "
            "frontend. The backend exposes the /api/agui/stream "
            "endpoint + the /api/health endpoint."
        ),
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="The port to bind to (default 8000).",
    )
    serve_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="The host to bind to (default 127.0.0.1).",
    )

    return parser


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------


def _cmd_theme_list(args: argparse.Namespace) -> int:
    """List all available palettes.

    Args:
        args: The parsed argparse namespace (unused).

    Returns:
        Exit code (``0`` = success).
    """
    palettes = list_all_palettes()
    if not palettes:
        print(
            "No palettes found. The themes/ directory may be empty.",
            file=sys.stderr,
        )
        return 1
    print(f"Found {len(palettes)} palette(s):")
    for entry in palettes:
        print(
            f"  - {entry.get('sourceKey', '?'):<40} "
            f"jurisdiction={entry.get('jurisdiction', '?'):<20} "
            f"level={entry.get('level', '?')}"
        )
    return 0


def _cmd_theme_show(args: argparse.Namespace) -> int:
    """Show a single palette (CSS variables + metadata).

    Args:
        args: The parsed argparse namespace.

    Returns:
        Exit code (``0`` = success, ``1`` = palette not found).
    """
    palette = load_palette(args.source_key)
    if palette is None:
        print(f"Palette not found: {args.source_key}", file=sys.stderr)
        return 1

    print(f"Palette: {palette.source_key}")
    print(f"  source_name   : {palette.source_name}")
    print(f"  jurisdiction  : {palette.jurisdiction}")
    print(f"  level         : {palette.level}")
    print(f"  primary       : {palette.primary}")
    print(f"  secondary     : {palette.secondary}")
    print(f"  accent        : {palette.accent}")
    print(f"  background    : {palette.background}")
    print(f"  text          : {palette.text}")
    print(f"  heading_font  : {palette.heading_font}")
    print(f"  body_font     : {palette.body_font}")
    print(f"  logo_url      : {palette.logo_url}")
    print(f"  flag          : {palette.flag}")
    print("  CSS variables :")
    for key, value in palette.css_variables.items():
        print(f"    {key:<22} : {value}")
    return 0


def _cmd_theme_validate(args: argparse.Namespace) -> int:
    """Validate that a palette has all required fields.

    Args:
        args: The parsed argparse namespace.

    Returns:
        Exit code (``0`` = valid, ``1`` = invalid / missing).
    """
    palette = load_palette(args.source_key)
    if palette is None:
        print(f"FAIL: palette not found: {args.source_key}", file=sys.stderr)
        return 1

    issues: list[str] = []
    if not palette.source_key:
        issues.append("missing source_key")
    if not palette.primary.startswith("#") or len(palette.primary) != 7:
        issues.append(f"invalid primary hex: {palette.primary!r}")
    if not palette.background.startswith("#") or len(palette.background) != 7:
        issues.append(f"invalid background hex: {palette.background!r}")
    if not palette.heading_font:
        issues.append("missing heading_font")
    if not palette.body_font:
        issues.append("missing body_font")

    if issues:
        print(f"FAIL: {palette.source_key} has issues:", file=sys.stderr)
        for issue in issues:
            print(f"  - {issue}", file=sys.stderr)
        return 1
    print(f"OK: {palette.source_key} validates cleanly")
    return 0


def _cmd_extract(args: argparse.Namespace) -> int:
    """Run the BAML extraction (stub in tests + dev).

    Args:
        args: The parsed argparse namespace.

    Returns:
        Exit code (``0`` = success).
    """
    from gemini_hackathon.theming import extract_source_palette_from_pdf

    if not Path(args.pdf_path).exists():
        print(f"PDF not found: {args.pdf_path}", file=sys.stderr)
        return 1

    result = extract_source_palette_from_pdf(
        pdf_path=args.pdf_path,
        source_name=args.source_name,
    )
    print(json.dumps(result, indent=2))
    return 0


def _cmd_pipeline_list(args: argparse.Namespace) -> int:
    """List the available DLT pipelines.

    Args:
        args: The parsed argparse namespace (unused).

    Returns:
        Exit code (``0`` = success).
    """
    print("Available DLT pipelines:")
    print("  - official_doc_fetcher    (8 jurisdiction resources)")
    print("  - safeguarding_fetcher    (5 safeguarding resources)")
    print("  - pdf_page_metadata       (downstream of official_doc_fetcher)")
    return 0


def _cmd_pipeline_run(args: argparse.Namespace) -> int:
    """Run one (or all) DLT pipeline(s).

    Args:
        args: The parsed argparse namespace.

    Returns:
        Exit code (``0`` = success, non-zero on failure).
    """
    try:
        if args.name == "all":
            from dlt_pipelines.official_doc_fetcher import run as run_official
            from dlt_pipelines.safeguarding_fetcher import run as run_safeguarding
            from dlt_pipelines.pdf_page_metadata import run as run_pdf_meta

            run_official()
            run_safeguarding()
            run_pdf_meta()
            return 0
        if args.name == "official_doc_fetcher":
            from dlt_pipelines.official_doc_fetcher import run
        elif args.name == "safeguarding_fetcher":
            from dlt_pipelines.safeguarding_fetcher import run
        elif args.name == "pdf_page_metadata":
            from dlt_pipelines.pdf_page_metadata import run
        else:
            print(f"Unknown pipeline: {args.name}", file=sys.stderr)
            return 1
        run()
        return 0
    except ImportError as exc:
        print(
            f"Pipeline runner not importable (missing optional dependency?): {exc}",
            file=sys.stderr,
        )
        return 2
    except Exception as exc:  # noqa: BLE001 — CLI top-level catch
        print(f"Pipeline failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


def _cmd_baml(args: argparse.Namespace) -> int:
    """Run ``baml-cli`` against the ``baml_extracts/`` package.

    Args:
        args: The parsed argparse namespace.

    Returns:
        Exit code (the exit code from the baml-cli subprocess).
    """
    action = args.baml_action
    if action is None:
        print(
            "baml: missing subcommand. Use `gemini-hackathon baml {generate|test|check}`.",
            file=sys.stderr,
        )
        return 2

    cmd: list[str] = ["baml-cli", action]
    if action == "generate":
        # `baml-cli generate` reads baml_config.yaml from the project root.
        project_root = Path(__file__).resolve().parent.parent
        if not (project_root / "baml_config.yaml").exists():
            print(
                f"baml_config.yaml not found at {project_root / 'baml_config.yaml'}; "
                "run from the project root or set BAML_CONFIG.",
                file=sys.stderr,
            )
            return 1

    try:
        result = subprocess.run(  # noqa: S603 — subprocess invocation is intentional
            cmd,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        print(
            "baml-cli not found on PATH; install with `uv add baml-py`.",
            file=sys.stderr,
        )
        return 127
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


def _cmd_serve(args: argparse.Namespace) -> int:
    """Start the Python backend HTTP server on the given port.

    Per the spec the production server is Hono + oRPC (Node.js /
    Bun); in this Python CLI we ship a minimal :class:`http.server`
    stand-in that serves the canonical endpoints:

    * ``GET /api/health``     → ``{"status": "ok"}``
    * ``GET /api/themes``     → ``list_all_palettes()``
    * ``GET /api/themes/<k>`` → :func:`load_palette` result

    Args:
        args: The parsed argparse namespace.

    Returns:
        Exit code (``0`` = clean shutdown).
    """
    host = args.host
    port = args.port

    class _Handler(http.server.BaseHTTPRequestHandler):
        """The canonical request handler for the Python backend."""

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            """Silence the default access-log noise; route through :mod:`logging`."""
            logger.info("serve: " + format, *args)

        def do_GET(self) -> None:  # noqa: N802 — http.server convention
            """Handle GET requests (the canonical 3 endpoints)."""
            if self.path == "/api/health":
                self._json_response({"status": "ok", "service": "gemini_hackathon"})
                return
            if self.path == "/api/themes":
                self._json_response(list_all_palettes())
                return
            if self.path.startswith("/api/themes/"):
                source_key = self.path[len("/api/themes/"):]
                palette = load_palette(source_key)
                if palette is None:
                    self._json_response({"error": "not found"}, status=404)
                    return
                self._json_response({
                    "source_key": palette.source_key,
                    "source_name": palette.source_name,
                    "jurisdiction": palette.jurisdiction,
                    "level": palette.level,
                    "css_variables": palette.css_variables,
                })
                return
            self._json_response({"error": "not found"}, status=404)

        def _json_response(self, payload: Any, status: int = 200) -> None:
            """Send a JSON response with the given status code."""
            body = json.dumps(payload, default=str).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    print(f"Serving on http://{host}:{port} (Ctrl-C to stop)")
    try:
        with socketserver.ThreadingTCPServer((host, port), _Handler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
    return 0


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


def _dispatch(args: argparse.Namespace) -> int:
    """Dispatch the parsed args to the right subcommand handler.

    Args:
        args: The parsed argparse namespace.

    Returns:
        The exit code from the dispatched handler.
    """
    if args.command is None:
        # No subcommand → show the help banner.
        print(
            "gemini-hackathon: missing COMMAND. "
            "Run `gemini-hackathon --help` for the full subcommand list.",
            file=sys.stderr,
        )
        return 2

    if args.command == "theme":
        if args.theme_action in (None, "list"):
            return _cmd_theme_list(args)
        if args.theme_action == "show":
            return _cmd_theme_show(args)
        if args.theme_action == "validate":
            return _cmd_theme_validate(args)

    if args.command == "extract":
        return _cmd_extract(args)

    if args.command == "pipeline":
        if args.pipeline_action in (None, "list"):
            return _cmd_pipeline_list(args)
        if args.pipeline_action == "run":
            return _cmd_pipeline_run(args)

    if args.command == "baml":
        return _cmd_baml(args)

    if args.command == "serve":
        return _cmd_serve(args)

    print(f"Unknown command: {args.command}", file=sys.stderr)
    return 2


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI.

    Args:
        argv: Optional argv override (default: ``sys.argv[1:]``).

    Returns:
        The process exit code.
    """
    parser = _build_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    if not args.quiet:
        _print_model_policy_banner()

    return _dispatch(args)


def _exit_with(message: str, code: int = 1) -> NoReturn:
    """Print ``message`` to stderr and exit with the given code.

    Args:
        message: The error message.
        code: The exit code.
    """
    print(message, file=sys.stderr)
    sys.exit(code)


__all__ = [
    "MODEL_POLICY_BANNER",
    "_print_model_policy_banner",
    "main",
]


if __name__ == "__main__":
    sys.exit(main())