"""Smoke tests for the project root files.

5 tests verifying the canonical project-routing files exist:

* :file:`AGENTS.md` — the canonical agent-routing file.
* :file:`README.md` — the project README.
* :file:`ARCHITECTURE.md` — the architecture document.
* :file:`openspec/changes/<id>/proposal.md` — the openspec change
  proposal that gates this repo.
* :file:`pyproject.toml` — the Python project metadata.

These tests catch the case where someone deletes one of the
canonical files (or the openspec change is archived without
preserving the file references).
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Project root existence
# ---------------------------------------------------------------------------


def test_agents_md_exists(project_root: Path) -> None:
    """The canonical ``AGENTS.md`` exists at the project root."""
    agents_md = project_root / "AGENTS.md"
    assert agents_md.is_file(), f"AGENTS.md not found at {agents_md}"
    text = agents_md.read_text(encoding="utf-8")
    assert "AGENTS" in text or "agent" in text.lower()
    # The file should be substantial (not a stub).
    assert len(text) > 1_000


def test_readme_exists(project_root: Path) -> None:
    """The canonical ``README.md`` exists at the project root."""
    readme = project_root / "README.md"
    assert readme.is_file(), f"README.md not found at {readme}"
    text = readme.read_text(encoding="utf-8")
    assert len(text) > 500


def test_architecture_exists(project_root: Path) -> None:
    """The canonical ``ARCHITECTURE.md`` exists at the project root."""
    arch = project_root / "ARCHITECTURE.md"
    assert arch.is_file(), f"ARCHITECTURE.md not found at {arch}"
    text = arch.read_text(encoding="utf-8")
    # The architecture doc should mention the canonical layers.
    assert "TanStack" in text or "BAML" in text or "CopilotKit" in text


def test_openspec_proposal_exists(project_root: Path) -> None:
    """The openspec change proposal exists.

    Per the openspec workflow: the canonical change is
    ``openspec/changes/2026-08-24-gemini-hackathon-public-v1/``.
    We verify:

    * The change directory exists.
    * The ``proposal.md`` file is present and non-trivial.
    * The ``tasks.md`` file is present.
    * At least one ``spec.md`` is present (under ``specs/``).
    """
    change_dir = project_root / "openspec" / "changes" / "2026-08-24-gemini-hackathon-public-v1"
    assert change_dir.is_dir(), f"openspec change dir not found: {change_dir}"

    proposal = change_dir / "proposal.md"
    assert proposal.is_file(), f"proposal.md not found at {proposal}"
    proposal_text = proposal.read_text(encoding="utf-8")
    assert len(proposal_text) > 500

    tasks = change_dir / "tasks.md"
    assert tasks.is_file(), f"tasks.md not found at {tasks}"

    specs_dir = change_dir / "specs"
    assert specs_dir.is_dir(), f"specs dir not found at {specs_dir}"
    spec_files = list(specs_dir.rglob("spec.md"))
    assert spec_files, "no spec.md files found under openspec change specs/"


def test_pyproject_toml_exists(project_root: Path) -> None:
    """The canonical ``pyproject.toml`` exists at the project root."""
    pyproject = project_root / "pyproject.toml"
    assert pyproject.is_file(), f"pyproject.toml not found at {pyproject}"
    text = pyproject.read_text(encoding="utf-8")
    # The canonical project metadata.
    assert 'name = "gemini-hackathon"' in text
    assert "[build-system]" in text
    assert "[project]" in text
    # The CLI entry point.
    assert "gemini-hackathon" in text
    assert "gemini_hackathon.cli" in text


# ---------------------------------------------------------------------------
# Project layout sanity
# ---------------------------------------------------------------------------


def test_project_layout_has_canonical_dirs(project_root: Path) -> None:
    """The canonical project sub-directories exist.

    Asserts the presence of:

    * :file:`gemini_hackathon/` — the Python package.
    * :file:`baml_extracts/` — the BAML schemas.
    * :file:`dlt_pipelines/` — the DLT ingestion layer.
    * :file:`themes/` — the theming palette directory.
    """
    for subdir in ("gemini_hackathon", "baml_extracts", "dlt_pipelines", "themes"):
        path = project_root / subdir
        assert path.is_dir(), f"missing canonical subdir: {path}"


def test_themes_dir_has_at_least_one_palette(project_root: Path) -> None:
    """The :file:`themes/` directory has at least 1 jurisdiction palette.

    Catches the case where the palette fixtures are accidentally
    removed from the repo.
    """
    themes_dir = project_root / "themes"
    palette_files = list(themes_dir.glob("*_palette.json"))
    assert palette_files, f"no *_palette.json files in {themes_dir}"


def test_gemini_hackathon_package_importable(project_root: Path) -> None:
    """The :mod:`gemini_hackathon` package is importable."""
    import gemini_hackathon

    assert gemini_hackathon.__file__ is not None
    assert Path(gemini_hackathon.__file__).is_relative_to(project_root)
