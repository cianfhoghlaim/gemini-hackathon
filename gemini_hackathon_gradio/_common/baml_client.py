"""gemini_hackathon_gradio._common.baml_client — the LLM client for the 5 Studios.

3-tier fallback chain for the gemini_hackathon editorial studios:

  Tier 1: gemini-3.5-flash on Vertex AI (production).
          Routes through `gemini_hackathon.call_llm.call_llm()` which
          uses LiteLLM as the unified gateway.
          Langfuse auto-traces every call.

  Tier 2: Unsloth Studio at 127.0.0.1:8888/v1 (dev / local).
          Hosts Gemma 4 26B-A4B-it-GGUF (the KCG-canonical local
          model). The 3-tier policy excludes `@cf/*` (Cloudflare
          Workers AI) and `qwen3-coder-*` per `docs/MODEL_POLICY.md`.

  Tier 3: HuggingFace Inference Providers (offline / Space free tier).
          3-model fallback chain (Qwen 7B → Llama 8B → Gemma 9b).

For the canonical BAML extractions, use the gemini_hackathon
baml_extracts/ functions directly — they handle schema validation +
retries + Langfuse tracing:

  - baml_extracts/education/lc_subject/ExtractSeniorCycleSyllabus
  - baml_extracts/education/jc_subject/ExtractJCSpec
  - baml_extracts/education/certification_criteria/ExtractSeniorCycleCertificationCriteria
  - baml_extracts/education/player_assessment/GenerateExitCardQuestions

These give you schema validation + retries + Langfuse tracing for
free (see the canonical baml_extracts/clients.baml LitellmClient).

This module is the schema-less codepath used by the editorial canvas
when no BAML function is needed (e.g. "describe this image" for the
HF Spaces).
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from typing import Any, Final


_log = logging.getLogger("baml_client")


# Tier 1 — call_llm() (LiteLLM gateway via gemini_hackathon.call_llm)
T1_BASE_URL: Final[str] = os.environ.get("LITELLM_BASE_URL", "http://litellm:4000/v1")
T1_DEFAULT_MODEL: Final[str] = os.environ.get("LITELLM_MODEL", "minimax")
T1_API_KEY: Final[str] = os.environ.get(
    "LITELLM_MASTER_KEY", os.environ.get("LITELLM_API_KEY", "")
)

# Tier 2 — Unsloth Studio (local Gemma 4 26B-A4B)
T2_BASE_URL: Final[str] = os.environ.get(
    "UNSLOTH_BASE_URL", "http://127.0.0.1:8888/v1"
)
T2_MODEL: Final[str] = os.environ.get(
    "UNSLOTH_MODEL", "unsloth/gemma-4-26B-A4B-it-GGUF"
)
T2_API_KEY: Final[str] = os.environ.get("UNSLOTH_API_KEY", "ollama")

# Tier 3 — HuggingFace Inference Providers
T3_BASE_URL: Final[str] = (
    os.environ.get("HF_INFERENCE_URL")
    or "https://router.huggingface.co/v1"
)
T3_FALLBACK_CHAIN: Final[tuple[str, ...]] = (
    "Qwen/Qwen2.5-7B-Instruct",
    "meta-llama/Llama-3.1-8B-Instruct",
    "google/gemma-2-9b-it",
)
T3_API_KEY: Final[str] = os.environ.get("HF_TOKEN", "")

_OPENAI_CHAT_PATH: Final[str] = "/chat/completions"


def get_client_config() -> dict[str, Any]:
    """Return the resolved 3-tier client config (for logging + UI display)."""
    return {
        "tier1_litellm": {
            "base_url": T1_BASE_URL,
            "model": T1_DEFAULT_MODEL,
            "key_set": bool(T1_API_KEY),
        },
        "tier2_unsloth": {
            "base_url": T2_BASE_URL,
            "model": T2_MODEL,
            "key_set": bool(T2_API_KEY),
        },
        "tier3_hf_inference": {
            "base_url": T3_BASE_URL,
            "fallback_chain": list(T3_FALLBACK_CHAIN),
            "key_set": bool(T3_API_KEY),
        },
    }


def _build_payload(
    messages: list[dict[str, str]],
    model: str,
    *,
    max_tokens: int = 4096,
    temperature: float = 0.1,
    response_format_json: bool = True,
) -> dict[str, Any]:
    """Build the OpenAI-compatible request body."""
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if response_format_json:
        payload["response_format"] = {"type": "json_object"}
    return payload


def _post_json(url: str, payload: dict[str, Any], token: str, timeout: int) -> dict[str, Any]:
    """POST a JSON payload and return the parsed response."""
    headers: dict[str, str] = {
        "Content-Type": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body)


def _extract_message(payload: dict[str, Any]) -> str:
    """Extract the assistant message text from a chat-completions response."""
    try:
        return str(payload["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError) as e:
        raise ValueError(f"Malformed chat-completion response: {e}") from e


def _try_tier(
    tier_name: str,
    base_url: str,
    model: str,
    api_key: str,
    messages: list[dict[str, str]],
    *,
    max_tokens: int,
    temperature: float,
    timeout: int,
) -> tuple[str, str] | None:
    """Try a single tier. Return (text, model) on success, None on failure."""
    if not api_key and tier_name != "unsloth":  # unsloth tolerates no-key
        _log.info("%s key not set; skipping tier %s", tier_name, tier_name)
        return None
    url = base_url.rstrip("/") + _OPENAI_CHAT_PATH
    payload = _build_payload(messages, model, max_tokens=max_tokens, temperature=temperature)
    try:
        start = time.time()
        resp = _post_json(url, payload, api_key, timeout)
        elapsed = time.time() - start
        _log.info("%s OK: %s (%.2fs)", tier_name, model, elapsed)
        return _extract_message(resp), model
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        _log.warning("%s failed: %s; falling through", tier_name, e)
        return None


def chat_complete(
    messages: list[dict[str, str]],
    *,
    max_tokens: int = 4096,
    temperature: float = 0.1,
    timeout: int = 60,
    max_model_retries: int = 1,
) -> tuple[str, str]:
    """Call the canonical LLM with the 3-tier fallback chain.

    Tier 1: LiteLLM gateway (production).
    Tier 2: Unsloth Studio (dev / local Gemma 4 26B-A4B).
    Tier 3: HuggingFace Inference Providers (offline / Space free tier).

    Returns:
        (content, model_used) - the assistant's text and the name of
        the model that ultimately produced it.

    Raises:
        RuntimeError: If all 3 tiers fail.
    """
    last_err: Exception | None = None

    for tier_name, base_url, model, api_key in (
        ("tier1_litellm", T1_BASE_URL, T1_DEFAULT_MODEL, T1_API_KEY),
        ("tier2_unsloth", T2_BASE_URL, T2_MODEL, T2_API_KEY),
        ("tier3_hf_inference", T3_BASE_URL, T3_FALLBACK_CHAIN[0], T3_API_KEY),
    ):
        result = _try_tier(
            tier_name,
            base_url,
            model,
            api_key,
            messages,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
        )
        if result is not None:
            return result
        last_err = RuntimeError(f"{tier_name} failed")

    raise RuntimeError(
        f"All 3 LLM tiers failed (LiteLLM + Unsloth Studio + HF Inference). "
        f"Last error: {last_err}"
    )


def chat_complete_json(
    messages: list[dict[str, str]],
    *,
    max_tokens: int = 4096,
    temperature: float = 0.1,
) -> tuple[dict[str, Any], str]:
    """Call chat_complete and parse the response as JSON.

    Returns:
        (parsed_dict, model_used). Raises ValueError if the response is
        not valid JSON.
    """
    text, model = chat_complete(messages, max_tokens=max_tokens, temperature=temperature)
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    try:
        return json.loads(text), model
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON: {e}; text was: {text[:200]}") from e
