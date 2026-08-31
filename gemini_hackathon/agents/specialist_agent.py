"""gemini_hackathon.agents.specialist_agent — the ADK 2 specialist agent scaffold.

Lifted from `cianfhoghlaim/docs/sruth/tuath/agents/adk/celtic_tutor.py`
(the canonical ADK 2 specialist scaffold).

Rewritten for the British Isles education theme: the `celtic_tutor_agent`
becomes the **generic subject specialist agent** (mathematics / english /
gaeilge / chemistry / physics / geography — one per NCCA subject).

This is a scaffold; the per-subject specialists are wired in W7
(ADK 2 stage coordinators). Each specialist:

  - Wraps a `google.adk.agents.LlmAgent`
  - Holds the per-subject BAML extraction tools (W5 + W7)
  - Exposes the per-subject MCP curriculum lookup tools (from
    `gemini_hackathon.agents.fleet.fleet_mcp_curriculum`)
  - Streams AG-UI events back to the editorial canvas (W12)

The myth/quest content from `sruth/tuath/agents/adk/{mythology_narrator,
quest_guide}` is NOT lifted — out of scope for the education system.
"""

from __future__ import annotations

from typing import Any

try:
    from google.adk.agents import LlmAgent
    from google.adk.tools import FunctionTool
except ImportError:
    LlmAgent = None  # type: ignore[assignment,misc]
    FunctionTool = None  # type: ignore[assignment,misc]


# The 14 NCCA LC subjects (the 14 specialists the W7 coordinators route to)
NCCA_LC_SUBJECTS: tuple[str, ...] = (
    "mathematics",
    "applied_mathematics",
    "chemistry",
    "geography",
    "history",
    "english",
    "gaeilge",
    "computer_science",
    "accounting",  # NCCA-adjacent
    "biology",  # NCCA-adjacent
    "business",  # NCCA-adjacent
    "french",  # NCCA-adjacent
    "irish_t2",  # NCCA-adjacent
    "physics",  # NCCA-adjacent
)


def build_specialist_agent(
    subject: str,
    *,
    model: str = "gemini-2.0-flash",
    baml_functions: list[Any] | None = None,
    mcp_tools: list[Any] | None = None,
    description: str | None = None,
    instruction: str | None = None,
) -> Any:
    """Build an ADK 2 specialist agent for one of the 14 NCCA LC subjects.

    Args:
        subject: One of NCCA_LC_SUBJECTS.
        model: The LLM model alias (default: gemini-2.0-flash).
        baml_functions: List of extracted BAML function refs to attach
            as tools. Default: empty (the coordinator wires the
            per-subject BAML functions in W7).
        mcp_tools: List of MCP tool refs (from
            `gemini_hackathon.agents.fleet.fleet_mcp_curriculum`).
            Default: empty.
        description: Optional description override.
        instruction: Optional instruction override.

    Returns:
        An `LlmAgent` configured for the subject. Returns None if
        google-adk is not installed (the canonical pattern from
        `adk2-tutorial` — the agents are importable without ADK for
        tests + dev environments).

    Raises:
        ValueError: If `subject` is not one of NCCA_LC_SUBJECTS.
    """
    if subject not in NCCA_LC_SUBJECTS:
        raise ValueError(f"Unknown subject {subject!r}; must be one of {NCCA_LC_SUBJECTS}")
    if LlmAgent is None:
        return None

    subj_desc = description or (
        f"Subject specialist for the NCCA {subject} Leaving Certificate "
        f"curriculum. Knows the active subnation's awarding-body "
        f"syllabus + the 5 NCCA policy documents (W2 corpus). "
        f"Routes learner questions to the right BAML extraction."
    )
    subj_instruction = instruction or (
        f"You are the {subject.title()} Subject Specialist for the "
        f"gemini_hackathon education system. You answer questions about "
        f"the NCCA {subject} LC curriculum, grounded in:\n"
        f"  - The 5 NCCA policy documents (data/ireland/ncca_policy/)\n"
        f"  - The {subject} syllabus (data/ireland/lc_subject/{subject}/)\n"
        f"  - The per-subject CocoIndex LanceDB table "
        f"(cianfhoghlaim.lc.{subject}.<level>_<lang>)\n"
        f"Always cite the source PDF + page when making a claim. "
        f"When asked about formative assessment, use the exit-card "
        f"BAML function (baml_extracts_education/player_assessment.baml)."
    )

    tools: list[Any] = []
    tools.extend(baml_functions or [])
    tools.extend(mcp_tools or [])

    return LlmAgent(
        name=f"{subject}_specialist",
        model=model,
        description=subj_desc,
        instruction=subj_instruction,
        tools=tools,
    )
