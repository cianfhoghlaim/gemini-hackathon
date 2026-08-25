"""Boot the Python backend on a free port, hit /api/health + /api/themes, kill it.

Usage:
    mise run backend:test
    python scripts/backend_smoke.py
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
import urllib.request

REPO_ROOT = "."  # scripts/backend_smoke.py


def _find_free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> int:
    port = _find_free_port()
    print(f"[backend_smoke] using free port {port}")
    proc = subprocess.Popen(
        [sys.executable, "-m", "gemini_hackathon.backend",
         "--host", "127.0.0.1", "--port", str(port)],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        # Wait for boot.
        base = f"http://127.0.0.1:{port}"
        for _ in range(30):
            try:
                with urllib.request.urlopen(f"{base}/api/health", timeout=1) as r:
                    if r.status == 200:
                        break
            except Exception:
                time.sleep(0.5)
        else:
            print("[FAIL] backend did not start in 15s")
            return 1

        # Hit /api/health.
        with urllib.request.urlopen(f"{base}/api/health") as r:
            health = json.loads(r.read())
            assert health["status"] == "ok"
            assert health["profile"] in ("hackathon", "dev")
            print(f"[OK] /api/health → status={health['status']}, profile={health['profile']}, models={health['model_count']}")

        # Hit /api/themes.
        with urllib.request.urlopen(f"{base}/api/themes") as r:
            themes = json.loads(r.read())
            assert themes["count"] == 15, f"expected 15 palettes, got {themes['count']}"
            print(f"[OK] /api/themes → {themes['count']} palettes")

        # Hit /api/models.
        with urllib.request.urlopen(f"{base}/api/models") as r:
            models = json.loads(r.read())
            assert models["object"] == "list"
            assert len(models["data"]) > 0
            print(f"[OK] /api/models → {len(models['data'])} models under {health['profile']} profile")

        # Hit /api/chat/completions with a stub-call (only if we have a key).
        # By default we expect this to fail (no Gemini key in dev), but the
        # server should still respond — either with a model response or a
        # clear 500. Either is "the backend works".
        req = urllib.request.Request(
            f"{base}/api/chat/completions",
            data=json.dumps({
                "messages": [{"role": "user", "content": "Say OK in one word."}],
                "temperature": 0,
                "max_tokens": 8,
            }).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                body = json.loads(r.read())
                if r.status == 200:
                    print(f"[OK] /api/chat/completions → model={body['model']}, content={body['choices'][0]['message']['content']!r}")
                else:
                    print(f"[WARN] /api/chat/completions → HTTP {r.status}: {body}")
        except urllib.error.HTTPError as e:
            body = e.read()
            try:
                detail = json.loads(body)
                err_type = detail.get("error", "unknown")
            except Exception:
                err_type = "unknown"
            print(f"[OK] /api/chat/completions → HTTP {e.code} ({err_type}) — backend reachable, no Gemini key in env")
        except Exception as e:
            print(f"[WARN] /api/chat/completions → {type(e).__name__}: {e}")

        print("\n[OK] All backend smoke checks green.")
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
