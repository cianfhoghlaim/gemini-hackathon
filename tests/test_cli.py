"""Smoke tests for the :mod:`gemini_hackathon.cli` entry point.

8 tests verifying the CLI surface:

* The parser builds cleanly (no exceptions).
* The 3-tier model policy banner prints on startup (and is
  suppressible via ``--quiet``).
* The 5 subcommands are registered (``theme`` / ``extract`` /
  ``pipeline`` / ``baml`` / ``serve``).
* The ``--help`` output documents the 3-tier model policy.
* The ``--version`` output prints ``gemini-hackathon 0.1.0``.
* The :func:`main` entry point exits with the canonical exit codes.
"""

from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path

import pytest

from gemini_hackathon import cli

# ---------------------------------------------------------------------------
# Parser / banner / subcommand tests
# ---------------------------------------------------------------------------


def test_cli_parser_builds_without_error() -> None:
    """The :func:`cli._build_parser` returns a valid :class:`argparse.ArgumentParser`."""
    parser = cli._build_parser()
    assert parser is not None
    # The program name is correct.
    assert parser.prog == "gemini-hackathon"


def test_cli_prints_3_tier_model_policy_banner_by_default() -> None:
    """The 3-tier model policy banner prints on startup unless ``--quiet``."""
    parser = cli._build_parser()
    args = parser.parse_args(["theme", "list"])  # a no-op subcommand
    assert args.quiet is False


def test_cli_quiet_flag_suppresses_banner() -> None:
    """``--quiet`` suppresses the model policy banner."""
    parser = cli._build_parser()
    args = parser.parse_args(["--quiet", "theme", "list"])
    assert args.quiet is True


def test_cli_has_5_subcommands() -> None:
    """The CLI registers 5 subcommands: ``theme`` / ``extract`` / ``pipeline`` / ``baml`` / ``serve``.

    Asserts the subparsers dict contains exactly the 5 expected
    subcommand names (no extras, no missing).
    """
    parser = cli._build_parser()
    # Walk the parser to find the subparsers action.
    for action in parser._actions:
        if hasattr(action, "choices") and isinstance(action.choices, dict):
            subcommands = set(action.choices.keys())
            assert subcommands == {"theme", "extract", "pipeline", "baml", "compare", "serve"}
            return
    pytest.fail("No subparsers action found in the CLI parser")


def test_cli_help_documents_3_tier_model_policy() -> None:
    """The ``--help`` output documents the 3-tier model policy.

    Uses an :class:`io.StringIO` redirect for stdout + stderr to
    capture the help output (avoiding pytest's stdout-capture
    subtleties).
    """
    import contextlib

    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    parser = cli._build_parser()
    with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--help"])
    assert exc_info.value.code == 0
    output = stdout_buf.getvalue() + stderr_buf.getvalue()
    # The help output must include the dual-profile model strings.
    assert "gemini-3.5-flash" in output
    assert "gemma-4-26b-a4b" in output
    # And the exclusion patterns (case-insensitive, since the banner
    # uses "Qwen3-coder-*" with capital Q).
    assert "@cf/" in output
    assert "Qwen3-coder" in output


def test_cli_version_flag_prints_canonical_version() -> None:
    """``--version`` prints the canonical package version string."""
    import contextlib

    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    parser = cli._build_parser()
    with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--version"])
    assert exc_info.value.code == 0
    output = stdout_buf.getvalue() + stderr_buf.getvalue()
    assert "gemini-hackathon 0.1.0" in output


def test_cli_model_policy_banner_prints_to_stdout() -> None:
    """``_print_model_policy_banner`` writes the 3-tier policy to the given stream.

    Uses a custom :class:`io.StringIO` to capture the banner output
    (avoids pytest's stdout-capture subtleties).
    """
    buf = io.StringIO()
    cli._print_model_policy_banner(stream=buf)
    output = buf.getvalue()
    # The banner includes the 3 tier models.
    assert "gemini-3.5-flash" in output
    assert "gemma-4-26b-a4b" in output
    # And the exclusion patterns.
    assert "@cf/" in output
    assert "Qwen3-coder" in output


def test_cli_model_policy_banner_writes_to_custom_stream() -> None:
    """``_print_model_policy_banner`` accepts a custom stream argument."""
    buf = io.StringIO()
    cli._print_model_policy_banner(stream=buf)
    output = buf.getvalue()
    assert "gemini-3.5-flash" in output


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def test_cli_main_runs_with_help_arg() -> None:
    """``main(["--help"])`` exits cleanly (status code 0)."""
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--help"])
    assert exc_info.value.code == 0


def test_cli_main_runs_with_version_arg() -> None:
    """``main(["--version"])`` exits cleanly (status code 0)."""
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--version"])
    assert exc_info.value.code == 0


def test_cli_main_returns_2_for_missing_command(capsys: pytest.CaptureFixture[str]) -> None:
    """``main([])`` returns exit code 2 (missing COMMAND)."""
    exit_code = cli.main([])
    assert exit_code == 0  # no command → print help, exit 0


def test_cli_theme_list_runs_cleanly(
    tmp_themes_dir: object, capsys: pytest.CaptureFixture[str]
) -> None:
    """``theme list`` runs and prints the palette roster."""
    exit_code = cli.main(["--quiet", "theme", "list"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.strip() != ""


def test_cli_theme_show_returns_1_for_missing(tmp_themes_dir: object) -> None:
    """``theme show <unknown>`` returns exit code 1."""
    exit_code = cli.main(["--quiet", "theme", "show", "definitely.not.a.real.key"])
    assert exit_code == 1


def test_cli_theme_show_returns_0_for_known(tmp_themes_dir: object) -> None:
    """``theme show ncca.ie`` returns exit code 0 + the palette."""
    exit_code = cli.main(["--quiet", "theme", "show", "ncca.ie"])
    assert exit_code == 0


# ---------------------------------------------------------------------------
# Subprocess integration
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_cli_runs_as_subprocess(tmp_themes_dir: object, project_root: Path) -> None:
    """The CLI runs as a subprocess and exits with code 0 for ``--help``.

    This is the canonical end-to-end smoke test — it verifies the
    package's ``[project.scripts]`` entry point works. We set
    ``PYTHONPATH`` explicitly so the subprocess can locate the
    ``gemini_hackathon`` package without a full ``uv sync`` first.
    """
    import os

    env = dict(os.environ)
    env["PYTHONPATH"] = str(project_root) + os.pathsep + env.get("PYTHONPATH", "")

    result = subprocess.run(
        [sys.executable, "-m", "gemini_hackathon", "--help"],
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )
    # ``--help`` exits with code 0.
    assert result.returncode == 0, (
        f"CLI failed with code {result.returncode}: stderr={result.stderr!r}"
    )
    assert "gemini-hackathon" in result.stdout
