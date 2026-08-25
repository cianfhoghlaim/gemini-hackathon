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
                    {"id": e.key, "litellm_alias": e.litellm_alias, "backend": e.backend}
                    for e in entries
                ],
            })
        elif self.path == "/api/themes":
            from . import list_all_palettes
            palettes = list_all_palettes()
            self._write_json(200, {"palettes": palettes, "count": len(palettes)})
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
            self._write_json(500, {"error": type(e).__name__, "detail": str(e)})
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


def _short_id() -> str:
    import uuid
    return uuid.uuid4().hex[:24]


def _now_epoch() -> int:
    import time
    return int(time.time())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gemini_hackathon.backend")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Pre-import the gemini_hackathon package so the registry + router are
    # ready before any request comes in.
    from . import list_all_palettes, MODEL_REGISTRY
    profile = _active_profile()
    palettes = list_all_palettes()
    entries = MODEL_REGISTRY.for_profile(profile)
    logger.info(
        "backend.boot profile=%s themes=%d models=%d",
        profile, len(palettes), len(entries),
    )

    httpd = ThreadingHTTPServer((args.host, args.port), _BackendHandler)
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
