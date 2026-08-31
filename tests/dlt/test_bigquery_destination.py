"""tests.dlt.test_bigquery_destination — verify the Phase 2 BigQuery destination factory.

Tests the polymorphic `get_destination()` factory at
`dlt_pipelines/_shared.py:364-455` against a mocked
`dlt.destinations.bigquery` call.

Per Phase 2 of the polish plan (`openspec/changes/2026-08-31-gcp-data-plane-v1`):
- The factory selects the BigQuery backend when `name="bigquery"`.
- The dataset name comes from the `bigquery_dataset` kwarg, then
  the `BIGQUERY_DATASET` env var, then the default `"biep"`.
- The legacy `get_duckdb_destination()` wrapper remains importable.

All tests are fully mocked — no live BigQuery calls.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


def test_get_destination_bigquery_calls_factory_with_kwarg(monkeypatch: pytest.MonkeyPatch) -> None:
    """`get_destination("bigquery", bigquery_dataset="test_biep")` passes kwargs through.

    Mocks `dlt.destinations.bigquery` and asserts the factory was
    called with `dataset_name="test_biep"`. Verifies the Phase 2
    BigQuery wire path returns the mocked factory product (the
    actual dlt destination instance).
    """
    # Reload the module so any cached module-level state from a
    # previous import doesn't leak.
    if "dlt_pipelines._shared" in sys.modules:
        importlib.reload(sys.modules["dlt_pipelines._shared"])
    mod = importlib.import_module("dlt_pipelines._shared")

    sentinel = object()
    with patch("dlt.destinations.bigquery", return_value=sentinel, create=True) as mock_factory:
        # The lazy import in get_destination() reads `from dlt.destinations import bigquery`.
        # `create=True` lets patch() inject a symbol that doesn't exist
        # in the test environment (when `dlt` isn't installed).
        result = mod.get_destination("bigquery", bigquery_dataset="test_biep")

    assert result is sentinel, "get_destination should return the mocked factory product"
    mock_factory.assert_called_once_with(dataset_name="test_biep")


def test_get_destination_bigquery_defaults_dataset_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When `bigquery_dataset=None` and `BIGQUERY_DATASET=test_env`, uses the env var."""
    if "dlt_pipelines._shared" in sys.modules:
        importlib.reload(sys.modules["dlt_pipelines._shared"])
    mod = importlib.import_module("dlt_pipelines._shared")

    monkeypatch.setenv("BIGQUERY_DATASET", "test_env")

    sentinel = object()
    with patch("dlt.destinations.bigquery", return_value=sentinel, create=True) as mock_factory:
        result = mod.get_destination("bigquery")

    assert result is sentinel
    mock_factory.assert_called_once_with(dataset_name="test_env")


def test_get_destination_bigquery_falls_back_to_biep_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When neither kwarg nor env var is set, falls back to `BIGQUERY_DEFAULT_DATASET` (default `"biep"`)."""
    if "dlt_pipelines._shared" in sys.modules:
        importlib.reload(sys.modules["dlt_pipelines._shared"])
    mod = importlib.import_module("dlt_pipelines._shared")

    monkeypatch.delenv("BIGQUERY_DATASET", raising=False)

    sentinel = object()
    with patch("dlt.destinations.bigquery", return_value=sentinel, create=True) as mock_factory:
        result = mod.get_destination("bigquery")

    assert result is sentinel
    mock_factory.assert_called_once_with(dataset_name="biep")


def test_get_destination_rejects_unknown_name() -> None:
    """`get_destination("bogus")` raises `ValueError`."""
    if "dlt_pipelines._shared" in sys.modules:
        importlib.reload(sys.modules["dlt_pipelines._shared"])
    mod = importlib.import_module("dlt_pipelines._shared")

    with pytest.raises(ValueError, match="unknown name"):
        mod.get_destination("bogus")


def test_get_destination_duckdb_returns_local_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`get_destination("duckdb")` returns the canonical DUCKDB_PATH destination.

    Verifies the duckdb branch creates the parent dir + uses the
    env-override path. Skipped if `dlt.destinations.duckdb` import fails.
    """
    if "dlt_pipelines._shared" in sys.modules:
        importlib.reload(sys.modules["dlt_pipelines._shared"])
    mod = importlib.import_module("dlt_pipelines._shared")

    target = tmp_path / "subdir" / "smoke.duckdb"
    monkeypatch.setenv("DUCKDB_PATH", str(target))

    # The duckdb factory is the runtime import target.
    sentinel = object()
    try:
        from dlt.destinations import duckdb as _duckdb
    except ImportError:
        pytest.skip("dlt is not installed; skipping the duckdb branch test")

    with (
        patch.object(mod, "_duckdb", _duckdb, create=True)
        if False
        else patch("dlt.destinations.duckdb", return_value=sentinel, create=True) as mock_factory
    ):
        result = mod.get_destination("duckdb")

    assert result is sentinel
    mock_factory.assert_called_once_with(credentials=str(target))
    assert target.parent.exists(), "parent dir should be created"


def test_get_duckdb_destination_legacy_wrapper_still_works(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Phase 0/1 `get_duckdb_destination()` wrapper still calls into `get_destination("duckdb")`."""
    if "dlt_pipelines._shared" in sys.modules:
        importlib.reload(sys.modules["dlt_pipelines._shared"])
    mod = importlib.import_module("dlt_pipelines._shared")

    target = tmp_path / "legacy.duckdb"

    sentinel = object()
    try:
        with patch("dlt.destinations.duckdb", return_value=sentinel, create=True) as mock_factory:
            result = mod.get_duckdb_destination(target)
    except ImportError:
        pytest.skip("dlt is not installed; skipping the legacy wrapper test")

    assert result is sentinel
    mock_factory.assert_called_once_with(credentials=str(target))
