"""gemini_hackathon_backend.lakehouse.lance_vector_target — VectorTarget impl backed by Lance namespace.

Phase 0 (GCP-first IaC refactor) — implements the
``cocoindex_flows._shared._vector_target.VectorTarget`` Protocol using
the Lance namespace SDK. Used when ``LANCE_NAMESPACE_BACKEND=dir|rest``
is set (overrides the Firestore native vector path).

References:
  - https://lance.org/format/namespace/
  - https://lance.org/format/namespace/supported-catalogs/biglake/
  - https://lance.org/format/namespace/supported-catalogs/iceberg/
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cocoindex_flows._shared._vector_target import VectorMatch, VectorRow
    from lance_namespace import LanceNamespace  # type: ignore[import-not-found]

logger = logging.getLogger(__name__)


class LanceVectorTarget:
    """`VectorTarget` backed by the Lance namespace SDK.

    Replaces the FirestoreVectorTarget when LANCE_NAMESPACE_BACKEND is set.
    Writes go through the canonical ``lance_namespace.LanceNamespace``
    API which supports both the local Directory V2 backend (dev) and the
    BigLake Iceberg REST backend (prod).
    """

    def __init__(self, namespace: LanceNamespace):
        self._namespace = namespace

    async def upsert_batch(self, rows: list[VectorRow]) -> int:
        """Upsert a batch of rows. Returns the count written.

        The Lance namespace API is sync; we wrap it in an async method to
        satisfy the VectorTarget Protocol. For real production use, the
        caller should batch writes (Lance is column-store, so bulk
        inserts are much faster than row-by-row).
        """
        if not rows:
            return 0
        # Group rows by (namespace_name, table_name) for efficient writes
        from collections import defaultdict

        grouped: dict[tuple[str, str], list[VectorRow]] = defaultdict(list)
        for row in rows:
            table_id = row.table_id if hasattr(row, "table_id") else "default"
            namespace_name = table_id.split(".")[0] if "." in table_id else "default"
            table_name = table_id.split(".")[-1] if "." in table_id else table_id
            grouped[(namespace_name, table_name)].append(row)

        written = 0
        for (namespace_name, table_name), batch in grouped.items():
            try:
                # Lance namespace is sync; the create + insert calls are
                # straightforward.
                self._namespace.create_namespace_if_not_exists(namespace_name)
                # Serialize rows to Arrow tables for efficient insert.
                try:
                    import pyarrow as pa  # type: ignore[import-not-found]
                except ImportError:
                    logger.warning("lance_vector_target.pyarrow_missing — falling back to JSON")
                    return self._upsert_via_json(namespace_name, table_name, batch)
                # Build the Arrow table from the rows.
                table = self._rows_to_arrow(batch, pa)
                self._namespace.create_table_if_not_exists(
                    namespace_name, table_name, schema=table.schema
                )
                self._namespace.insert_into_table(namespace_name, table_name, table)
                written += len(batch)
            except Exception as exc:
                logger.warning(
                    "lance_vector_target.upsert_failed ns=%s table=%s reason=%s",
                    namespace_name,
                    table_name,
                    exc,
                )
        return written

    def _upsert_via_json(
        self,
        namespace_name: str,
        table_name: str,
        batch: list[VectorRow],
    ) -> int:
        """Fallback upsert path when pyarrow is not installed."""

        written = 0
        for _row in batch:
            try:
                self._namespace.insert_into_table(
                    namespace_name,
                    table_name,
                    [
                        {"id": str(r.id), "vector": list(r.vector), **(r.payload or {})}
                        for r in batch
                    ],
                )
                written += len(batch)
                break  # Lance namespace batched the insert
            except Exception as exc:
                logger.warning("lance_vector_target.fallback_upsert_failed reason=%s", exc)
        return written

    def _rows_to_arrow(self, rows: list[VectorRow], pa: Any) -> Any:
        """Build a pyarrow.Table from the rows. Falls back to None if schema unknown."""
        ids = [str(r.id) for r in rows]
        vectors = [list(r.vector) for r in rows]
        if not rows:
            return pa.table({"id": [], "vector": []})
        # Coerce payload fields into columns when possible
        payload_keys: set[str] = set()
        for r in rows:
            if r.payload:
                payload_keys.update(r.payload.keys())
        arrays: dict[str, Any] = {
            "id": pa.array(ids, type=pa.string()),
            "vector": pa.array(vectors, type=pa.list_(pa.float32())),
        }
        for k in payload_keys:
            arrays[k] = pa.array([(r.payload or {}).get(k) for r in rows])
        return pa.table(arrays)

    async def find_nearest(
        self,
        table_name: str,
        query_vector: list[float],
        *,
        k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[VectorMatch]:
        """Return the k nearest rows to query_vector.

        Uses the Lance namespace's ``query_table`` API for ANN search
        (delegates to Lance's IVF/PQ/HNSW indices under the hood).
        """
        try:
            results = self._namespace.query_table(
                table_name,
                query=query_vector,
                k=k,
                filter=filters,
            )
        except Exception as exc:
            logger.warning("lance_vector_target.query_failed reason=%s", exc)
            return []
        # Map the Lance rows back to the VectorMatch protocol
        from cocoindex_flows._shared._vector_target import VectorMatch

        matches: list[VectorMatch] = []
        for row in results:
            row_id = getattr(row, "id", None) or (row.get("id") if isinstance(row, dict) else None)
            distance = getattr(row, "_distance", None) or (
                row.get("_distance") if isinstance(row, dict) else 0.0
            )
            payload = {
                k: v
                for k, v in (row.items() if isinstance(row, dict) else vars(row).items())
                if k not in ("id", "vector", "_distance")
            }
            matches.append(VectorMatch(id=row_id, distance=float(distance), payload=payload))
        return matches

    async def close(self) -> None:
        """No-op for the Lance namespace (it's connectionless)."""
        return


__all__ = ["LanceVectorTarget"]
