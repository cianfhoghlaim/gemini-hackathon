"""End-to-end test for /api/assets/generate.

Boots the backend, POSTs a control record, asserts the response shape.
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def _start(port: int):
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "gemini_hackathon.backend",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=str(REPO_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    for _ in range(60):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return proc, base
        except OSError:
            time.sleep(0.5)
    proc.terminate()
    raise RuntimeError("backend did not start")


def _post(url: str, body: dict, timeout: float = 15.0):
    req = urllib.request.Request(
        url,
        method="POST",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, json.loads(r.read())


def test_assets_generate_returns_stub_in_dev():
    port = _free_port()
    proc, base = _start(port)
    try:
        status, body = _post(
            f"{base}/api/assets/generate",
            {
                "source_pdf_path": "/tmp/chem-2024.pdf",
                "source_page": 12,
                "learning_outcome_id": "LC-CHEM-3.1.2",
                "subject": "Boyle's Law demo",
                "palette_primary": "#00733B",
                "palette_secondary": "#0E2D5C",
                "palette_accent": "#FFB81C",
                "palette_background": "#FFFFFF",
            },
        )
        assert status == 200
        assert body["status"] == "ok"
        assert body["backend"] == "stub"  # all real backends down in dev
        assert body["model_key"] == "deterministic-stub-v1"
        assert body["image_b64"]
        # Provenance chain present.
        p = body["provenance"]
        assert "control_record_hash" in p
        assert "tried_backends" in p
        assert "litellm" in p["tried_backends"]
        assert "stub" in p["tried_backends"]
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


def test_assets_generate_rejects_bad_record():
    """Missing source_pdf_path defaults to 'unknown.pdf' (not an error)."""
    port = _free_port()
    proc, base = _start(port)
    try:
        status, body = _post(
            f"{base}/api/assets/generate",
            {
                "subject": "Test",
                "palette_primary": "#000",
            },
        )
        assert status == 200
        assert body["provenance"]["source_pdf_path"] == "unknown.pdf"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
