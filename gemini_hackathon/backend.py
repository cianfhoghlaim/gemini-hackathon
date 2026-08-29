"""Minimal stdlib HTTP server for the gemini_hackathon Python backend.

Serves the OpenAI-compatible /api/chat/completions shape that CopilotKit
expects. Routes /api/* through the registry-backed router so every LLM
call goes through ``call_llm`` and inherits MODEL_PROFILE gating + the
exclusion guard + the structlog invocation events.

Endpoints:

    GET  /api/health
        Returns {"status": "ok", "profile": "hackathon|dev", "models": [...]}

    GET  /api/models
        Lists every visible model under the active profile.

    POST /api/chat/completions
        OpenAI-compatible. Body: {"messages": [...], "model"?: str, ...}.
        Pass `model` to pin a specific tier entry; otherwise the router
        walks the active profile's tiers in order. Streams the response
        chunk by chunk (no SSE — CopilotKit's React side buffers).

    POST /api/themes
        Returns the canonical 15-palette roster (from theming.py).

Run with:
    python -m gemini_hackathon.cli serve --port 8000
or
    python -m gemini_hackathon.backend --port 8000

This is intentionally stdlib-only (no Hono + no FastAPI). When the
project graduates to a real backend (Hono + oRPC + Convex actions),
this file is replaced — the CopilotKit proxy at
``web/app/routes/api/copilotkit.ts`` keeps the same URL shape.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import threading
from collections.abc import Iterable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class _BackendHandler(BaseHTTPRequestHandler):
    """Routes /api/* requests through the gemini_hackathon call_llm router."""

    server_version = "gemini_hackathon/0.1"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        logger.info(format, *args)

    # -- helpers ----------------------------------------------------------
    def _write_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict[str, Any] | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length == 0:
            return None
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as e:
            self._write_json(400, {"error": "invalid_json", "detail": str(e)})
            return None

    # -- HTTP methods -----------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/health":
            from . import MODEL_REGISTRY
            profile = _active_profile()
            entries = MODEL_REGISTRY.for_profile(profile)
            self._write_json(200, {
                "status": "ok",
                "profile": profile,
                "models": [e.key for e in entries],
                "model_count": len(entries),
            })
        elif self.path == "/api/models":
            from . import MODEL_REGISTRY
            profile = _active_profile()
            entries = MODEL_REGISTRY.for_profile(profile)
            self._write_json(200, {
                "object": "list",
                "data": [
                    {
                        "id": e.key,
                        "litellm_alias": e.litellm_alias,
                        "backend": e.backend,
                        "display_name": e.display_name,
                        "family": e.family,
                        "role": e.role,
                    }
                    for e in entries
                ],
                "federated_backends": [
                    "gemini-3.5-flash (Vertex AI / AI Studio)",
                    "gemma-4-26b-a4b (Unsloth Studio)",
                    "llama-3.1-8b-instruct (local)",
                ],
                "federation_note": (
                    "All model responses are routed through litellm with a "
                    "3-tier fallback chain (Vertex Gemini → Unsloth Gemma → "
                    "local Llama). All calls emit OpenTelemetry spans via the "
                    "gemini_hackathon.agents.app_utils.setup_telemetry() "
                    "pipeline to Google Cloud Trace + Cloud Logging."
                ),
            })
        elif self.path == "/api/themes":
            from . import list_all_palettes
            palettes = list_all_palettes()
            self._write_json(200, {"palettes": palettes, "count": len(palettes)})
        elif self.path == "/api/observability/health":
            self._write_json(200, _observability_health())
        else:
            self._write_json(404, {"error": "not_found", "path": self.path})

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/api/chat/completions":
            self._handle_chat_completions()
        else:
            self._write_json(404, {"error": "not_found", "path": self.path})

    def do_OPTIONS(self) -> None:  # noqa: N802
        # CORS preflight.
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    # -- chat completions -------------------------------------------------
    def _handle_chat_completions(self) -> None:
        from . import call_llm

        body = self._read_body()
        if body is None:
            return  # 400 already written

        messages = body.get("messages", [])
        if not isinstance(messages, list) or not messages:
            self._write_json(400, {"error": "messages_required"})
            return

        model_pin = body.get("model")  # Optional: pin to a specific (family, role).
        family = None
        role = None
        if model_pin and "." in model_pin:
            # Convention: "family.role" — e.g. "text_llm.default"
            family, _, role = model_pin.partition(".")

        try:
            response = call_llm(
                messages,
                family=family,
                role=role,
                temperature=body.get("temperature", 0.2),
                max_tokens=body.get("max_tokens", 1024),
                metadata={"endpoint": "/api/chat/completions"},
            )
        except Exception as e:  # noqa: BLE001
            err_type = type(e).__name__
            # Pretty-print the failure mode so the UI can render a useful
            # error instead of "Internal Server Error".
            detail = str(e) or "(no detail)"
            hint = None
            if err_type == "TypeError":
                hint = (
                    "call_llm raised TypeError — usually a router/credential "
                    "issue. Check GOOGLE_CLOUD_PROJECT (Vertex) or GEMINI_API_KEY "
                    "(AI Studio), and UNSLOTH_BASE_URL/UNSLOTH_API_KEY."
                )
            elif err_type == "LLMCallError":
                hint = (
                    "All 3 tiers failed. The most common cause is a missing "
                    "API key or unreachable backend — check the env vars above."
                )
            elif err_type == "ModelExcludedError":
                hint = (
                    "The requested model is excluded by policy (Cloudflare "
                    "Workers AI or Qwen3-coder). Pick a different model."
                )
            payload = {
                "error": err_type,
                "detail": detail[:500],
                "model_pin": model_pin,
                "active_profile": _active_profile(),
            }
            if hint:
                payload["hint"] = hint
            self._write_json(500, payload)
            return

        # OpenAI-compatible response.
        self._write_json(200, {
            "id": f"chatcmpl-{_short_id()}",
            "object": "chat.completion",
            "created": _now_epoch(),
            "model": response.model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": response.content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": response.tokens_in,
                "completion_tokens": response.tokens_out,
                "total_tokens": response.tokens_in + response.tokens_out,
            },
            "gemini_hackathon": {
                "tier": response.tier,
                "family": response.family,
                "role": response.role,
                "backend": response.backend,
                "latency_ms": response.latency_ms,
                "cost_usd": response.cost_usd,
            },
        })


def _active_profile() -> str:
    raw = os.environ.get("MODEL_PROFILE", "hackathon").strip().lower()
    return "dev" if raw == "dev" else "hackathon"


def _observability_health() -> dict[str, Any]:
    """Health probe for the GCP-native telemetry stack.

    Returns a structured payload the demo video can screenshot from the
    Vertex AI Logs Explorer. Surfaces:
      - whether google-adk + google-cloud-logging are installed
      - the resolved GCP project / location
      - whether LOGS_BUCKET_NAME is set (gates GCS prompt upload)
      - whether Fleet primitives are available
    """
    health: dict[str, Any] = {
        "gcp_project": os.environ.get("GOOGLE_CLOUD_PROJECT"),
        "gcp_location": os.environ.get("GOOGLE_CLOUD_LOCATION", "global"),
        "logs_bucket": os.environ.get("LOGS_BUCKET_NAME"),
        "agent_engine_telemetry": os.environ.get(
            "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY", "true"
        ),
        "otel_capture_mode": os.environ.get(
            "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "false"
        ),
    }
    try:
        import google.adk.agents  # noqa: F401
        import google.adk.runners  # noqa: F401
        health["google_adk"] = "installed"
    except ImportError:
        health["google_adk"] = "missing"
    try:
        from google.adk.telemetry.google_cloud import (  # noqa: F401
            get_gcp_exporters,
        )
        from google.adk.telemetry.setup import (  # noqa: F401
            maybe_set_otel_providers,
        )
        health["otel_exporters"] = "available"
    except ImportError:
        health["otel_exporters"] = "missing"
    try:
        from .agents.fleet import (  # type: ignore
            FleetIdentity,
            ModelArmor,
            Observability,
        )
        health["fleet_primitives"] = [
            "FleetIdentity",
            "ModelArmor",
            "Observability",
        ]
    except ImportError:
        health["fleet_primitives"] = []
    return health


def _short_id() -> str:
    import uuid
    return uuid.uuid4().hex[:24]


def _now_epoch() -> int:
    import time
    return int(time.time())


# ---------------------------------------------------------------------------
# Session-aware routes
# ---------------------------------------------------------------------------
# These are the routes the web app's /find-resources + /agents pages
# call. They bypass the generic LLM router and dispatch directly to the
# ADK agent's tool implementations — the in-process tools (lookup,
# retrieve, find_similar, mark, retrieve_safeguarding) are
# deterministic and don't need a real LLM call in dev.


class _SessionToolHandler(BaseHTTPRequestHandler):
    """Routes that call ADK tools directly (no LLM round-trip in dev)."""

    server_version = "gemini_hackathon/0.1"

    def log_message(self, format, *args):  # noqa: A002
        logger.info(format, *args)

    def do_OPTIONS(self):  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Session-Id")
        self.end_headers()

    def do_POST(self):  # noqa: N802
        if self.path == "/api/agents/find-resources":
            self._handle_find_resources()
        elif self.path == "/api/agents/chat":
            self._handle_agents_chat()
        elif self.path == "/api/assets/generate":
            self._handle_assets_generate()
        else:
            self._write_json(404, {"error": "not_found", "path": self.path})

    def _handle_find_resources(self):
        from .agents.tools import find_similar_resources

        body = self._read_body()
        if body is None:
            return

        active_subnation = body.get("active_subnation", "ireland")
        subject_id = body.get("subject_id", "ncca_maths_lc")
        topic = body.get("topic", "")
        k = int(body.get("k", 8))

        if not topic:
            self._write_json(400, {"error": "topic_required"})
            return

        results = find_similar_resources(
            active_subnation=active_subnation,
            subject_id=subject_id,
            topic=topic,
            k=k,
        )
        self._write_json(200, {
            "results": results,
            "active_subnation": active_subnation,
            "topic": topic,
            "count": len(results),
        })

    def _handle_agents_chat(self) -> None:
        """Run one ADK agent turn and return AG-UI events as JSON.

        Wraps the canonical starter-pack pattern with the Fortified
        Enterprise Fleet primitives: ModelArmor (input validation),
        Observability (trace + invocation record), and the App(...)
        production container.

        Dev stub: when google-adk is missing or no real LLM keys are set,
        returns a stub AG-UI event stream so the chat panel renders.
        """
        body = self._read_body()
        if body is None:
            return

        message = body.get("message", "")
        user_id = body.get("user_id", "anon")
        session_id = body.get("session_id", user_id)

        from .agents.adk_gemini_agent import (
            AGUI_EVENT_TYPES,
            GEMINI_HACKATHON_AGENT,
            is_adk_available,
            run_agent_turn,
        )

        if not is_adk_available() or not message:
            self._write_json(200, {
                "status": "stub",
                "reason": "google-adk missing or empty message",
                "events": [
                    {"type": "TEXT_MESSAGE_CONTENT", "data": {"text": "(stub) no google-adk or empty message"}},
                    {"type": "RUN_FINISHED", "data": {"status": "stub"}},
                ],
                "protocol": "agui-1.0-subset",
                "supported_event_types": list(AGUI_EVENT_TYPES),
            })
            return

        result = run_agent_turn(
            message=message,
            user_id=user_id,
            session_id=session_id,
            subnation=body.get("subnation", "ireland"),
            subnation_flag=body.get("subnation_flag", "🇮🇪"),
            awarding_body=body.get("awarding_body", "NCCA"),
            role=body.get("role", "student"),
            cycle=body.get("cycle", "leaving_cycle"),
            subjects=body.get("subjects", []),
            safeguarding_policy=body.get("safeguarding_policy", "DEIS + Well-Being"),
            palette_primary=body.get("palette_primary", "#00733B"),
            palette_heading=body.get("palette_heading", "Merriweather"),
        )

        payload: dict[str, Any] = {
            "status": result.status,
            "events": [{"type": ev.type, "data": ev.data} for ev in result.events],
            "protocol": "agui-1.0-subset",
            "supported_event_types": list(AGUI_EVENT_TYPES),
        }
        if result.error:
            payload["error"] = result.error
        if result.model_armor_check is not None:
            payload["model_armor"] = {
                "blocked": getattr(result.model_armor_check, "blocked", False),
                "reason": getattr(result.model_armor_check, "reason", None),
            }
        if result.observability is not None:
            payload["observability"] = {
                "trace_id": getattr(result.observability, "trace_id", None),
                "agent_name": GEMINI_HACKATHON_AGENT.name,
            }
        self._write_json(200, payload)

    def _handle_assets_generate(self) -> None:
        """Run the asset-generation pipeline against an AssetControlRecord.

        In dev with no real model backends, returns the deterministic stub
        so the UI can render. Always returns the full provenance chain so
        the UI can show the user every backend the router tried.
        """
        body = self._read_body()
        if body is None:
            return

        from .assets.control_record import AssetControlRecord
        from .assets.image_gen import ImageGenRouter

        try:
            record = AssetControlRecord(
                source_pdf_path=body.get("source_pdf_path", "unknown.pdf"),
                source_page=int(body.get("source_page", 0)),
                learning_outcome_id=body.get("learning_outcome_id"),
                subject=body.get("subject", ""),
                palette_primary=body.get("palette_primary", "#000000"),
                palette_secondary=body.get("palette_secondary", "#000000"),
                palette_accent=body.get("palette_accent", "#000000"),
                palette_background=body.get("palette_background", "#FFFFFF"),
                style=body.get("style", "illustration"),
                aspect_ratio=body.get("aspect_ratio", "16:9"),
                text_overlay=body.get("text_overlay"),
                seed=body.get("seed"),
            )
        except (TypeError, ValueError) as e:
            self._write_json(400, {"status": "invalid_record", "error": str(e)})
            return

        result = ImageGenRouter().generate(record, role=body.get("role"))
        self._write_json(200, {
            "status": "ok",
            "image_b64": result.image_b64,
            "backend": result.backend.value,
            "model_key": result.model_key,
            "seed": result.seed,
            "duration_ms": result.duration_ms,
            "provenance": result.provenance,
        })


# ---------------------------------------------------------------------------
# Route registration — main + session tool handler
# ---------------------------------------------------------------------------


def main(argv=None):
    parser = argparse.ArgumentParser(prog="gemini_hackathon.backend")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    from . import list_all_palettes, MODEL_REGISTRY
    profile = _active_profile()
    palettes = list_all_palettes()
    entries = MODEL_REGISTRY.for_profile(profile)
    logger.info(
        "backend.boot profile=%s themes=%d models=%d",
        profile, len(palettes), len(entries),
    )

    # Compose two handlers behind one ThreadingHTTPServer: the main
    # backend handler (for /api/themes, /api/chat/completions, ...) and
    # the session tool handler (for /api/agents/*).
    class _RoutingHandler(_BackendHandler, _SessionToolHandler):
        def do_POST(self):  # noqa: N802
            if self.path.startswith("/api/agents/") or self.path.startswith("/api/assets/"):
                _SessionToolHandler.do_POST(self)
            else:
                _BackendHandler.do_POST(self)
        def do_GET(self):  # noqa: N802
            _BackendHandler.do_GET(self)
        def do_OPTIONS(self):  # noqa: N802
            # CORS preflight — both handlers do the same thing.
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Session-Id")
            self.end_headers()

    httpd = ThreadingHTTPServer((args.host, args.port), _RoutingHandler)
    logger.info("backend.listening host=%s port=%d", args.host, args.port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("backend.shutdown")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
