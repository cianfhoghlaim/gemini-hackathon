"""tests.cocoindex.test_dual_write_target — verify the Phase 2 DualWriteTarget composite.

Tests `DualWriteTarget` from
`cocoindex_flows/_shared/_vector_target.py:319-393` against mocked
`VectorTarget` subclasses.

Per Phase 2 of the polish plan (`openspec/changes/2026-08-31-gcp-data-plane-v1`):
- `DualWriteTarget.upsert(key, vector, metadata)` fans out to ALL
  targets (both Firestore + Vertex when wired via
  `VECTOR_TARGET_DUAL_WRITE=1`).
- `DualWriteTarget.find_nearest_sync(...)` serves reads from the
  PRIMARY target only.
- `DualWriteTarget.delete(key)` is best-effort — failures are
  silently logged (must not abort a CocoIndex ingest run).
- When every target fails on `upsert`, `DualWriteTarget` raises
  `RuntimeError("All dual-write targets failed: ...")`.

All tests are fully mocked — no live GCP calls.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from cocoindex_flows._shared._vector_target import DualWriteTarget


class _StubTarget:
    """In-memory VectorTarget stand-in for the dual-write tests."""

    def __init__(self, *, name: str = "Stub", raise_on_upsert: Exception | None = None) -> None:
        self.name = name
        self.upserts: list[tuple[str, list[float], dict[str, Any] | None]] = []
        self.deletes: list[str] = []
        self._raise_on_upsert = raise_on_upsert

    @property
    def available(self) -> bool:
        return True

    @property
    def is_stub(self) -> bool:
        return False

    def upsert(self, key: str, vector: list[float], metadata: dict[str, Any] | None = None) -> None:
        if self._raise_on_upsert is not None:
            raise self._raise_on_upsert
        self.upserts.append((key, list(vector), metadata))

    def find_nearest_sync(
        self,
        query_vector: list[float],
        k: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        return [{"id": f"{self.name}-{i}", "score": 0.9 - i * 0.01} for i in range(k)]

    async def find_nearest(
        self,
        table_name: str,
        query_vector: list[float],
        *,
        k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[Any]:
        return []

    def delete(self, key: str) -> None:
        self.deletes.append(key)


def test_dual_write_upsert_fans_out_to_both_targets() -> None:
    """`DualWriteTarget.upsert(key, vector, metadata)` calls upsert on every target."""
    primary = _StubTarget(name="Firestore")
    secondary = _StubTarget(name="Vertex")
    dual = DualWriteTarget(primary, secondary, primary=primary)

    dual.upsert("k1", [0.1] * 768, {"src": "test"})

    assert len(primary.upserts) == 1
    assert primary.upserts[0][0] == "k1"
    assert primary.upserts[0][2] == {"src": "test"}

    assert len(secondary.upserts) == 1
    assert secondary.upserts[0][0] == "k1"
    assert secondary.upserts[0][2] == {"src": "test"}


def test_dual_write_find_nearest_hits_primary_only() -> None:
    """`DualWriteTarget.find_nearest_sync` serves the read from the primary target only."""
    primary = _StubTarget(name="Firestore")
    secondary_mock = MagicMock(name="Vertex")
    # The MagicMock's `find_nearest_sync` is the spy — it must NOT be called.
    secondary_mock.find_nearest_sync = MagicMock(return_value=[{"id": "should-not-appear"}])

    dual = DualWriteTarget(primary, secondary_mock, primary=primary)
    results = dual.find_nearest_sync([0.1] * 768, k=5)

    # The primary's `find_nearest_sync` returns "Firestore-0"..."Firestore-4".
    assert len(results) == 5
    assert results[0]["id"] == "Firestore-0"

    # The secondary is never queried for reads.
    secondary_mock.find_nearest_sync.assert_not_called()


def test_dual_write_all_targets_fail_raises_runtime_error() -> None:
    """When every target fails on upsert, `DualWriteTarget` raises `RuntimeError`."""
    primary = _StubTarget(name="Firestore", raise_on_upsert=RuntimeError("Firestore down"))
    secondary = _StubTarget(name="Vertex", raise_on_upsert=RuntimeError("Vertex down"))
    dual = DualWriteTarget(primary, secondary, primary=primary)

    with pytest.raises(RuntimeError, match="All dual-write targets failed"):
        dual.upsert("k1", [0.1] * 768, {"src": "test"})

    # The error message should include both target type names + their error messages.
    with pytest.raises(RuntimeError) as excinfo:
        dual.upsert("k2", [0.2] * 768)
    msg = str(excinfo.value)
    assert "_StubTarget" in msg
    assert "Firestore down" in msg
    assert "Vertex down" in msg


def test_dual_write_partial_failure_does_not_raise() -> None:
    """When at least one target succeeds, `upsert` returns normally."""
    primary = _StubTarget(name="Firestore", raise_on_upsert=RuntimeError("Firestore down"))
    secondary = _StubTarget(name="Vertex")
    dual = DualWriteTarget(primary, secondary, primary=primary)

    # Should NOT raise — the secondary succeeded.
    dual.upsert("k1", [0.1] * 768, {"src": "test"})

    assert primary.upserts == []  # raised
    assert len(secondary.upserts) == 1


def test_dual_write_delete_is_best_effort() -> None:
    """`DualWriteTarget.delete(key)` calls delete on every target; failures are silent."""
    primary = _StubTarget(name="Firestore")

    secondary = MagicMock()
    secondary.delete = MagicMock(side_effect=RuntimeError("Vertex delete failed"))

    dual = DualWriteTarget(primary, secondary, primary=primary)
    # Should NOT raise — delete is best-effort.
    dual.delete("k1")

    assert primary.deletes == ["k1"]
    secondary.delete.assert_called_once_with("k1")


def test_dual_write_requires_at_least_one_target() -> None:
    """`DualWriteTarget()` with no targets raises `ValueError`."""
    with pytest.raises(ValueError, match="≥1 target"):
        DualWriteTarget()


def test_dual_write_is_stub_when_all_targets_are_stubs() -> None:
    """`DualWriteTarget.is_stub` is True iff every target is in stub mode."""
    live_primary = _StubTarget(name="Firestore")
    stub = MagicMock()
    stub.is_stub = True
    stub.available = False

    dual = DualWriteTarget(live_primary, stub, primary=live_primary)
    # `live_primary.is_stub` is False, so the composite's `is_stub` is False.
    assert dual.is_stub is False

    stub_only = DualWriteTarget(stub, primary=stub)
    assert stub_only.is_stub is True


def test_dual_write_explicit_primary_kwarg() -> None:
    """The `primary=` kwarg overrides the default "first target" primary."""
    first = _StubTarget(name="First")
    second = _StubTarget(name="Second")
    explicit_primary = _StubTarget(name="ExplicitPrimary")
    dual = DualWriteTarget(first, second, primary=explicit_primary)

    # Writes still fan out to all 3.
    dual.upsert("k1", [0.1] * 768)
    assert len(first.upserts) == 1
    assert len(second.upserts) == 1
    assert len(explicit_primary.upserts) == 1

    # Reads serve from the explicit primary.
    results = dual.find_nearest_sync([0.1] * 768, k=3)
    assert results[0]["id"] == "ExplicitPrimary-0"
