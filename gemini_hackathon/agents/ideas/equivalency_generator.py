"""gemini_hackathon.agents.ideas.equivalency_generator — cross-jurisdiction mapping.

The Equivalency Generator is one of the 4 idea agents in the
gemini_hackathon fleet (per the openspec change
``2026-08-24-gemini-hackathon-public-v1``). Given an NCCA Leaving
Certificate topic, it produces the canonical equivalent topic
names in each of the other 7 British Isles jurisdictions:

* England (AQA / OCR / Pearson)
* Scotland (SQA — National 5 / Higher / Advanced Higher)
* Wales (WJEC / CBAC)
* Northern Ireland (CCEA)
* Isle of Man (IoM Government Education Service)

The agent is the canonical Python wrapper around the BAML
``ExtractEquivalencies`` function (see
``baml_extracts/extract_equivalency.baml``). When a live BAML
client is available, the wrapper delegates the heavy lifting to
the BAML function; otherwise it returns a deterministic stub so
the rest of the fleet can be exercised in tests + CI.

The agent always uses the canonical :func:`gemini_hackathon.call_llm`
entrypoint (the 3-tier model policy) and the
:func:`gemini_hackathon.theming.load_palette` function to render
each target jurisdiction's brand identity on the result rows.

Wholesale port of the Cianfhoghlaim
``agents/adk/curriculum_comparison_agent.py`` (per the
``wholesale-copy-convention``) — adapted from the
``LlmAgent`` factory to a plain Python class.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import structlog

from gemini_hackathon.call_llm import LLMResponse, Message, call_llm
from gemini_hackathon.theming import Palette, load_palette

from ..fleet.fleet_identity import IdentityContext
from ..fleet.fleet_mcp_curriculum import MCPCurriculumServer
from ..fleet.fleet_observability import Observability, TraceContext

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Constants — the canonical 8 BI jurisdictions
# ---------------------------------------------------------------------------

#: The 7 target jurisdictions (the 8 British Isles jurisdictions
#: minus the source jurisdiction, which is computed per request).
ALL_TARGET_JURISDICTIONS: tuple[str, ...] = (
    "England",
    "Scotland",
    "Wales",
    "Northern Ireland",
    "Isle of Man",
)

#: Map of jurisdiction → awarding body string (for the prompt).
JURISDICTION_AWARDING_BODY: dict[str, str] = {
    "Ireland": "NCCA",
    "England": "AQA / OCR / Pearson Edexcel",
    "Scotland": "SQA",
    "Wales": "WJEC / CBAC",
    "Northern Ireland": "CCEA",
    "Isle of Man": "IoM Government Education Service",
}


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EquivalencyRequest:
    """The input envelope for an equivalency lookup.

    Attributes:
        topic: The source topic name.
        source_jurisdiction: The source jurisdiction (default
            ``"Ireland"`` — the canonical NCCA LC source).
        target_jurisdictions: Optional iterable of target
            jurisdictions (default: all 5 other BI jurisdictions).
        subject: The optional subject name (e.g. ``"Mathematics"``).
        identity: The resolved :class:`IdentityContext`.
    """

    topic: str
    source_jurisdiction: str = "Ireland"
    target_jurisdictions: Sequence[str] = ()
    subject: str = ""
    identity: IdentityContext | None = None


@dataclass(frozen=True)
class EquivalencyRow:
    """One row of the equivalency result table.

    Attributes:
        target_jurisdiction: The target jurisdiction name.
        target_topic: The equivalent topic name (empty string when
            no equivalent exists).
        awarding_body: The awarding body for the target jurisdiction.
        confidence: The mapping confidence in [0.0, 1.0].
        palette: The :class:`Palette` for the target jurisdiction
            (or ``None`` if the palette file is missing).
        notes: Optional caveat from the BAML extraction.
    """

    target_jurisdiction: str
    target_topic: str
    awarding_body: str
    confidence: float
    palette: Palette | None = None
    notes: str = ""


@dataclass(frozen=True)
class EquivalencyResult:
    """The full output of an equivalency lookup.

    Attributes:
        source_topic: The source topic name.
        source_jurisdiction: The source jurisdiction.
        subject: The subject (echoed back).
        rows: The list of :class:`EquivalencyRow` results.
        llm_response: The underlying :class:`LLMResponse`.
        trace_id: The observability trace ID.
    """

    source_topic: str
    source_jurisdiction: str
    subject: str
    rows: list[EquivalencyRow]
    llm_response: LLMResponse
    trace_id: str


# ---------------------------------------------------------------------------
# The EquivalencyGenerator agent
# ---------------------------------------------------------------------------


class EquivalencyGenerator:
    """The Cross-Jurisdiction Equivalency Generator idea agent.

    Constructed once at process start and registered with the
    :class:`FleetGateway`. The :meth:`invoke` method is the
    canonical entrypoint for the gateway's keyword router.
    """

    def __init__(
        self,
        *,
        mcp_server: MCPCurriculumServer | None = None,
        observability: Observability | None = None,
        baml_client: Any | None = None,
    ) -> None:
        """Initialise the generator.

        Args:
            mcp_server: The :class:`MCPCurriculumServer` (default:
                a fresh instance).
            observability: The :class:`Observability` (default: a
                fresh instance).
            baml_client: Optional BAML client. When supplied, the
                agent delegates the heavy lifting to
                ``baml_client.ExtractEquivalencies(...)``; otherwise
                it falls back to calling :func:`call_llm` with the
                canonical prompt + JSON parsing.
        """
        self.mcp_server = mcp_server or MCPCurriculumServer()
        self.observability = observability or Observability()
        self.baml_client = baml_client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def invoke(
        self,
        request: EquivalencyRequest,
        *,
        trace: TraceContext | None = None,
    ) -> EquivalencyResult:
        """Run the equivalency lookup for one source topic.

        Args:
            request: The :class:`EquivalencyRequest` envelope.
            trace: Optional pre-existing observability trace
                (default: the generator opens its own).

        Returns:
            The :class:`EquivalencyResult` envelope.
        """
        identity = request.identity or IdentityContext()
        target_jurisdictions = list(
            request.target_jurisdictions
            or [j for j in ALL_TARGET_JURISDICTIONS if j != request.source_jurisdiction]
        )

        # Open the trace.
        if trace is None:
            cm = self.observability.trace(
                agent="equivalency_generator",
                user_id=identity.user_id,
                metadata={
                    "topic": request.topic,
                    "source_jurisdiction": request.source_jurisdiction,
                    "target_jurisdictions": target_jurisdictions,
                    "subject": request.subject,
                },
            )
            trace = cm.__enter__()  # capture the yielded TraceContext
            close_cm = cm
        else:
            close_cm = None

        try:
            # Try the live BAML client first.
            raw_equivalents: dict[str, str] = {}
            confidence: dict[str, float] = {}
            notes_map: dict[str, str] = {}
            if self.baml_client is not None:
                raw_equivalents, confidence, notes_map = self._call_baml(request)
                llm_response = _make_fake_response(trace.trace_id)
            else:
                messages = self._build_messages(request)
                llm_response = call_llm(
                    messages=messages,
                    metadata={
                        "trace_id": trace.trace_id,
                        "agent": "equivalency_generator",
                        "user_id": identity.user_id,
                    },
                )
                raw_equivalents, confidence, notes_map = _parse_llm_response(
                    llm_response.content
                )

            self.observability.record_invocation(trace, llm_response)

            # Build the result rows.
            rows: list[EquivalencyRow] = []
            for target in target_jurisdictions:
                topic_name = raw_equivalents.get(target, "")
                rows.append(
                    EquivalencyRow(
                        target_jurisdiction=target,
                        target_topic=topic_name,
                        awarding_body=JURISDICTION_AWARDING_BODY.get(target, ""),
                        confidence=confidence.get(target, 0.0),
                        palette=load_palette(_palette_key_for(target)),
                        notes=notes_map.get(target, ""),
                    )
                )

            return EquivalencyResult(
                source_topic=request.topic,
                source_jurisdiction=request.source_jurisdiction,
                subject=request.subject,
                rows=rows,
                llm_response=llm_response,
                trace_id=trace.trace_id,
            )
        finally:
            if close_cm is not None:
                close_cm.__exit__(None, None, None)

    def as_gateway_invoker(
        self,
        *,
        sanitised_input: Any,
        identity: IdentityContext,
        trace: TraceContext,
    ) -> list[Message]:
        """Adapter that produces the message list for the gateway.

        Args:
            sanitised_input: The :class:`SanitisedPrompt`.
            identity: The :class:`IdentityContext`.
            trace: The :class:`TraceContext`.

        Returns:
            The message list to send to :func:`call_llm`.
        """
        # Parse the topic + target jurisdictions out of the
        # sanitised question text. The gateway keyword router has
        # already classified the agent (this is the right one),
        # so we just need to extract the payload.
        text = sanitised_input.text
        topic = _extract_topic(text, identity)
        targets = _extract_targets(text)
        request = EquivalencyRequest(
            topic=topic,
            source_jurisdiction=identity.jurisdiction,
            target_jurisdictions=targets,
            identity=identity,
        )
        trace.metadata["resolved_topic"] = topic
        trace.metadata["target_jurisdictions"] = targets
        return self._build_messages(request)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _call_baml(
        self, request: EquivalencyRequest
    ) -> tuple[dict[str, str], dict[str, float], dict[str, str]]:
        """Delegate to the BAML client (when available)."""
        try:
            result = self.baml_client.ExtractEquivalencies(  # type: ignore[attr-defined]
                topic=request.topic,
                source_jurisdiction=request.source_jurisdiction,
                target_jurisdictions=list(request.target_jurisdictions),
            )
            equivalents: dict[str, str] = dict(result.equivalents or {})
            confidence = {target: float(result.confidence) for target in equivalents}
            notes_map = (
                {request.source_jurisdiction: result.notes}
                if getattr(result, "notes", None)
                else {}
            )
            return equivalents, confidence, notes_map
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "equivalency.baml_call_failed",
                error=f"{type(e).__name__}: {e}",
            )
            return {}, {}, {}

    def _build_messages(self, request: EquivalencyRequest) -> list[Message]:
        """Compose the message list for :func:`call_llm`."""
        targets = list(
            request.target_jurisdictions
            or [j for j in ALL_TARGET_JURISDICTIONS if j != request.source_jurisdiction]
        )
        targets_block = ", ".join(sorted(targets))

        system = (
            "You are the BIEP Cross-Jurisdiction Equivalency "
            "Generator. Given a topic in a source jurisdiction, "
            "produce the canonical equivalent topic name in each "
            "target jurisdiction. Be precise: only name the topic "
            "when an equivalent exists; otherwise return an empty "
            "string. Order the equivalents by alphabetical "
            "jurisdiction name. Score your confidence in [0.0, "
            "1.0]. Use these awarding-body mappings:\n\n"
            f"- Ireland           (NCCA)\n"
            f"- England           (AQA / OCR / Pearson)\n"
            f"- Scotland          (SQA)\n"
            f"- Wales             (WJEC / CBAC)\n"
            f"- Northern Ireland  (CCEA)\n"
            f"- Isle of Man       (IoM Government)\n\n"
            "Return ONLY valid JSON of the shape:\n"
            "{\n"
            '  "source_topic": "<source topic name>",\n'
            '  "source_jurisdiction": "<source jurisdiction>",\n'
            '  "subject": "<subject>",\n'
            '  "equivalents": {\n'
            '    "<jurisdiction>": "<equivalent topic or empty>"\n'
            "  },\n"
            '  "confidence": <float 0-1>,\n'
            '  "notes": "<optional caveat>"\n'
            "}\n\n"
            "Do not wrap the JSON in markdown fences."
        )
        user = (
            f"topic               : {request.topic}\n"
            f"source_jurisdiction : {request.source_jurisdiction}\n"
            f"target_jurisdictions: {targets_block}\n"
            f"subject             : {request.subject or '(unspecified)'}"
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _palette_key_for(jurisdiction: str) -> str:
    """Return the source palette key for the given jurisdiction."""
    return {
        "Ireland": "ncca.ie",
        "England": "aqa.org.uk",
        "Scotland": "sqa.org.uk",
        "Wales": "wjec.co.uk",
        "Northern Ireland": "ccea.org.uk",
        "Isle of Man": "gov.im/education",
    }.get(jurisdiction, "ncca.ie")


def _extract_topic(text: str, identity: IdentityContext) -> str:
    """Heuristic topic extractor."""
    # Strip common prefixes ("what is the equivalent of X in Y").
    for prefix in (
        "what is the equivalent of ",
        "what's the equivalent of ",
        "what is the equivalent topic of ",
        "equivalent of ",
        "equivalent topic of ",
    ):
        if text.lower().startswith(prefix):
            return text[len(prefix):].strip().rstrip("?.!").strip()
    return text.strip().rstrip("?.!").strip() or identity.jurisdiction


def _extract_targets(text: str) -> list[str]:
    """Heuristic target-jurisdiction extractor."""
    lowered = text.lower()
    found: list[str] = []
    for kw, jur in (
        ("aqa", "England"),
        ("ocr", "England"),
        ("pearson", "England"),
        ("england", "England"),
        ("sqa", "Scotland"),
        ("scotland", "Scotland"),
        ("highers", "Scotland"),
        ("wjec", "Wales"),
        ("cbac", "Wales"),
        ("wales", "Wales"),
        ("ccea", "Northern Ireland"),
        ("northern ireland", "Northern Ireland"),
        ("isle of man", "Isle of Man"),
        ("iom", "Isle of Man"),
    ):
        if kw in lowered and jur not in found:
            found.append(jur)
    return found


def _parse_llm_response(
    content: str,
) -> tuple[dict[str, str], dict[str, float], dict[str, str]]:
    """Best-effort parse of the LLM JSON response."""
    import json as _json

    try:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0]
        payload = _json.loads(cleaned)
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "equivalency.llm_json_parse_failed",
            error=f"{type(e).__name__}: {e}",
            content_preview=content[:120],
        )
        return {}, {}, {}
    equivalents = payload.get("equivalents", {}) or {}
    if not isinstance(equivalents, dict):
        return {}, {}, {}
    confidence_val = float(payload.get("confidence", 0.85) or 0.85)
    confidence = {jur: confidence_val for jur in equivalents}
    notes_map: dict[str, str] = {}
    if isinstance(payload.get("notes"), str) and payload["notes"]:
        notes_map["__global__"] = payload["notes"]
    return {str(k): str(v) for k, v in equivalents.items()}, confidence, notes_map


def _make_fake_response(trace_id: str) -> LLMResponse:
    """Construct a stub :class:`LLMResponse` for the BAML path.

    Args:
        trace_id: The observability trace ID (used for the
            ``model`` placeholder so the log event still tags
            the right run).

    Returns:
        A stub :class:`LLMResponse`.
    """
    from gemini_hackathon.call_llm import LLMResponse

    return LLMResponse(
        content="",
        model="baml-extract-equivalencies",
        tier=1,
        latency_ms=0,
        tokens_in=0,
        tokens_out=0,
        cost_usd=0.0,
        attempts=[],
    )


# ---------------------------------------------------------------------------
# Public exports
# ---------------------------------------------------------------------------

__all__ = [
    "ALL_TARGET_JURISDICTIONS",
    "EquivalencyGenerator",
    "EquivalencyRequest",
    "EquivalencyResult",
    "EquivalencyRow",
    "JURISDICTION_AWARDING_BODY",
    "build_default_generator",
    "generator_invoker",
]


# ---------------------------------------------------------------------------
# Convenience constructors
# ---------------------------------------------------------------------------


def build_default_generator() -> EquivalencyGenerator:
    """Construct a canonical :class:`EquivalencyGenerator` instance."""
    return EquivalencyGenerator()


def generator_invoker(
    generator: EquivalencyGenerator | None = None,
) -> Any:
    """Return a callable that adapts :class:`EquivalencyGenerator` for the gateway.

    Args:
        generator: Optional pre-built generator (default: a fresh
            :func:`build_default_generator` instance).

    Returns:
        A callable suitable for
        :meth:`FleetGateway.register_agent`.
    """
    _gen = generator or build_default_generator()
    return _gen.as_gateway_invoker
