"""tests.cocoindex.test_vertex_target — verify the Phase 2 Vertex AI Vector Search target.

Tests `VertexVectorSearchTarget` from
`cocoindex_flows/_shared/_vector_target.py:221-401` against mocked
`google.cloud.aiplatform.MatchingEngineIndex` and
`MatchingEngineIndexEndpoint` calls.

Per Phase 2 of the polish plan (`openspec/changes/2026-08-31-gcp-data-plane-v1`):
- `upsert(key, vector, metadata)` writes ONE datapoint via the
  per-row shim that wraps `upsert_batch`.
- `find_nearest_sync(query_vector, k, distance_strategy)` queries
  the deployed index endpoint without a table_name restrict.
- `delete(key)` removes one datapoint by ID.
- All 4 methods (the 3 sync shims + `upsert_batch`) gracefully
  degrade to no-op in stub mode (no `google-cloud-aiplatform`).

All tests are fully mocked — no live Vertex AI calls.
"""

from __future__ import annotations

import importlib
import sys
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


def _reload_vector_target_module() -> Any:
    """Reload `cocoindex_flows._shared._vector_target` to drop cached state."""
    if "cocoindex_flows._shared._vector_target" in sys.modules:
        importlib.reload(sys.modules["cocoindex_flows._shared._vector_target"])
    return importlib.import_module("cocoindex_flows._shared._vector_target")


def test_vertex_target_init_with_full_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Constructor wires up aiplatform.init + MatchingEngineIndex + IndexEndpoint."""
    monkeypatch.setenv("GCP_PROJECT_ID", "agentic-hackathon-august-26")
    monkeypatch.setenv("VERTEX_VECTOR_SEARCH_REGION", "europe-west1")
    monkeypatch.setenv("VERTEX_VECTOR_SEARCH_INDEX_ID", "projects/p/locations/l/indexes/123")
    monkeypatch.setenv("VERTEX_VECTOR_SEARCH_INDEX_ENDPOINT_ID", "projects/p/locations/l/indexEndpoints/456")
    monkeypatch.setenv("VERTEX_VECTOR_SEARCH_DEPLOYED_INDEX_ID", "deployed_abc")
    monkeypatch.setenv("VERTEX_VECTOR_SEARCH_DIMENSIONS", "1536")

    mod = _reload_vector_target_module()

    fake_index = MagicMock(name="MatchingEngineIndex")
    fake_endpoint = MagicMock(name="MatchingEngineIndexEndpoint")
    fake_aiplatform = MagicMock()
    fake_aiplatform.MatchingEngineIndex.return_value = fake_index
    fake_aiplatform.MatchingEngineIndexEndpoint.return_value = fake_endpoint

    # The source module imports `aiplatform` at the top of the try block;
    # we patch the module's `aiplatform` attribute directly rather than
    # trying to swap sys.modules (which doesn't affect already-loaded
    # modules' attribute lookup).
    monkeypatch.setattr(mod, "VERTEX_VECTOR_SEARCH_AVAILABLE", True)
    monkeypatch.setattr(mod, "aiplatform", fake_aiplatform)
    target = mod.VertexVectorSearchTarget()

    assert target.available is True
    assert target.is_stub is False
    fake_aiplatform.init.assert_called_once_with(
        project="agentic-hackathon-august-26", location="europe-west1"
    )
    fake_aiplatform.MatchingEngineIndex.assert_called_once_with(
        "projects/p/locations/l/indexes/123"
    )
    fake_aiplatform.MatchingEngineIndexEndpoint.assert_called_once_with(
        "projects/p/locations/l/indexEndpoints/456"
    )
    # Display-name defaults
    assert target._index_display_name == "gemini-hackathon-index"
    assert target._endpoint_display_name == "gemini-hackathon-endpoint"
    assert target._dimensions == 1536


def test_vertex_target_init_stub_mode_when_aiplatform_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When `google.cloud.aiplatform` isn't installed, the target is in stub mode."""
    monkeypatch.setenv("GCP_PROJECT_ID", "p")
    monkeypatch.setenv("VERTEX_VECTOR_SEARCH_INDEX_ID", "idx")
    monkeypatch.setenv("VERTEX_VECTOR_SEARCH_INDEX_ENDPOINT_ID", "iep")
    monkeypatch.setenv("VERTEX_VECTOR_SEARCH_DEPLOYED_INDEX_ID", "dep")

    mod = _reload_vector_target_module()

    # Simulate "aiplatform not installed" — set the availability flag
    # to False (the real try/except in the module sets this when the
    # import fails; we replicate it here so the test doesn't depend
    # on what's actually installed in this environment).
    with patch.dict(sys.modules, {"google.cloud.aiplatform": None}):
        monkeypatch.setattr(mod, "VERTEX_VECTOR_SEARCH_AVAILABLE", False)
        target = mod.VertexVectorSearchTarget()

    assert target.available is False
    assert target.is_stub is True


def test_vertex_target_upsert_sync_writes_one_datapoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`upsert(key, vector, metadata)` builds a VectorRow + calls upsert_batch."""
    monkeypatch.setenv("GCP_PROJECT_ID", "p")
    monkeypatch.setenv("VERTEX_VECTOR_SEARCH_INDEX_ID", "idx")
    monkeypatch.setenv("VERTEX_VECTOR_SEARCH_INDEX_ENDPOINT_ID", "iep")
    monkeypatch.setenv("VERTEX_VECTOR_SEARCH_DEPLOYED_INDEX_ID", "dep")

    mod = _reload_vector_target_module()

    fake_index = MagicMock(name="MatchingEngineIndex")
    fake_endpoint = MagicMock(name="MatchingEngineIndexEndpoint")
    fake_aiplatform = MagicMock()
    fake_aiplatform.MatchingEngineIndex.return_value = fake_index
    fake_aiplatform.MatchingEngineIndexEndpoint.return_value = fake_endpoint

    monkeypatch.setattr(mod, "VERTEX_VECTOR_SEARCH_AVAILABLE", True)
    monkeypatch.setattr(mod, "aiplatform", fake_aiplatform)
    target = mod.VertexVectorSearchTarget()

    # Patch upsert_batch so the async shim doesn't try to use the real
    # event loop (the underlying MatchingEngineIndex is a MagicMock, so
    # it would silently succeed but we want a deterministic assertion).
    async def _fake_upsert_batch(rows):  # noqa: ANN001 — async shim
        return len(rows)

    monkeypatch.setattr(target, "upsert_batch", _fake_upsert_batch)
    count = target.upsert("k1", [0.1] * 768, {"source_table": "lc_math"})

    assert count == 1


def test_vertex_target_find_nearest_sync_calls_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`find_nearest_sync` calls `MatchingEngineIndexEndpoint.find_neighbors`."""
    monkeypatch.setenv("GCP_PROJECT_ID", "p")
    monkeypatch.setenv("VERTEX_VECTOR_SEARCH_INDEX_ID", "idx")
    monkeypatch.setenv("VERTEX_VECTOR_SEARCH_INDEX_ENDPOINT_ID", "iep")
    monkeypatch.setenv("VERTEX_VECTOR_SEARCH_DEPLOYED_INDEX_ID", "dep")

    mod = _reload_vector_target_module()

    fake_index = MagicMock(name="MatchingEngineIndex")
    fake_endpoint = MagicMock(name="MatchingEngineIndexEndpoint")
    neighbor = MagicMock()
    neighbor.id = "lc_math::k1"
    neighbor.distance = 0.1
    fake_endpoint.find_neighbors.return_value = [[neighbor]]

    fake_aiplatform = MagicMock()
    fake_aiplatform.MatchingEngineIndex.return_value = fake_index
    fake_aiplatform.MatchingEngineIndexEndpoint.return_value = fake_endpoint

    monkeypatch.setattr(mod, "VERTEX_VECTOR_SEARCH_AVAILABLE", True)
    monkeypatch.setattr(mod, "aiplatform", fake_aiplatform)
    # The runtime imports the Namespace class from the deep
    # `google.cloud.aiplatform.matching_engine.matching_engine_index_endpoint`
    # sub-module. Mock the import at runtime via sys.modules so the
    # lazy import succeeds in the test environment (the SDK isn't
    # installed without `--group gcp`).
    fake_namespace_module = MagicMock(name="Namespace")
    monkeypatch.setitem(
        sys.modules,
        "google.cloud.aiplatform.matching_engine.matching_engine_index_endpoint",
        fake_namespace_module,
    )
    target = mod.VertexVectorSearchTarget()
    results = target.find_nearest_sync([0.1] * 768, k=5, distance_strategy="COSINE")

    assert len(results) == 1
    assert results[0]["id"] == "k1"
    assert results[0]["distance"] == 0.1
    assert results[0]["score"] == 0.9
    fake_endpoint.find_neighbors.assert_called_once()


def test_vertex_target_delete_calls_remove_datapoints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`delete(key)` calls `MatchingEngineIndex.remove_datapoints`."""
    monkeypatch.setenv("GCP_PROJECT_ID", "p")
    monkeypatch.setenv("VERTEX_VECTOR_SEARCH_INDEX_ID", "idx")
    monkeypatch.setenv("VERTEX_VECTOR_SEARCH_INDEX_ENDPOINT_ID", "iep")
    monkeypatch.setenv("VERTEX_VECTOR_SEARCH_DEPLOYED_INDEX_ID", "dep")

    mod = _reload_vector_target_module()

    fake_index = MagicMock(name="MatchingEngineIndex")
    fake_endpoint = MagicMock(name="MatchingEngineIndexEndpoint")
    fake_aiplatform = MagicMock()
    fake_aiplatform.MatchingEngineIndex.return_value = fake_index
    fake_aiplatform.MatchingEngineIndexEndpoint.return_value = fake_endpoint

    monkeypatch.setattr(mod, "VERTEX_VECTOR_SEARCH_AVAILABLE", True)
    monkeypatch.setattr(mod, "aiplatform", fake_aiplatform)
    target = mod.VertexVectorSearchTarget()
    target.delete("lc_math::k1")

    fake_index.remove_datapoints.assert_called_once_with(datapoints=["lc_math::k1"])


def test_vertex_target_stub_mode_methods_return_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When in stub mode, all 3 sync shims + the async batch methods return empty."""
    monkeypatch.setenv("GCP_PROJECT_ID", "p")
    monkeypatch.setenv("VERTEX_VECTOR_SEARCH_INDEX_ID", "idx")
    monkeypatch.setenv("VERTEX_VECTOR_SEARCH_INDEX_ENDPOINT_ID", "iep")
    monkeypatch.setenv("VERTEX_VECTOR_SEARCH_DEPLOYED_INDEX_ID", "dep")

    mod = _reload_vector_target_module()

    with patch.dict(sys.modules, {"google.cloud.aiplatform": None}):
        monkeypatch.setattr(mod, "VERTEX_VECTOR_SEARCH_AVAILABLE", False)
        target = mod.VertexVectorSearchTarget()

    assert target.upsert("k1", [0.1] * 768) == 0
    assert target.find_nearest_sync([0.1] * 768, k=5) == []
    target.delete("k1")  # no-op, no exception


def test_vertex_target_env_var_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When env vars are unset, the constructor falls back to canonical defaults."""
    monkeypatch.delenv("VERTEX_VECTOR_SEARCH_REGION", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_LOCATION", raising=False)
    monkeypatch.delenv("VERTEX_VECTOR_SEARCH_INDEX", raising=False)
    monkeypatch.delenv("VERTEX_VECTOR_SEARCH_ENDPOINT", raising=False)
    monkeypatch.delenv("VERTEX_VECTOR_SEARCH_DIMENSIONS", raising=False)

    mod = _reload_vector_target_module()

    # Stub mode (no aiplatform) — we're only checking the env-var
    # fallback values, not the live API call.
    with patch.dict(sys.modules, {"google.cloud.aiplatform": None}):
        monkeypatch.setattr(mod, "VERTEX_VECTOR_SEARCH_AVAILABLE", False)
        target = mod.VertexVectorSearchTarget()

    assert target._location == "europe-west1"
    assert target._index_display_name == "gemini-hackathon-index"
    assert target._endpoint_display_name == "gemini-hackathon-endpoint"
    assert target._dimensions == 768
