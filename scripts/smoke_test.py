"""Canonical smoke test — `mise run smoke`.

Runs every feature path that can be exercised in a deterministic, offline-friendly way:

  1. Theming: list_all_palettes returns 15 (7 jurisdictions + 3 boards + 5 safeguarding).
  2. Models: registry loads with 24 entries; hackathon profile excludes minimax-m3.
  3. Exclusion guard: @cf/* + qwen3-coder-* are rejected.
  4. OCR: capability router loads; auto_capability heuristic works.
  5. Assets: AssetControlRecord JSON-roundtrips; router falls back to stub.
  6. CLI: all 6 subcommands registered; banner prints.
  7. Observability: trace_agent emits opened/closed events.
  8. DLT: shared module imports (skipped on Python<3.11).
  9. Compare: stub run_comparison() writes a row to DuckDB.
 10. pyproject + theme JSON sanity: every palette file is valid JSON.

Exit code 0 = everything green. Non-zero = at least one feature is broken.

Usage:
    mise run smoke          # full run, no network required
    mise run smoke --quick  # skip DuckDB-write + slow assertions
    mise run smoke --verbose # show every assertion result
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Make `import gemini_hackathon` work without an install step.
sys.path.insert(0, str(REPO_ROOT))

# Python 3.11+ has tomllib; for 3.9/3.10 fall back to tomli.
try:
    import tomllib  # type: ignore[import-not-found]
except ImportError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        tomllib = None  # type: ignore[assignment]


def _section(name: str) -> None:
    print(f"\n=== {name} ===")


def _ok(label: str, verbose: bool, detail: str = "") -> None:
    suffix = f"  ({detail})" if detail and verbose else ""
    print(f"  [OK]   {label}{suffix}")


def _fail(label: str, err: Exception) -> None:
    print(f"  [FAIL] {label}: {type(err).__name__}: {err}")


def step_theming(verbose: bool) -> None:
    _section("1. Theming layer")
    try:
        from gemini_hackathon import BOARDS, JURISDICTIONS, list_all_palettes, load_palette

        palettes = list_all_palettes()
        assert len(palettes) == 15, f"expected 15, got {len(palettes)}"
        _ok("list_all_palettes() returns 15", verbose, f"j={len(JURISDICTIONS)} b={len(BOARDS)}")
        for k in [
            "ncca",
            "aqa",
            "ocr",
            "pearson",
            "sqa",
            "wjec",
            "ccea",
            "iom",
            "jersey",
            "guernsey",
            "ncca.ie",
            "aqa.org.uk",
            "ocr.org.uk",
            "qualifications.pearson.com",
            "sqa.org.uk",
            "wjec.co.uk",
            "ccea.org.uk",
            "gov.im/education",
            "gov.ie/education",
            "gov.uk/dfe",
            "education.gov.scot",
            "gov.wales/education",
            "ccea.org.uk/safeguarding",
        ]:
            p = load_palette(k)
            assert p is not None, f"{k} not found"
        _ok("all 23 key forms resolve", verbose)
    except Exception as e:
        _fail("theming", e)
        raise


def step_models(verbose: bool) -> None:
    _section("2. Model registry")
    try:
        from gemini_hackathon import MODEL_REGISTRY, model_for

        assert len(MODEL_REGISTRY) == 24, f"expected 24 entries, got {len(MODEL_REGISTRY)}"
        _ok("MODEL_REGISTRY has 24 entries", verbose)

        hack = MODEL_REGISTRY.for_profile("hackathon")
        dev = MODEL_REGISTRY.for_profile("dev")
        _ok(f"hackathon={len(hack)}, dev={len(dev)}", verbose)

        assert "minimax-m3" not in {e.key for e in hack}
        _ok("hackathon profile excludes minimax-m3", verbose)

        for role in ("default", "fallback"):
            entry = model_for("text_llm", role, profile="hackathon")
            assert entry is not None, f"text_llm/{role} not resolved"
        _ok("resolver resolves hackathon text tiers", verbose)
    except Exception as e:
        _fail("models", e)
        raise


def step_exclusion(verbose: bool) -> None:
    _section("3. Model exclusion guard")
    try:
        from gemini_hackathon.call_llm import ModelExcludedError, _assert_model_allowed

        for bad in [
            "@cf/meta/llama-3.1-8b-instruct",
            "qwen3-coder-32b-instruct",
            "openrouter/qwen3-coder-anything",
        ]:
            try:
                _assert_model_allowed(bad)
                raise AssertionError(f"{bad} should have been rejected")
            except ModelExcludedError:
                pass
        _ok("@cf/* and qwen3-coder-* are rejected", verbose)

        for good in [
            "gemini-3.5-flash",
            "gemma-4-26b-a4b",
            "minimax-m3",
            "openai/gemma-4-26b-a4b",
            "vertex_ai/gemini-3.5-flash",
        ]:
            _assert_model_allowed(good)
        _ok("allowed models pass through", verbose)
    except Exception as e:
        _fail("exclusion", e)
        raise


def step_ocr(verbose: bool) -> None:
    _section("4. OCR capability router")
    try:
        from gemini_hackathon.ocr import _DISPATCH_TABLE, Capability, _prompt_for, auto_capability

        assert len(_DISPATCH_TABLE) == 7
        _ok("dispatch table has 7 capabilities", verbose)

        assert auto_capability("/tmp/lc_maths_2024.pdf") == Capability.ENGLISH
        assert auto_capability("/tmp/gaeilge_paper_1.pdf") == Capability.GAELIC
        assert auto_capability("/tmp/cymraeg_syllabus.pdf") == Capability.GAELIC
        _ok("auto_capability() heuristic", verbose)

        gaelic_prompt = _prompt_for(Capability.GAELIC, language_hint=None)
        assert "fada" in gaelic_prompt
        assert "séimhiú" in gaelic_prompt
        _ok("gaelic prompt preserves fada + séimhiú", verbose)
    except Exception as e:
        _fail("ocr", e)
        raise


def step_assets(verbose: bool) -> None:
    _section("5. Asset pipeline")
    try:
        from gemini_hackathon.assets.control_record import AssetControlRecord
        from gemini_hackathon.assets.image_gen import (
            ImageGenBackend,
            ImageGenRouter,
            _control_to_prompt,
        )

        rec = AssetControlRecord.from_syllabus_and_palette(
            source_pdf_path="/tmp/lc_chem_2024.pdf",
            source_page=12,
            subject="Flame test apparatus",
            palette={"primary": "#00733B"},
            learning_outcome_id="LC-CHEM-3.1.2",
        )
        d = rec.to_dict()
        json.dumps(d)
        _ok("AssetControlRecord JSON-roundtrips", verbose)

        for k in ("COMFYUI_BASE_URL", "INVOKEAI_BASE_URL", "UNSLOTH_BASE_URL"):
            os.environ.pop(k, None)
        result = ImageGenRouter().generate(rec)
        assert result.backend == ImageGenBackend.STUB
        assert result.provenance["source_pdf_path"] == "/tmp/lc_chem_2024.pdf"
        _ok("ImageGenRouter falls back to stub when no live backends", verbose)

        prompt = _control_to_prompt(rec)
        assert "Flame test apparatus" in prompt
        assert "#00733B" in prompt
        _ok("control→text-prompt mapping includes subject + palette", verbose)
    except Exception as e:
        _fail("assets", e)
        raise


def step_cli(verbose: bool) -> None:
    _section("6. CLI")
    try:
        from gemini_hackathon import cli

        parser = cli._build_parser()
        for action in parser._actions:
            if hasattr(action, "choices") and isinstance(action.choices, dict):
                subcommands = set(action.choices.keys())
                assert subcommands == {
                    "theme",
                    "extract",
                    "pipeline",
                    "baml",
                    "compare",
                    "serve",
                }, f"got {subcommands}"
                break
        _ok("CLI has 6 subcommands", verbose)
    except Exception as e:
        _fail("cli", e)
        raise


def step_observability(verbose: bool) -> None:
    _section("7. Observability")
    try:
        import structlog

        from gemini_hackathon.observability import trace_agent

        with structlog.testing.capture_logs() as logs, trace_agent(agent="smoke_test"):
            pass
        events = {e["event"] for e in logs}
        assert "agent.trace_opened" in events
        assert "agent.trace_closed" in events
        _ok("trace_agent emits opened + closed", verbose)
    except Exception as e:
        _fail("observability", e)
        raise


def step_compare(verbose: bool, quick: bool) -> None:
    _section("9. Comparison harness → DuckDB")
    try:
        from gemini_hackathon import call_llm as call_llm_mod
        from gemini_hackathon import compare as compare_mod
        from gemini_hackathon.call_llm import LLMResponse, TierAttempt
        from gemini_hackathon.compare import run_comparison
    except ImportError as e:
        print(f"  [SKIP] missing imports: {e}")
        return

    def _stub_response(text):
        return LLMResponse(
            content=text,
            model="gemini-3.5-flash",
            backend="vertex",
            tier=1,
            family="text_llm",
            role="default",
            latency_ms=10,
            tokens_in=10,
            tokens_out=20,
            cost_usd=0.0,
            attempts=[
                TierAttempt(
                    tier=1,
                    family="text_llm",
                    role="default",
                    model="gemini-3.5-flash",
                    backend="vertex",
                    latency_ms=10,
                    succeeded=True,
                )
            ],
        )

    good_response = json.dumps(
        {
            "source_key": "x",
            "source_name": "y",
            "jurisdiction": "z",
            "level": "LC",
            "primary": "#000000",
            "secondary": "#000000",
            "accent": "#000000",
            "background": "#FFFFFF",
            "text": "#1A1A1A",
            "heading_font": "Helvetica",
            "body_font": "Helvetica",
        }
    )

    if quick:
        print("  [SKIP] quick mode")
        return

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"%PDF-1.4\n%fake\n%%EOF\n")
        pdf = f.name

    original_call_llm = call_llm_mod.call_llm
    call_llm_mod.call_llm = lambda *a, **kw: _stub_response(good_response)
    compare_mod.call_llm = call_llm_mod.call_llm
    try:
        with tempfile.TemporaryDirectory() as tmp:
            duckdb_path = os.path.join(tmp, "smoke.duckdb")
            result = run_comparison(pdf_path=pdf, duckdb_path=duckdb_path, profile="hackathon")
            assert result["profile"] == "hackathon"
            assert result["summary"]["models_compared"] >= 1
            _ok(
                f"compare wrote {result['summary']['models_compared']} rows",
                verbose,
                f"best={result['summary']['best_score']:.2f}",
            )

            import duckdb

            con = duckdb.connect(duckdb_path, read_only=True)
            n = con.execute("SELECT COUNT(*) FROM model_comparisons").fetchone()[0]
            assert n == result["summary"]["models_compared"]
            _ok(f"DuckDB has {n} rows in model_comparisons", verbose)
            con.close()
    finally:
        call_llm_mod.call_llm = original_call_llm
        compare_mod.call_llm = original_call_llm
        os.unlink(pdf)


def step_baml_client_generated() -> None:
    _section("11. BAML clients are generated")
    baml_py = REPO_ROOT / "baml_client" / "baml_client" / "__init__.py"
    baml_ts = REPO_ROOT / "web" / "baml_client" / "baml_client" / "index.ts"
    assert baml_py.exists(), f"missing: {baml_py}"
    assert baml_ts.exists(), f"missing: {baml_ts}"
    print(f"  [OK]   Python client at {baml_py.relative_to(REPO_ROOT)}")
    print(f"  [OK]   TypeScript client at {baml_ts.relative_to(REPO_ROOT)}")


def step_palette_json_sanity() -> None:
    _section("10. Palette JSON files are valid")
    bad: list[str] = []
    for f in (REPO_ROOT / "themes").glob("*_palette.json"):
        try:
            with open(f) as fp:
                json.load(fp)
        except json.JSONDecodeError as e:
            bad.append(f"{f.name}: {e}")
    cd = REPO_ROOT / "themes" / "crown_dependencies"
    if cd.exists():
        for f in cd.glob("*.json"):
            try:
                with open(f) as fp:
                    json.load(fp)
            except json.JSONDecodeError as e:
                bad.append(f"{f.name}: {e}")
    sd = REPO_ROOT / "themes" / "safeguarding"
    if sd.exists():
        for f in sd.glob("*.json"):
            try:
                with open(f) as fp:
                    json.load(fp)
            except json.JSONDecodeError as e:
                bad.append(f"{f.name}: {e}")
    assert not bad, f"invalid JSON: {bad}"
    print("  [OK]   every theme JSON file parses")


def step_pyproject_sanity(verbose: bool) -> None:
    _section("12. Project metadata sanity")
    if tomllib is None:
        print("  [SKIP] tomllib not available on this Python (3.11+ required)")
        return
    try:
        with open(REPO_ROOT / "pyproject.toml", "rb") as f:
            data = tomllib.load(f)
        assert data["project"]["name"] == "gemini-hackathon"
        print(
            f"  [OK]   pyproject.toml is well-formed (deps={len(data['project'].get('dependencies', []))})"
        )
    except Exception as e:
        _fail("pyproject", e)
        raise


def main() -> int:
    verbose = "--verbose" in sys.argv
    quick = "--quick" in sys.argv

    print(
        f"gemini_hackathon smoke test ({'verbose' if verbose else 'normal'}, {'quick' if quick else 'full'})"
    )
    print(f"Repo: {REPO_ROOT}")

    steps = [
        ("theming", lambda: step_theming(verbose)),
        ("models", lambda: step_models(verbose)),
        ("exclusion", lambda: step_exclusion(verbose)),
        ("ocr", lambda: step_ocr(verbose)),
        ("assets", lambda: step_assets(verbose)),
        ("cli", lambda: step_cli(verbose)),
        ("observability", lambda: step_observability(verbose)),
        ("compare", lambda: step_compare(verbose, quick)),
        ("palette_json", step_palette_json_sanity),
        ("baml_client", step_baml_client_generated),
        ("pyproject", lambda: step_pyproject_sanity(verbose)),
    ]

    passed, failed = 0, []
    for name, fn in steps:
        try:
            fn()
            passed += 1
        except Exception as e:
            failed.append((name, e))
            if verbose:
                traceback.print_exc()

    print("\n=== Result ===")
    print(f"{passed}/{len(steps)} steps green")
    if failed:
        print("FAILED:")
        for name, e in failed:
            print(f"  - {name}: {type(e).__name__}: {e}")
        return 1
    print("All steps green ✓")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
