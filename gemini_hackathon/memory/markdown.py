"""gemini_hackathon.memory.markdown — MarkdownMemoryService for per-user long-term memory.

Lifted verbatim from `monstertix/agent/concert/memory.py:MarkdownMemoryService`
(the 4th memory service option in the ADK 2 ecosystem — alongside
`InMemoryMemoryService`, `VertexAiRagMemoryService`, and
`VertexAiMemoryBankService`).

The MarkdownMemoryService stores memory as plain markdown files
(one per user). This is the simplest option, requires zero infrastructure,
and is perfect for the gemini_hackathon dev environment + HF Spaces.

For production, swap `MarkdownMemoryService` for `VertexAiMemoryBankService`
(no code changes required — both implement the `BaseMemoryService` 2-method
interface: `add_session_to_memory` + `search_memory`).

In gemini_hackathon, MarkdownMemoryService is consumed by:
  - The W7 ADK 2 stage coordinators (each session remembers the
    active subnation + role + the recent formative assessment exit cards)
  - The W9 skill-progression ledger (writes per-learner mastery events
    to memory before flushing to FalkorDB)
  - The W14 certificate pipeline (reads the per-learner mastery vector
    to populate the certificate)
"""

from __future__ import annotations

import hashlib
import os
import pathlib
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from google.adk.memory.base_memory_service import (
        BaseMemoryService,
        SearchMemoryResponse,
    )
    from google.adk.memory.memory_entry import MemoryEntry
    from google.adk.sessions import Session


# Module-level configurable path (per-user markdown files)
MEMORY_DIR: pathlib.Path = pathlib.Path(
    os.getenv("GH_MEMORY_DIR", "~/.gemini_hackathon/memory")
).expanduser()
MEMORY_USER: str = os.getenv("GH_MEMORY_USER", "userx")


def _memory_path(root: pathlib.Path, user_id: str, *, for_writing: bool = False) -> pathlib.Path:
    """Where this user's memory lives.

    Only creates the directory when something is about to be written.
    """
    if for_writing:
        root.mkdir(parents=True, exist_ok=True)
    return root / f"{user_id}.md"


class MarkdownMemoryService:
    """A memory service whose storage is a Markdown file per user.

    Not a scalable idea, and not the point. The point is that memory is
    an interface, the interface is small, and you can see the whole of
    your agent's long-term knowledge in a text editor.

    Implements:
      - `add_session_to_memory(session)` — ingest a conversation
      - `search_memory(app_name, user_id, query)` — hand memories back
    """

    def __init__(self, root: Optional[str | pathlib.Path] = None):
        self.root = pathlib.Path(root) if root else MEMORY_DIR

    async def add_session_to_memory(self, session: "Session") -> None:
        """Persist the session's transcript + state to the user's markdown file.

        The format is:
          # Session: <session_id> (<timestamp>)
          ## Events
          - user: <message>
          - agent: <message>
          ...
        """
        path = _memory_path(self.root, session.user_id, for_writing=True)
        lines: list[str] = [
            f"# Session: {session.id}",
            "",
        ]
        for event in session.events or []:
            content = getattr(event, "content", None)
            if content is None:
                continue
            role = getattr(content, "role", "agent")
            parts = getattr(content, "parts", []) or []
            for part in parts:
                text = getattr(part, "text", None)
                if text:
                    lines.append(f"- **{role}**: {text.strip()}")
            tool_calls = getattr(content, "parts", [])
            for part in parts:
                fc = getattr(part, "function_call", None)
                if fc:
                    lines.append(f"- **tool_call**: {fc.name}")
        with path.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n\n")

    async def search_memory(
        self,
        app_name: str,
        user_id: str,
        query: str,
    ) -> "SearchMemoryResponse":
        """Return memories matching the query (simple substring search).

        In production this would be a vector similarity search; for the
        gemini_hackathon dev environment a simple substring match is
        sufficient (the corpus is small + the 5 NCCA policy PDFs are
        already cited explicitly).
        """
        from google.adk.memory.memory_entry import MemoryEntry
        from google.adk.memory.base_memory_service import SearchMemoryResponse
        from google.genai import types as gtypes

        path = _memory_path(self.root, user_id, for_writing=False)
        if not path.exists():
            return SearchMemoryResponse(memories=[])

        query_lower = query.lower()
        matches: list[MemoryEntry] = []
        content = path.read_text(encoding="utf-8")
        for block in content.split("\n# Session:"):
            if not block.strip():
                continue
            if query_lower in block.lower():
                # MemoryEntry.content must be a google.genai.types.Content
                memory_content = gtypes.Content(
                    role="user",
                    parts=[gtypes.Part(text=block.strip())],
                )
                matches.append(
                    MemoryEntry(
                        id=hashlib.md5(block.encode()).hexdigest()[:16],
                        app_name=app_name,
                        user_id=user_id,
                        content=memory_content,
                    )
                )
        return SearchMemoryResponse(memories=matches)


__all__ = ["MarkdownMemoryService", "MEMORY_DIR", "MEMORY_USER"]
