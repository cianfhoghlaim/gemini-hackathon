"""gemini_hackathon_gradio._common.baml_pydantic_bridge — the BAML → Pydantic mirror pattern.

Lifted from `sruth/spaces/an_scrudu/extraction.py` and generalised.

When the canonical BAML function (in `gemini_hackathon/baml_extracts/`)
is available, prefer that — it gives you schema validation + retries +
Langfuse tracing for free. This bridge exists for two reasons:

  1. Tests + dev environments where the BAML client is unavailable
     (the baml_client/ folder is git-ignored and re-emitted by
     `baml-cli generate`). The bridge lets the editorial studios run
     in dev without BAML compilation.

  2. Ad-hoc scripts that need to validate LLM JSON against a Pydantic
     model without going through the BAML compiler. The 5 Studios
     use this when the operator passes a free-form prompt and we
     need to coerce the response into a typed record.

Usage:

    from gemini_hackathon_gradio._common.baml_pydantic_bridge import (
        mirror_baml_schema,
        extract_via_llm,
        fallback_regex,
    )
    from pydantic import BaseModel

    class MyRecord(BaseModel):
        subject: str
        year: int

    schema = mirror_baml_schema(MyRecord)

    # Try LLM first; fall back to regex if LLM unreachable.
    record = extract_via_llm(schema, messages=[...], timeout=60)
    if record is None:
        record = fallback_regex(text, MyRecord)
"""

from __future__ import annotations

import logging
import re
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

_log = logging.getLogger("baml_pydantic_bridge")

T = TypeVar("T", bound=BaseModel)


def mirror_baml_schema(model_cls: type[T]) -> dict[str, Any]:
    """Generate the BAML-style JSON schema dict from a Pydantic model.

    Mirrors the shape of a `.baml` class so the LLM prompt can describe
    the expected JSON shape to the model.
    """
    return model_cls.model_json_schema()


def pydantic_to_baml_prompt_hint(model_cls: type[T]) -> str:
    """Return a compact human-readable schema description for the LLM prompt.

    Example output:
        subject (str, required): The subject name
        year (int, required): The year of the paper
    """
    schema = mirror_baml_schema(model_cls)
    lines: list[str] = []
    for field_name, field_info in schema.get("properties", {}).items():
        required = field_name in schema.get("required", [])
        type_str = field_info.get("type", "any")
        desc = field_info.get("description", "")
        line = f"- {field_name} ({type_str}"
        if required:
            line += ", required"
        line += ")"
        if desc:
            line += f": {desc}"
        lines.append(line)
    return "\n".join(lines)


def extract_via_llm(
    model_cls: type[T],
    messages: list[dict[str, str]],
    *,
    timeout: int = 60,
    temperature: float = 0.1,
) -> T | None:
    """Call the 3-tier LLM and parse the response into a Pydantic model.

    Returns None if all 3 tiers fail OR the LLM returns invalid JSON.
    """
    schema_hint = pydantic_to_baml_prompt_hint(model_cls)
    sys_prompt = (
        "You are an expert extractor. From the input below, extract every "
        "field in the return type. Return ONLY valid JSON (no markdown "
        "wrapping, no preamble) matching this schema:\n\n"
        f"{schema_hint}\n"
    )
    full_messages = [{"role": "system", "content": sys_prompt}, *messages]
    try:
        from .baml_client import chat_complete_json

        parsed, _model = chat_complete_json(full_messages, temperature=temperature)
    except Exception as e:
        _log.warning("LLM extraction failed: %s", e)
        return None
    try:
        return model_cls.model_validate(parsed)
    except ValidationError as e:
        _log.warning("LLM JSON did not match schema: %s; raw: %s", e, parsed)
        return None


def fallback_regex(model_cls: type[T], text: str) -> T | None:
    """Last-resort offline extraction.

    Tries to coerce free-form text into the Pydantic model using a
    series of regex heuristics. Returns None if the coercion fails.
    These heuristics are deliberately conservative — we prefer a None
    return to a hallucinated record.
    """
    schema = mirror_baml_schema(model_cls)
    candidates: dict[str, Any] = {}
    for field_name, _field_info in schema.get("properties", {}).items():
        # Try field-name-keyed extraction first.
        for pat in (
            rf"{re.escape(field_name)}\s*[:=]\s*[\"']?([^\"'\n,]+)",
            rf"\"{re.escape(field_name)}\"\s*:\s*[\"']?([^\"'\n,]+)",
        ):
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                candidates[field_name] = m.group(1).strip().strip("\"' ")
                break
    try:
        return model_cls.model_validate(candidates)
    except ValidationError:
        return None


def extract_with_fallback(
    model_cls: type[T],
    messages: list[dict[str, str]],
    raw_text: str,
    *,
    timeout: int = 60,
) -> T | None:
    """Try LLM first; fall back to regex on raw_text if LLM fails."""
    record = extract_via_llm(model_cls, messages, timeout=timeout)
    if record is not None:
        return record
    return fallback_regex(model_cls, raw_text)


__all__ = [
    "extract_via_llm",
    "extract_with_fallback",
    "fallback_regex",
    "mirror_baml_schema",
    "pydantic_to_baml_prompt_hint",
]
