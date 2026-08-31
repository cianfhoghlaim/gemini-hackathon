"""gemini_hackathon_backend.lakehouse — Lance namespace + vector target wrapper.

Phase 0 (GCP-first IaC refactor) — replaces the direct ``lancedb``
writes with the canonical ``lance_namespace`` SDK per
https://lance.org/format/namespace/supported-catalogs/biglake/
and
https://lance.org/format/namespace/supported-catalogs/iceberg/.

Public API:
  ``namespace_from_env()``        — read LANCE_NAMESPACE_BACKEND + connect
  ``LanceVectorTarget``           — a VectorTarget wrapper that writes
                                    to the namespace (replaces the
                                    FirestoreVectorTarget when
                                    LANCE_NAMESPACE_BACKEND is set)
  ``LANCE_NAMESPACE_BACKEND``     — env var: "dir" (dev) or "rest" (prod)
"""

from gemini_hackathon_backend.lakehouse.namespace import (
    SUPPORTED_BACKENDS,
    build_lance_properties,
    connect_lance_namespace,
    namespace_from_env,
)

__all__ = [
    "SUPPORTED_BACKENDS",
    "build_lance_properties",
    "connect_lance_namespace",
    "namespace_from_env",
]
