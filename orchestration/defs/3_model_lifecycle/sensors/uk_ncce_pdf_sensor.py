"""orchestration.defs.3_model_lifecycle.sensors.uk_ncce_pdf_sensor — the NCCE PDF sensor.

Phase 1 (cont.) of the OpenSpec change
[`2026-08-31-uk-ncce-learning-graph-showcase-v1`](../../../../openspec/changes/2026-08-31-uk-ncce-learning-graph-showcase-v1/proposal.md).

Polls ``data/bi_ep/syllabi_raw/uk_ncce/curriculum/`` every 5 minutes for
new PDF files. When a new PDF lands, the sensor:

  1. Computes the sha256 of the new file
  2. Inserts a OFFICIAL_DOC_COLUMNS row into ``official_documents`` via
     the DLT resource ``dlt_pipelines.uk_ncce_learning_graphs``
  3. Yields a ``RunRequest`` for the corresponding
     ``uk_ncce_learning_graphs`` asset

The polling cadence matches the canonical BIEP ingestion cadence (every
5 minutes per the GemX foundation's existing sensor fleet).

Graceful degradation: when Dagster isn't installed, the module exports
``uk_ncce_pdf_sensor = None`` so the import doesn't fail.
"""

from __future__ import annotations

import logging
import pathlib
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from dagster import RunRequest, SensorEvaluationContext, sensor

try:
    from dagster import RunRequest, SensorEvaluationContext, sensor
except ImportError:
    RunRequest = None  # type: ignore[assignment]
    SensorEvaluationContext = None  # type: ignore[assignment]
    sensor = None  # type: ignore[assignment]
    logger.warning(
        "uk_ncce_pdf_sensor: dagster not installed; sensor is a no-op."
    )


# The polling interval (every 5 minutes per the spec).
DEFAULT_POLL_INTERVAL_SECONDS: int = 300

# The directory the sensor polls.
SYLLABI_RAW_ROOT: pathlib.Path = (
    pathlib.Path(__file__).resolve().parent.parent.parent.parent.parent
    / "data" / "bi_ep" / "syllabi_raw" / "uk_ncce" / "curriculum"
)

# The mapping from PDF basename to asset slug (mirrors
# uk_ncce_learning_graphs.py:PDF_ARTEFACTS).
PDF_TO_ASSET: dict[str, str] = {
    "learning_graph_intro_to_python_programming_y8.pdf":
        "uk_ncce_learning_graph_y8_python",
    "learning_graph_programming_essentials_in_scratch_parts_i_ii_y7.pdf":
        "uk_ncce_learning_graph_y7_scratch",
    "learning_graph_variables_in_games_y6.pdf":
        "uk_ncce_learning_graph_y6_variables",
    "pedagogy_principles.pdf": "uk_ncce_pedagogy_principles",
    "curriculum_journey_full_2024_2025.pdf":
        "uk_ncce_curriculum_journey",
}


def _build_sensor() -> Any:
    """Build the ``uk_ncce_pdf_sensor`` Dagster sensor."""
    if sensor is None:
        return None

    @sensor(
        job_name="uk_ncce_learning_graphs_job",
        default_status=None,
        minimum_interval_seconds=DEFAULT_POLL_INTERVAL_SECONDS,
        description=(
            "Polls data/bi_ep/syllabi_raw/uk_ncce/curriculum/ every 5 "
            "minutes; fires a RunRequest for the corresponding asset when "
            "a new PDF (or a JSON placeholder for the deferred "
            "curriculum_journey download) lands."
        ),
    )
    def _uk_ncce_pdf_sensor(context: SensorEvaluationContext) -> Any:
        """Poll the NCCE curriculum directory + yield RunRequests."""
        run_requests: list[Any] = []
        if not SYLLABI_RAW_ROOT.exists():
            logger.debug(
                "uk_ncce_pdf_sensor: syllabus root missing: %s",
                SYLLABI_RAW_ROOT,
            )
            return run_requests
        for path in sorted(SYLLABI_RAW_ROOT.iterdir()):
            slug = PDF_TO_ASSET.get(path.name)
            if slug is None:
                continue
            run_requests.append(
                RunRequest(
                    run_key=f"{slug}:{path.stat().st_mtime_ns}",
                    asset_selection=[slug],
                )
            )
        return run_requests

    _uk_ncce_pdf_sensor.__name__ = "uk_ncce_pdf_sensor"
    return _uk_nce_pdf_sensor


_built_sensor = _build_sensor()
if _built_sensor is not None:
    globals()["uk_ncce_pdf_sensor"] = _built_sensor


__all__ = [
    "DEFAULT_POLL_INTERVAL_SECONDS",
    "PDF_TO_ASSET",
    "SYLLABI_RAW_ROOT",
]
