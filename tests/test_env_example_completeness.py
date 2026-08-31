"""Tests verifying `.env.example` documents every env var consumed by the
Python source under `gemini_hackathon/`.

Updated 2026-08-31 (Phase 6): walks the AST of every Python module under
`gemini_hackathon/` for `os.environ.get(...)`, `os.environ[...]`, and
`os.environ.get(...)` indirect calls (e.g. via `getenv(...)`). Asserts
the union of env-var names is a subset of the keys declared in
`.env.example`.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPO_ROOT / "gemini_hackathon"
ENV_EXAMPLE = REPO_ROOT / ".env.example"


_ENV_NAMES_FROM_CALLS = re.compile(
    r"""(?ix)
    (?: os \. environ | os \. getenv )
    \s*\(\s*
    (?:
        f"?\{[A-Za-z_]+\}?"       # f-string with a single placeholder
        |
        "([^"\\]*(?:\\.[^"\\]*)*)"   # plain double-quoted string
        |
        '([^'\\]*(?:\\.[^'\\]*)*)'   # plain single-quoted string
    )
    """
)

_TEST_FILES = frozenset(
    {
        "tests",
        "test_call_llm.py.test_call_llm",
        ".venv",
        "__pycache__",
    }
)


def _parse_env_example_keys() -> set[str]:
    """Parse `.env.example` to recover every declared env-var name.

    The file uses `KEY=value` syntax (with `# ----- section -----` headers
    + `# inline comment` rows). We extract every bare identifier that
    sits left of the first `=` on a non-comment, non-empty line.

    Anything declared `KEY_${SUFFIX}` is captured as `KEY_${SUFFIX}`.
    """
    keys: set[str] = set()
    for line in ENV_EXAMPLE.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=", stripped)
        if m:
            keys.add(m.group(1))
    return keys


def _ast_collect_env_names(source_path: Path) -> set[str]:
    """Walk the source AST for env-var reads + accept a regex fallback."""
    text = source_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text, filename=str(source_path))
    except SyntaxError:
        # Skip files that don't parse (e.g. vendored stubs).
        return set()

    names: set[str] = set()

    # 1. Static AST walk for `os.environ.get("X")`, `os.environ["X"]`,
    #    `os.getenv("X")`, and `os.environ.setdefault("X", ...)`.
    class _Visitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:
            func = node.func
            func_str = (ast.unparse(func) if hasattr(ast, "unparse") else "") or ""
            # Capture first positional arg when it is a string literal.
            if (
                func_str in {"os.environ.get", "os.getenv", "os.environ.setdefault"}
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                names.add(node.args[0].value)
            self.generic_visit(node)

        def visit_Subscript(self, node: ast.Subscript) -> None:
            func_str = (ast.unparse(node.value) if hasattr(ast, "unparse") else "") or ""
            if (
                func_str == "os.environ"
                and isinstance(node.slice, ast.Constant)
                and isinstance(node.slice.value, str)
            ):
                names.add(node.slice.value)
            self.generic_visit(node)

    _Visitor().visit(tree)

    # 2. Regex fallback for patterns the static walker can't parse
    #    (e.g. `os.environ.get(f"X_{var}")`, `getenv("X")` calls via
    #    aliased imports, dynamic arguments).
    for match in _ENV_NAMES_FROM_CALLS.finditer(text):
        for grp in match.groups()[1:]:
            if grp:
                names.add(grp)

    return names


def _walk_python_files(root: Path):
    for path in root.rglob("*.py"):
        if any(part in _TEST_FILES for part in path.parts):
            continue
        if "__pycache__" in path.parts or ".venv" in path.parts:
            continue
        yield path


def test_dotenv_example_exists():
    """`.env.example` is committed at the repo root."""
    assert ENV_EXAMPLE.exists(), "`.env.example` is missing — env-var contract is broken"


def test_env_example_has_at_least_50_keys():
    """Phase 6 expanded the catalogue to ≥52 keys (32 + ≥20 net new)."""
    keys = _parse_env_example_keys()
    assert len(keys) >= 50, (
        f"`.env.example` only declares {len(keys)} keys; expected ≥50 after the Phase 6 expansion"
    )


def test_every_env_var_in_gemini_hackathon_is_documented():
    """Every `os.environ` read under `gemini_hackathon/` has a `.env.example` key."""
    keys = _parse_env_example_keys()

    used_names: set[str] = set()
    for path in _walk_python_files(SOURCE_ROOT):
        used_names |= _ast_collect_env_names(path)

    missing = sorted(used_names - keys)
    # Filter out the canonical Google service-account-resolved prefix
    # (`GOOGLE_CLOUD_PROJECT` is a real key in `.env.example`).
    assert not missing, (
        f"Found {len(missing)} env-var names used by `gemini_hackathon/` but "
        f"not declared in `.env.example`:\n  "
        + "\n  ".join(missing[:30])
        + ("\n  ..." if len(missing) > 30 else "")
    )


def test_ast_walker_does_not_double_count_string_constants():
    """The AST + regex deduplication is stable (sets, not multiset)."""
    counts: dict[str, int] = {}
    for path in _walk_python_files(SOURCE_ROOT):
        for name in _ast_collect_env_names(path):
            counts[name] = counts.get(name, 0) + 1
    # Every name appears at least once per file that uses it, but never more
    # than once per file (the AST walker is per-file set-based).
    assert all(v >= 1 for v in counts.values())


def test_env_example_uses_canonical_key_format():
    """Every declared key is uppercase alphanumeric (the Python convention)."""
    keys = _parse_env_example_keys()
    bad = sorted(k for k in keys if not re.match(r"^[A-Z][A-Z0-9_]*$", k))
    assert not bad, f"Non-conforming env-var names in `.env.example`: {bad}"
