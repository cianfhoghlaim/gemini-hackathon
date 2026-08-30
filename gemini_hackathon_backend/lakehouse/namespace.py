"""gemini_hackathon_backend.lakehouse.namespace — Lance namespace factory.

Phase 0 (GCP-first IaC refactor) — replaces the direct ``lancedb``
writes with the canonical ``lance_namespace`` SDK.

Three catalog backends are supported, per the Lance docs:

  - ``"dir"``     — local filesystem Directory V2 namespace
                    (the canonical dev path; zero deps).
                    Reference: https://lance.org/format/namespace/supported-catalogs/directory/
  - ``"rest"``    — REST API namespace. Works for both the cianfhoghlaim-
                    parity Lakekeeper path AND the GCP-native BigLake
                    Iceberg REST catalog (BigLake is exposed as an
                    Iceberg-REST-compatible endpoint).
                    Reference: https://lance.org/format/namespace/supported-catalogs/biglake/
                    Reference: https://lance.org/format/namespace/supported-catalogs/iceberg/
  - ``"dynamodb"`` / ``"glue"`` / ``"unity"`` — other backends; not used
                    in gemini-hackathon but listed for completeness.

Public API:
  ``connect_lance_namespace(backend, **properties)`` — returns a
  ``lance_namespace.LanceNamespace`` instance.
  ``build_lance_properties(backend, ...)`` — builds the property dict
  per backend (validates required keys + formats the URL/host).

The CocoIndex vector target wrapper is in
``cocoindex_flows/_shared/_vector_target.py`` and reads
``LANCE_NAMESPACE_BACKEND`` env var at every ``mount_table_target`` call.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


#: The 3 Lance namespace backends we support.
SUPPORTED_BACKENDS: tuple[str, ...] = (
    "dir",     # local filesystem (dev)
    "rest",    # Lakekeeper OR BigLake Iceberg REST (prod)
    "dynamodb",
    "glue",
    "unity",
)


def build_lance_properties(
    backend: str,
    *,
    # "dir" properties
    root: str | None = None,
    # "rest" properties (Lakekeeper or BigLake Iceberg REST)
    host: str | None = None,
    # "rest" + BigLake-only properties
    project: str | None = None,
    region: str | None = None,
    catalog_id: str | None = None,
    # "rest" + Lakekeeper-only properties
    namespace: str | None = None,
) -> dict[str, str]:
    """Build the property dict for one backend.

    Returns the dict that ``lance_namespace.connect(impl, properties)``
    expects. Validates the required keys per backend.

    Required keys per backend:
      - "dir"  : ``root`` (the local filesystem path)
      - "rest" : ``host`` (the REST endpoint URL); optional
                  ``namespace`` (Lakekeeper) or
                  ``project + region + catalog_id`` (BigLake)
    """
    backend = backend.lower()
    if backend == "dir":
        if not root:
            raise ValueError("build_lance_properties(backend='dir') requires `root`")
        return {"root": root}
    if backend == "rest":
        # Per the Lance REST namespace spec (v0.4+), the URL is supplied
        # as the `uri` property. We map `host` -> `uri` internally so
        # callers can use the more familiar name.
        #
        # If project/region/catalog_id is given (the BigLake pattern),
        # auto-construct the URL so the caller doesn't have to.
        if not host and project and region and catalog_id:
            host = (
                f"https://biglake.googleapis.com/v1"
                f"/projects/{project}"
                f"/locations/{region}"
                f"/catalogs/{catalog_id}"
            )
        if not host:
            raise ValueError("build_lance_properties(backend='rest') requires `host`")
        props: dict[str, str] = {"uri": host}
        # BigLake Iceberg REST: project + region + catalog_id (Google-style
        # host: https://biglake.googleapis.com/v1/projects/PROJECT/locations/REGION/catalogs/CATALOG)
        if project:
            props["project"] = project
        if region:
            props["region"] = region
        if catalog_id:
            props["catalog_id"] = catalog_id
        # Lakekeeper (self-hosted) uses a plain namespace.
        if namespace:
            props["namespace"] = namespace
        return props
    raise ValueError(
        f"build_lance_properties: unsupported backend {backend!r}. "
        f"Supported: {SUPPORTED_BACKENDS}"
    )


def connect_lance_namespace(
    backend: str,
    *,
    root: str | None = None,
    host: str | None = None,
    project: str | None = None,
    region: str | None = None,
    catalog_id: str | None = None,
    namespace: str | None = None,
) -> Any:
    """Return a ``lance_namespace.LanceNamespace`` for the given backend.

    Args:
        backend: One of ``"dir"`` (dev) or ``"rest"`` (Lakekeeper / BigLake prod).
        root: For ``"dir"``, the local filesystem path (e.g.
            ``~/.gemini_hackathon/lance``).
        host: For ``"rest"``, the REST endpoint URL.
        project / region / catalog_id: For BigLake Iceberg REST, the
            GCP project + region + catalog ID (the BigLake endpoint URL
            is derived from these).
        namespace: For Lakekeeper, the namespace ID.

    Returns:
        A ``lance_namespace.LanceNamespace`` instance.

    Raises:
        ValueError: If the backend is unsupported or required properties
            are missing.
        ImportError: If the ``lance-namespace`` package is not installed.
    """
    properties = build_lance_properties(
        backend,
        root=root,
        host=host,
        project=project,
        region=region,
        catalog_id=catalog_id,
        namespace=namespace,
    )
    import lance_namespace  # type: ignore[import-not-found]
    namespace_instance = lance_namespace.connect(backend, properties)
    logger.info(
        "lance_namespace.connected",
        backend=backend,
        properties=list(properties.keys()),
    )
    return namespace_instance


def namespace_from_env() -> Any | None:
    """Read ``LANCE_NAMESPACE_BACKEND`` + related env vars and connect.

    Returns the connected namespace, or ``None`` if the env var is unset
    (the canonical "no namespace requested" path — the caller falls back
    to the in-process LanceDB write).
    """
    backend = os.environ.get("LANCE_NAMESPACE_BACKEND", "").strip().lower()
    if not backend:
        return None
    if backend == "dir":
        return connect_lance_namespace(
            backend="dir",
            root=os.environ.get(
                "LANCE_NAMESPACE_DIR_ROOT",
                os.path.expanduser("~/.gemini_hackathon/lance"),
            ),
        )
    if backend == "rest":
        # BigLake Iceberg REST (GCP-native) when GCP_PROJECT_ID is set;
        # otherwise a plain REST host (Lakekeeper / cianfhoghlaim-parity).
        if os.environ.get("GCP_PROJECT_ID"):
            return connect_lance_namespace(
                backend="rest",
                host=os.environ.get(
                    "LANCE_ICEBERG_HOST",
                    (
                        f"https://biglake.googleapis.com/v1"
                        f"/projects/{os.environ['GCP_PROJECT_ID']}"
                        f"/locations/{os.environ.get('GOOGLE_CLOUD_LOCATION', 'us-central1')}"
                        f"/catalogs/{os.environ.get('LANCE_ICEBERG_CATALOG', 'gemini_hackathon')}"
                    ),
                ),
            )
        return connect_lance_namespace(
            backend="rest",
            host=os.environ.get("LANCE_ICEBERG_HOST", "http://localhost:8181"),
        )
    raise ValueError(
        f"namespace_from_env: unsupported LANCE_NAMESPACE_BACKEND={backend!r}. "
        f"Supported: {SUPPORTED_BACKENDS}"
    )


__all__ = [
    "SUPPORTED_BACKENDS",
    "build_lance_properties",
    "connect_lance_namespace",
    "namespace_from_env",
]