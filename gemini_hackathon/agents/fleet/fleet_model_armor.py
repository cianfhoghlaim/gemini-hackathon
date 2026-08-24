"""gemini_hackathon.agents.fleet.fleet_model_armor — input/output validation.

The 3rd Fleet primitive (per the openspec
``2026-08-24-gemini-hackathon-public-v1``). Provides the canonical
defense layer for every idea agent:

* **Prompt injection defense** — heuristic + regex pattern
  matching against the OWASP LLM01:2025 prompt-injection catalogue.
* **Jailbreak detection** — flag content that resembles known
  jailbreak patterns (DAN, developer mode, token smuggling).
* **PII redaction** — best-effort regex redaction of emails,
  phone numbers, and Irish/UK PPS numbers before any LLM call.
* **Length cap** — reject prompts that exceed the configured
  token budget.
* **Output sanitisation** — strip model output of known-bad
  patterns (e.g. ``<system>`` overrides, HTML comment smuggling).

This is a wholesale port of the Cianfhoghlaim
``agents/fleet/armor.py`` module (per the
``wholesale-copy-convention``), adapted to the gemini_hackathon
context (no Cloudflare Workers AI or Qwen3-coder concerns leak
through — the armor layer only inspects input/output text).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


#: Maximum prompt length (in characters) before :class:`PromptTooLongError`
#: is raised. The default (~50k chars) maps to roughly 12-15k tokens for
#: an English-language curriculum syllabus.
DEFAULT_MAX_PROMPT_CHARS: int = 50_000

#: Maximum completion length (in characters) before the output is truncated.
DEFAULT_MAX_COMPLETION_CHARS: int = 16_000


# ---------------------------------------------------------------------------
# Prompt-injection patterns (OWASP LLM01:2025 + Cianfhoghlaim-curated)
# ---------------------------------------------------------------------------

#: Phrases that appear in >90% of known prompt-injection attempts.
INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|above)", re.IGNORECASE),
    re.compile(r"forget\s+(everything|all)", re.IGNORECASE),
    re.compile(r"override\s+(system|safety)\s+(prompt|instructions?)", re.IGNORECASE),
    re.compile(r"reveal\s+(the\s+)?system\s+prompt", re.IGNORECASE),
    re.compile(r"print\s+(your\s+|the\s+)?(system|initial)\s+prompt", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(in\s+)?(DAN|developer|god|jailbreak)\s+mode", re.IGNORECASE),
    re.compile(r"\bDAN\s+mode\b", re.IGNORECASE),
    re.compile(r"without\s+(any\s+)?(ethical|safety)\s+(filter|restriction|guideline)", re.IGNORECASE),
    re.compile(r"<\|im_start\|>|<\|im_end\|>|\[\[INST\]\]|\[\[/INST\]\]"),
    re.compile(r"<system>\s*</system>|<system>.*?</system>", re.IGNORECASE | re.DOTALL),
    re.compile(r"\\u200b|\\u200c|\\u200d|\\u2060", re.IGNORECASE),  # zero-width smuggling
)

#: Jailbreak / role-override patterns.
JAILBREAK_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bpretend\s+(to\s+be|you('re| are))\b", re.IGNORECASE),
    re.compile(r"\b(roleplay|role\s*play)\s+as\b", re.IGNORECASE),
    re.compile(r"\bact\s+as\s+(an?\s+)?(uncensored|unfiltered|jailbroken)\b", re.IGNORECASE),
    re.compile(r"\bbypass\s+(content|safety)\s+(filter|policy)", re.IGNORECASE),
    re.compile(r"\b(simulate|fake)\s+(a\s+)?(conversation|chat)\b", re.IGNORECASE),
)

#: PII patterns — emails + phone numbers + Irish/UK PPS/NI numbers.
PII_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    re.compile(r"\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}"),
    re.compile(r"\b\d{7}[A-Z]{1,2}\b"),  # Irish PPS (7 digits + 1-2 letters)
    re.compile(r"\b[A-Z]{2}\d{6}[A-D]\b"),  # UK NINo (2 letters + 6 digits + suffix)
)


# ---------------------------------------------------------------------------
# Exception types
# ---------------------------------------------------------------------------


class ArmorError(ValueError):
    """Base class for every armor-layer failure."""


class PromptInjectionError(ArmorError):
    """Raised when a prompt matches a known injection pattern."""

    def __init__(self, message: str, *, matched_patterns: Sequence[str]) -> None:
        super().__init__(message)
        self.matched_patterns: list[str] = list(matched_patterns)


class JailbreakError(ArmorError):
    """Raised when a prompt matches a known jailbreak pattern."""

    def __init__(self, message: str, *, matched_patterns: Sequence[str]) -> None:
        super().__init__(message)
        self.matched_patterns: list[str] = list(matched_patterns)


class PromptTooLongError(ArmorError):
    """Raised when a prompt exceeds the configured character budget."""


class CompletionTooLongError(ArmorError):
    """Raised when a completion exceeds the configured character budget."""


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SanitisedPrompt:
    """The output of :meth:`ModelArmor.sanitise_input`.

    Attributes:
        text: The redacted + validated prompt text.
        pii_redactions: The count of PII tokens redacted.
        injected_chars_removed: The count of characters removed by
            the zero-width-smuggling strip.
        matched_patterns: The patterns that matched (empty when clean).
    """

    text: str
    pii_redactions: int = 0
    injected_chars_removed: int = 0
    matched_patterns: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SanitisedCompletion:
    """The output of :meth:`ModelArmor.sanitise_output`.

    Attributes:
        text: The sanitised completion text.
        truncated: Whether the output was truncated to the budget.
        stripped_tags: The tags stripped from the output
            (e.g. ``"<system>"`` blocks).
    """

    text: str
    truncated: bool = False
    stripped_tags: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# The ModelArmor class
# ---------------------------------------------------------------------------


class ModelArmor:
    """The fleet-wide input/output validation layer.

    Construct once at process start; every :func:`call_llm` call
    should route its messages through :meth:`sanitise_input` and
    every response through :meth:`sanitise_output`.

    The class is configured with conservative defaults; pass
    ``strict=True`` to :meth:`sanitise_input` to reject any
    matched pattern as :class:`PromptInjectionError` /
    :class:`JailbreakError`.
    """

    def __init__(
        self,
        *,
        max_prompt_chars: int = DEFAULT_MAX_PROMPT_CHARS,
        max_completion_chars: int = DEFAULT_MAX_COMPLETION_CHARS,
        redact_pii: bool = True,
        reject_injections: bool = False,
        reject_jailbreaks: bool = False,
    ) -> None:
        """Initialise the armor layer.

        Args:
            max_prompt_chars: The maximum input prompt length
                (default 50 000).
            max_completion_chars: The maximum output length
                (default 16 000).
            redact_pii: Whether to redact PII patterns in input.
            reject_injections: Whether to reject input that matches
                known injection patterns.
            reject_jailbreaks: Whether to reject input that matches
                known jailbreak patterns.
        """
        self.max_prompt_chars = max_prompt_chars
        self.max_completion_chars = max_completion_chars
        self.redact_pii = redact_pii
        self.reject_injections = reject_injections
        self.reject_jailbreaks = reject_jailbreaks

    # ------------------------------------------------------------------
    # Input sanitisation
    # ------------------------------------------------------------------

    def sanitise_input(self, text: str, *, strict: bool | None = None) -> SanitisedPrompt:
        """Sanitise a user-supplied prompt before it reaches :func:`call_llm`.

        Performs, in order:

        1. Length check — reject if ``len(text) > max_prompt_chars``.
        2. Zero-width-smuggling strip — remove Unicode bidi + zero-width
           controls that can hide injection tokens.
        3. Prompt-injection scan — match against :data:`INJECTION_PATTERNS`.
        4. Jailbreak scan — match against :data:`JAILBREAK_PATTERNS`.
        5. PII redaction — replace emails / phones / PPS / NINo with
           ``[REDACTED:<type>]``.

        Args:
            text: The raw user-supplied text.
            strict: Override the constructor-level
                ``reject_injections`` / ``reject_jailbreaks`` flags
                (``None`` = use the constructor defaults).

        Returns:
            A :class:`SanitisedPrompt` with the cleaned text + counts.

        Raises:
            PromptTooLongError: If ``len(text) > max_prompt_chars``.
            PromptInjectionError: If a known injection matches AND
                ``reject_injections`` is True (or ``strict=True``).
            JailbreakError: If a known jailbreak matches AND
                ``reject_jailbreaks`` is True (or ``strict=True``).
        """
        if len(text) > self.max_prompt_chars:
            raise PromptTooLongError(
                f"Prompt length {len(text)} > max_prompt_chars "
                f"{self.max_prompt_chars}"
            )

        reject_inj = self.reject_injections if strict is None else strict
        reject_jb = self.reject_jailbreaks if strict is None else strict

        # 1. Zero-width + bidi control strip.
        cleaned, injected_count = _strip_zero_width(text)

        # 2. Injection scan.
        injection_hits = [p.pattern for p in INJECTION_PATTERNS if p.search(cleaned)]
        if injection_hits and reject_inj:
            logger.warning(
                "armor.prompt_injection_detected",
                matched=injection_hits,
            )
            raise PromptInjectionError(
                f"Prompt matches {len(injection_hits)} injection pattern(s); "
                f"see matched_patterns for details.",
                matched_patterns=injection_hits,
            )

        # 3. Jailbreak scan.
        jailbreak_hits = [p.pattern for p in JAILBREAK_PATTERNS if p.search(cleaned)]
        if jailbreak_hits and reject_jb:
            logger.warning(
                "armor.jailbreak_detected",
                matched=jailbreak_hits,
            )
            raise JailbreakError(
                f"Prompt matches {len(jailbreak_hits)} jailbreak pattern(s); "
                f"see matched_patterns for details.",
                matched_patterns=jailbreak_hits,
            )

        # 4. PII redaction (always counted; only applied if redact_pii=True).
        pii_redactions = 0
        if self.redact_pii:
            cleaned, pii_redactions = _redact_pii(cleaned)

        matched = tuple(injection_hits + jailbreak_hits)
        if matched:
            logger.info(
                "armor.prompt_patrolled",
                matched_count=len(matched),
                pii_redactions=pii_redactions,
            )

        return SanitisedPrompt(
            text=cleaned,
            pii_redactions=pii_redactions,
            injected_chars_removed=injected_count,
            matched_patterns=matched,
        )

    # ------------------------------------------------------------------
    # Output sanitisation
    # ------------------------------------------------------------------

    def sanitise_output(self, text: str) -> SanitisedCompletion:
        """Sanitise a model completion before it reaches the user.

        Performs, in order:

        1. Length check — truncate if ``len(text) > max_completion_chars``.
        2. Strip ``<system>`` / ``<assistant>`` / ``<user>`` tags
           that could be smuggled back into the user-facing stream.
        3. Strip residual HTML comment smuggling.

        Args:
            text: The raw model completion text.

        Returns:
            A :class:`SanitisedCompletion` with the cleaned text +
            metadata.
        """
        stripped: list[str] = []

        # 1. Length cap.
        truncated = False
        if len(text) > self.max_completion_chars:
            text = text[: self.max_completion_chars] + "…[truncated]"
            truncated = True
            stripped.append("truncation")

        # 2. Strip smuggled role tags.
        cleaned = text
        for tag in ("system", "assistant", "user", "tool"):
            pattern = re.compile(
                rf"</?{tag}(?:\s[^>]*)?>", re.IGNORECASE
            )
            if pattern.search(cleaned):
                stripped.append(tag)
                cleaned = pattern.sub("", cleaned)

        # 3. Strip residual HTML comments.
        comment_pattern = re.compile(r"<!--.*?-->", re.DOTALL)
        if comment_pattern.search(cleaned):
            stripped.append("html_comment")
            cleaned = comment_pattern.sub("", cleaned)

        if stripped:
            logger.info(
                "armor.completion_sanitised",
                stripped_tags=stripped,
                truncated=truncated,
            )

        return SanitisedCompletion(
            text=cleaned.strip(),
            truncated=truncated,
            stripped_tags=tuple(stripped),
        )

    # ------------------------------------------------------------------
    # Convenience: full message-list sanitisation
    # ------------------------------------------------------------------

    def sanitise_messages(
        self, messages: Sequence[dict[str, Any]], *, strict: bool | None = None
    ) -> list[dict[str, Any]]:
        """Sanitise a full message list (system + user + assistant turns).

        The system + assistant messages are passed through
        :meth:`sanitise_output` (defense against smuggled tags); the
        user messages are passed through :meth:`sanitise_input`.

        Args:
            messages: The OpenAI-compatible message list.
            strict: Override for ``strict`` in
                :meth:`sanitise_input`.

        Returns:
            A new sanitised message list.
        """
        out: list[dict[str, Any]] = []
        for msg in messages:
            role = msg.get("role", "user")
            content = str(msg.get("content", ""))
            if role in {"user"}:
                sanitised = self.sanitise_input(content, strict=strict)
                out.append({"role": role, "content": sanitised.text})
            else:
                sanitised = self.sanitise_output(content)
                out.append({"role": role, "content": sanitised.text})
        return out


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _strip_zero_width(text: str) -> tuple[str, int]:
    """Strip zero-width Unicode + bidi controls from ``text``.

    Args:
        text: The raw text.

    Returns:
        A 2-tuple ``(cleaned_text, characters_removed)``.
    """
    pattern = re.compile(r"[\u200b\u200c\u200d\u2060\u202a-\u202e\u2066-\u2069]")
    matches = pattern.findall(text)
    return pattern.sub("", text), len(matches)


def _redact_pii(text: str) -> tuple[str, int]:
    """Replace PII patterns with ``[REDACTED:<type>]`` tokens.

    Args:
        text: The raw text.

    Returns:
        A 2-tuple ``(cleaned_text, redaction_count)``.
    """
    redactions = 0
    for pattern, label in (
        (PII_PATTERNS[0], "email"),
        (PII_PATTERNS[1], "phone"),
        (PII_PATTERNS[2], "pps"),
        (PII_PATTERNS[3], "nino"),
    ):
        new_text, count = pattern.subn(f"[REDACTED:{label}]", text)
        text = new_text
        redactions += count
    return text, redactions


# ---------------------------------------------------------------------------
# Public exports
# ---------------------------------------------------------------------------

__all__ = [
    "ArmorError",
    "DEFAULT_MAX_COMPLETION_CHARS",
    "DEFAULT_MAX_PROMPT_CHARS",
    "INJECTION_PATTERNS",
    "JAILBREAK_PATTERNS",
    "JailbreakError",
    "ModelArmor",
    "PII_PATTERNS",
    "PromptInjectionError",
    "PromptTooLongError",
    "CompletionTooLongError",
    "SanitisedCompletion",
    "SanitisedPrompt",
]
