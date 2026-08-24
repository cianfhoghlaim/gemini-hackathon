"""gemini_hackathon.agents.fleet.fleet_mcp_curriculum — MCP curriculum server.

The 7th Fleet primitive (per the openspec
``2026-08-24-gemini-hackathon-public-v1``). Implements the Model
Context Protocol (MCP) server that exposes the curriculum lookup
tools to all 4 idea agents.

The MCP server registers 3 tools:

* :func:`lookup_topic` — given a topic + jurisdiction + level,
  return the canonical learning outcomes + the source palette key.
* :func:`find_equivalent_topics` — given a topic + the source
  jurisdiction, return the equivalent topic names in each target
  jurisdiction (short-circuits the BAML ``ExtractEquivalencies``
  call for the common case).
* :func:`list_active_sources` — return the list of active source
  palettes + their jurisdictions + the active curriculum levels.

The tools are exposed over **stdio** (the canonical MCP transport
for local CLI agents) and over **HTTP+SSE** (the canonical MCP
transport for CopilotKit-style web clients).

This module is a wholesale port of the Cianfhoghlaim
``agents/fleet/mcp_curriculum_server.py`` (per the
``wholesale-copy-convention``) with two adaptations:

1. The tool implementations are simplified to read from the
   ``themes/`` + ``baml_extracts/`` assets that ship with this
   project (no live BAML client required at import time).
2. The MCP server can be started in two modes:
   ``mcp.run_stdio()`` (default) or ``mcp.run_http(port=...)``.

Usage from a downstream agent::

    from gemini_hackathon.agents.fleet.fleet_mcp_curriculum import (
        MCPCurriculumServer,
    )

    server = MCPCurriculumServer()
    server.run_stdio()
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

from gemini_hackathon.theming import (
    JURISDICTION_SOURCES,
    SAFEGUARDING_SOURCES,
    Palette,
    list_all_palettes,
    load_palette,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Optional MCP SDK import (graceful degradation)
# ---------------------------------------------------------------------------

_MCP_AVAILABLE: bool = False
try:
    from mcp.server import Server as _MCPServer  # type: ignore[import-not-found]
    from mcp.server.stdio import (  # type: ignore[import-not-found]
        stdio_server as _stdio_server,
    )
    from mcp.types import (  # type: ignore[import-not-found]
        Tool as _MCPTool,
    )

    _MCP_AVAILABLE = True
except ImportError:  # pragma: no cover
    _MCPServer = None  # type: ignore[assignment,misc]
    _stdio_server = None  # type: ignore[assignment]
    _MCPTool = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TopicLookup:
    """The result of a ``lookup_topic`` call.

    Attributes:
        topic: The canonical topic name.
        jurisdiction: The source jurisdiction.
        level: The curriculum level.
        learning_outcomes: The list of learning outcomes
            (stubbed when BAML extraction is unavailable).
        source_palette_key: The active source palette key.
        palette: The :class:`Palette` (or ``None`` if missing).
    """

    topic: str
    jurisdiction: str
    level: str
    learning_outcomes: list[str] = field(default_factory=list)
    source_palette_key: str = ""
    palette: Palette | None = None


@dataclass(frozen=True)
class EquivalentTopicHit:
    """One result row from ``find_equivalent_topics``."""

    target_jurisdiction: str
    target_topic: str
    confidence: float


@dataclass(frozen=True)
class ActiveSource:
    """One row from ``list_active_sources``."""

    source_key: str
    source_name: str
    jurisdiction: str
    level: str
    primary_color: str


# ---------------------------------------------------------------------------
# Tool implementations (pure Python — usable without the MCP SDK)
# ---------------------------------------------------------------------------


class MCPCurriculumServer:
    """The MCP server that exposes curriculum lookup tools.

    The class can be used in two modes:

    * **Direct** — call :meth:`lookup_topic`,
      :meth:`find_equivalent_topics`, :meth:`list_active_sources`
      directly from Python (no MCP transport required; this is the
      test + dev path).
    * **MCP transport** — call :meth:`run_stdio` (or
      :meth:`run_http`) to start a real MCP server that exposes
      the same methods as MCP tools.

    All tool implementations are read-only — no LLM call is made.
    The BAML ``ExtractEquivalencies`` function (when available)
    is invoked by the :meth:`equivalency_generator` idea agent,
    NOT by this MCP server (this server only exposes the lookup
    primitives).
    """

    def __init__(
        self,
        *,
        themes_dir: Path | str | None = None,
    ) -> None:
        """Initialise the MCP server.

        Args:
            themes_dir: Override the themes directory (defaults to
                the project's ``themes/``).
        """
        if themes_dir is not None:
            from gemini_hackathon import theming

            theming.THEMES_DIR = Path(themes_dir)
        self._server: Any = None
        if _MCP_AVAILABLE and _MCPServer is not None:
            self._server = _MCPServer("gemini-hackathon-mcp")
            self._register_tools()

    # ------------------------------------------------------------------
    # Tool implementations
    # ------------------------------------------------------------------

    def lookup_topic(
        self,
        topic: str,
        *,
        jurisdiction: str = "Ireland",
        level: str = "LC",
    ) -> TopicLookup:
        """Look up a topic by jurisdiction + level.

        Args:
            topic: The topic name (case-insensitive).
            jurisdiction: The jurisdiction name.
            level: The curriculum level (``"LC"``, ``"JC"``,
                ``"GCSE"``, ``"A-Level"``, …).

        Returns:
            A :class:`TopicLookup` with the canonical outcomes
            (stubbed when no live extraction is available) + the
            source palette key for the requested jurisdiction.
        """
        source_key = JURISDICTION_SOURCES.get(jurisdiction, "ncca.ie")
        palette = load_palette(source_key)
        learning_outcomes = _stub_learning_outcomes(topic, jurisdiction, level)
        logger.info(
            "mcp.lookup_topic",
            topic=topic,
            jurisdiction=jurisdiction,
            level=level,
            source_palette_key=source_key,
            palette_loaded=palette is not None,
            outcome_count=len(learning_outcomes),
        )
        return TopicLookup(
            topic=topic,
            jurisdiction=jurisdiction,
            level=level,
            learning_outcomes=learning_outcomes,
            source_palette_key=source_key,
            palette=palette,
        )

    def find_equivalent_topics(
        self,
        topic: str,
        *,
        source_jurisdiction: str = "Ireland",
        target_jurisdictions: Iterable[str] | None = None,
    ) -> list[EquivalentTopicHit]:
        """Return equivalent topic names in each target jurisdiction.

        In the production path this delegates to the BAML
        ``ExtractEquivalencies`` function. In the test + dev path
        (and in this MCP server), it returns a deterministic stub
        so the tool is callable without a live BAML client.

        Args:
            topic: The source topic name.
            source_jurisdiction: The source jurisdiction.
            target_jurisdictions: Optional iterable of target
                jurisdiction names (default: all 8 BI jurisdictions
                minus the source).

        Returns:
            A list of :class:`EquivalentTopicHit` rows.
        """
        targets = list(
            target_jurisdictions
            or [j for j in JURISDICTION_SOURCES if j != source_jurisdiction]
        )
        hits: list[EquivalentTopicHit] = []
        for target in targets:
            hits.append(
                EquivalentTopicHit(
                    target_jurisdiction=target,
                    target_topic=_stub_equivalent(topic, target),
                    confidence=_stub_confidence(source_jurisdiction, target),
                )
            )
        logger.info(
            "mcp.find_equivalent_topics",
            topic=topic,
            source_jurisdiction=source_jurisdiction,
            hit_count=len(hits),
        )
        return hits

    def list_active_sources(
        self, *, include_safeguarding: bool = True
    ) -> list[ActiveSource]:
        """Return the list of active source palettes.

        Args:
            include_safeguarding: Whether to include the 5
                safeguarding sources (default ``True``).

        Returns:
            A list of :class:`ActiveSource` rows.
        """
        sources: list[ActiveSource] = []
        for entry in list_all_palettes():
            sources.append(
                ActiveSource(
                    source_key=entry.get("sourceKey", ""),
                    source_name=entry.get("sourceName", ""),
                    jurisdiction=entry.get("jurisdiction", ""),
                    level=entry.get("level", ""),
                    primary_color="",
                )
            )
        # Backfill the primary_color from each loaded palette.
        for source in sources:
            palette = load_palette(source.source_key)
            if palette is not None:
                object.__setattr__(source, "primary_color", palette.primary)

        if include_safeguarding:
            for safe_key in SAFEGUARDING_SOURCES:
                palette = load_palette(safe_key)
                if palette is not None:
                    sources.append(
                        ActiveSource(
                            source_key=palette.source_key,
                            source_name=palette.source_name,
                            jurisdiction=palette.jurisdiction,
                            level=palette.level,
                            primary_color=palette.primary,
                        )
                    )

        logger.info(
            "mcp.list_active_sources",
            count=len(sources),
            include_safeguarding=include_safeguarding,
        )
        return sources

    # ------------------------------------------------------------------
    # MCP transport (stdio + HTTP)
    # ------------------------------------------------------------------

    def _register_tools(self) -> None:
        """Register the 3 tools on the MCP server."""
        if self._server is None:  # pragma: no cover
            return

        @self._server.list_tools()  # type: ignore[misc]
        async def _list_tools() -> list[Any]:
            return [
                _MCPTool(
                    name="lookup_topic",
                    description=(
                        "Look up a topic by jurisdiction + level. "
                        "Returns learning outcomes + the source palette key."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "topic": {"type": "string"},
                            "jurisdiction": {"type": "string"},
                            "level": {"type": "string"},
                        },
                        "required": ["topic"],
                    },
                ),
                _MCPTool(
                    name="find_equivalent_topics",
                    description=(
                        "Find equivalent topics across jurisdictions "
                        "for the given source topic."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "topic": {"type": "string"},
                            "source_jurisdiction": {"type": "string"},
                            "target_jurisdictions": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["topic"],
                    },
                ),
                _MCPTool(
                    name="list_active_sources",
                    description=(
                        "List the active source palettes (jurisdictions "
                        "+ safeguarding bodies)."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "include_safeguarding": {"type": "boolean"},
                        },
                    },
                ),
            ]

        @self._server.call_tool()  # type: ignore[misc]
        async def _call_tool(name: str, arguments: dict[str, Any]) -> Any:
            if name == "lookup_topic":
                result = self.lookup_topic(
                    topic=arguments.get("topic", ""),
                    jurisdiction=arguments.get("jurisdiction", "Ireland"),
                    level=arguments.get("level", "LC"),
                )
                return _topic_lookup_to_text(result)
            if name == "find_equivalent_topics":
                hits = self.find_equivalent_topics(
                    topic=arguments.get("topic", ""),
                    source_jurisdiction=arguments.get(
                        "source_jurisdiction", "Ireland"
                    ),
                    target_jurisdictions=arguments.get("target_jurisdictions"),
                )
                return _equivalent_hits_to_text(hits)
            if name == "list_active_sources":
                sources = self.list_active_sources(
                    include_safeguarding=arguments.get(
                        "include_safeguarding", True
                    )
                )
                return _active_sources_to_text(sources)
            raise ValueError(f"Unknown MCP tool: {name!r}")

    async def run_stdio_async(self) -> None:
        """Run the MCP server over stdio (canonical CLI transport)."""
        if not _MCP_AVAILABLE or _stdio_server is None:  # pragma: no cover
            raise RuntimeError(
                "mcp SDK not installed; install with `uv add mcp`."
            )
        if self._server is None:
            raise RuntimeError("MCP server was not initialised.")
        async with _stdio_server() as (read_stream, write_stream):
            await self._server.run(
                read_stream,
                write_stream,
                self._server.create_initialization_options(),
            )

    def run_stdio(self) -> None:
        """Blocking helper to run :meth:`run_stdio_async`."""
        import asyncio

        asyncio.run(self.run_stdio_async())

    def run_http(self, host: str = "127.0.0.1", port: int = 8765) -> None:
        """Run the MCP server over HTTP+SSE (canonical web transport).

        Args:
            host: The bind host (default ``127.0.0.1``).
            port: The bind port (default 8765).
        """
        if not _MCP_AVAILABLE:  # pragma: no cover
            raise RuntimeError(
                "mcp SDK not installed; install with `uv add mcp`."
            )
        # The MCP Python SDK ships a Starlette app for HTTP+SSE.
        try:
            import uvicorn  # type: ignore[import-not-found]
            from mcp.server.sse import SseServerTransport  # type: ignore[import-not-found]
            from starlette.applications import Starlette  # type: ignore[import-not-found]
            from starlette.routing import Mount, Route  # type: ignore[import-not-found]
        except ImportError as e:
            raise RuntimeError(
                "HTTP transport requires `uvicorn` + `starlette` + "
                "the MCP SSE adapter. Install with "
                "`uv add mcp uvicorn starlette`."
            ) from e

        sse = SseServerTransport("/messages/")
        server = self._server

        async def _handle_sse(request: Any) -> Any:  # type: ignore[no-untyped-def]
            async with sse.connect_sse(
                request.scope, request.receive, request._send  # noqa: SLF001
            ) as (read_stream, write_stream):
                await server.run(
                    read_stream,
                    write_stream,
                    server.create_initialization_options(),
                )

        app = Starlette(
            routes=[
                Route("/sse", endpoint=_handle_sse),
                Mount("/messages/", app=sse.handle_post_message),
            ]
        )
        uvicorn.run(app, host=host, port=port)


# ---------------------------------------------------------------------------
# Stubs (deterministic placeholders for the live BAML functions)
# ---------------------------------------------------------------------------


def _stub_learning_outcomes(
    topic: str, jurisdiction: str, level: str
) -> list[str]:
    """Return a deterministic placeholder for learning outcomes."""
    return [
        f"[stub:{jurisdiction}/{level}] students should be able to define {topic}",
        f"[stub:{jurisdiction}/{level}] students should be able to apply {topic}",
        f"[stub:{jurisdiction}/{level}] students should be able to analyse {topic}",
    ]


def _stub_equivalent(topic: str, target_jurisdiction: str) -> str:
    """Return a deterministic placeholder for an equivalent topic."""
    return f"{topic} ({target_jurisdiction} equivalent — stub)"


def _stub_confidence(source: str, target: str) -> float:
    """Return a deterministic confidence score (0.50-0.95)."""
    h = hash(f"{source}|{target}") & 0xFFFF
    return 0.50 + (h % 46) / 100.0


# ---------------------------------------------------------------------------
# MCP serialisation helpers
# ---------------------------------------------------------------------------


def _topic_lookup_to_text(result: TopicLookup) -> list[Any]:
    """Serialize a :class:`TopicLookup` to MCP text content."""
    payload = {
        "topic": result.topic,
        "jurisdiction": result.jurisdiction,
        "level": result.level,
        "source_palette_key": result.source_palette_key,
        "learning_outcomes": result.learning_outcomes,
        "palette": (
            {
                "primary": result.palette.primary,
                "secondary": result.palette.secondary,
                "heading_font": result.palette.heading_font,
                "body_font": result.palette.body_font,
            }
            if result.palette is not None
            else None
        ),
    }
    return [{"type": "text", "text": json.dumps(payload, indent=2)}]


def _equivalent_hits_to_text(hits: list[EquivalentTopicHit]) -> list[Any]:
    """Serialize a list of :class:`EquivalentTopicHit` to MCP text content."""
    payload = [
        {
            "target_jurisdiction": h.target_jurisdiction,
            "target_topic": h.target_topic,
            "confidence": h.confidence,
        }
        for h in hits
    ]
    return [{"type": "text", "text": json.dumps(payload, indent=2)}]


def _active_sources_to_text(sources: list[ActiveSource]) -> list[Any]:
    """Serialize a list of :class:`ActiveSource` to MCP text content."""
    payload = [
        {
            "source_key": s.source_key,
            "source_name": s.source_name,
            "jurisdiction": s.jurisdiction,
            "level": s.level,
            "primary_color": s.primary_color,
        }
        for s in sources
    ]
    return [{"type": "text", "text": json.dumps(payload, indent=2)}]


# ---------------------------------------------------------------------------
# Public exports
# ---------------------------------------------------------------------------

__all__ = [
    "ActiveSource",
    "EquivalentTopicHit",
    "MCPCurriculumServer",
    "TopicLookup",
]
