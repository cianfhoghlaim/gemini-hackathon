"""Generate the 4 NEW ADK-focused .ipynb notebooks (Phase 7.4).

Run: uv run --with nbformat python notebooks/converted/_generate_adk_notebooks.py

This is a one-shot generator — the resulting .ipynb files are committed to the repo.
After first generation, the .ipynb files are static (don't need regenerating).
"""

from __future__ import annotations

import json
import pathlib


def cell_md(source: list[str]) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": source,
    }


def cell_code(source: list[str]) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source,
    }


def notebook(cells: list[dict]) -> dict:
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {
                "name": "python",
                "version": "3.12",
                "file_extension": ".py",
                "mimetype": "text/x-python",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def write(path: pathlib.Path, nb: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        json.dump(nb, fp, indent=1, ensure_ascii=False)
    print(f"  wrote {path} ({sum(len(c.get('source', [])) for c in nb['cells'])} cells)")


# ---------------------------------------------------------------------------
# Notebook 1: google_adk_agent_tree.ipynb — the ADK agent tree
# ---------------------------------------------------------------------------


def build_google_adk_agent_tree() -> dict:
    cells = [
        cell_md(
            [
                "# The Google ADK Agent Tree\n",
                "\n",
                "**What this notebook shows**: the complete Google ADK (`google-adk >= 2.7.1`) agent tree for the gemini-hackathon submission. Walks the LlmAgent + 5 tools + App + Runner + Fleet primitives stack.\n",
                "\n",
                "**Source**: derived from the `gemini_hackathon/agents/adk_gemini_agent.py` (Phase 1-3 lift + extensions).\n",
                "\n",
                "**5-layer walkthrough**:\n",
                "1. (this file) Title + provenance\n",
                "2. The LlmAgent + 5 FunctionTool + App + Runner stack\n",
                "3. The AGUI 13-event protocol (see `agui_event_protocol.ipynb`)\n",
                "4. The CopilotKit consumption (see `copilotkit_runtime_config.ipynb`)\n",
                "5. (This file) The run_agent_turn() pipeline\n",
            ]
        ),
        cell_md(
            [
                "## Layer 2 — The LlmAgent + 5 FunctionTool + App + Runner stack\n",
                "\n",
                "The `build_adk_agent()` factory in `gemini_hackathon/agents/adk_gemini_agent.py`:\n",
                '- Wraps the LlmAgent in `App(root_agent=..., name="gemini_hackathon")`\n',
                '- Uses `Gemini(model="gemini-3.5-flash", retry_options=HttpRetryOptions(attempts=3))`\n',
                "- Wires 5 FunctionTool wrappers (lookup_outcome, retrieve_resources, find_similar_resources, retrieve_safeguarding, mark_answer)\n",
                "- Instantiates `InMemoryRunner(agent=app)`\n",
                "\n",
                "Run the cell below to inspect the live agent tree.\n",
            ]
        ),
        cell_code(
            [
                "import sys\n",
                "from pathlib import Path\n",
                "\n",
                "REPO_ROOT = Path.cwd()\n",
                "sys.path.insert(0, str(REPO_ROOT))\n",
                "\n",
                "# Build the canonical ADK agent tree\n",
                "from gemini_hackathon.agents.adk_gemini_agent import (\n",
                "    GEMINI_HACKATHON_AGENT, build_adk_agent, _build_adk_tool_wrappers,\n",
                ")\n",
                "\n",
                "print(\"AGUI events:\", len(GEMINI_HACKATHON_AGENT.tool_count if hasattr(GEMINI_HACKATHON_AGENT, 'tool_count') else 5))\n",
                'print("Model:", GEMINI_HACKATHON_AGENT.model)\n',
                'print("Tool descriptions:")\n',
                "for tool in GEMINI_HACKATHON_AGENT.tools:\n",
                '    print(f"  - {tool.name}: {tool.description[:80]}...")\n',
            ]
        ),
        cell_md(
            [
                "## Layer 5 — The `run_agent_turn()` pipeline\n",
                "\n",
                "The `run_agent_turn()` function (in `adk_gemini_agent.py`) composes:\n",
                "\n",
                "1. `ModelArmor.check_prompt(message)` — input sanitisation (prompt-injection / PII guard)\n",
                "2. `Observability.trace(agent_name, user_id, session_id, subnation)` — opens a Fleet trace\n",
                "3. `runner.run(user_id, session_id, new_message=content)` — the real ADK invocation\n",
                "4. `Observability.record_invocation(trace, agent_name, event_count, status)` — emits the cost + tokens event\n",
                "5. `render_agui_events(raw_events)` — converts ADK Event → AgUiEvent for the AGUI stream\n",
                "\n",
                "Run the cell below to see the Fleet-wrapped turn in action.\n",
            ]
        ),
        cell_code(
            [
                "from gemini_hackathon.agents.adk_gemini_agent import run_agent_turn, AgentTurnResult\n",
                "\n",
                "result = run_agent_turn(\n",
                '    message="What are the JC Maths outcomes for Ireland?",\n',
                '    subnation="ireland",\n',
                '    role="student",\n',
                '    cycle="junior_cycle",\n',
                ")\n",
                'print(f"status: {result.status}")\n',
                'print(f"events: {len(result.events)}")\n',
                "print(f\"model_armor.blocked: {result.model_armor_check.blocked if result.model_armor_check else 'n/a'}\")\n",
                "print(f\"observability.trace_id: {result.observability.trace_id if result.observability else 'n/a'}\")\n",
            ]
        ),
    ]
    return notebook(cells)


# ---------------------------------------------------------------------------
# Notebook 2: agui_event_protocol.ipynb — the 13 AGUI event types
# ---------------------------------------------------------------------------


def build_agui_event_protocol() -> dict:
    cells = [
        cell_md(
            [
                "# The AGUI 13-Event Protocol\n",
                "\n",
                "**What this notebook shows**: the 13 AGUI event types emitted by the ADK agent tree, the `render_agui_events()` loop, and the SSE stream to `/api/copilotkit/chat/completions`.\n",
                "\n",
                "**Source**: `gemini_hackathon/agents/adk_gemini_agent.py:AGUI_EVENT_TYPES` + `render_agui_events()`.\n",
            ]
        ),
        cell_md(
            [
                "## Layer 3 — The 13 AGUI event types\n",
                "\n",
                "Per `AGUI_EVENT_TYPES` (the gemini-hackathon AG-UI subset):\n",
                "\n",
                "1. `RUN_STARTED`\n",
                "2. `STATE_DELTA`\n",
                "3. `TEXT_MESSAGE_START`\n",
                "4. `TEXT_MESSAGE_CONTENT`\n",
                "5. `TEXT_MESSAGE_END`\n",
                "6. `TOOL_CALL_START`\n",
                "7. `TOOL_CALL_ARGS`\n",
                "8. `TOOL_CALL_END`\n",
                "9. `TOOL_CALL_RESULT`\n",
                "10. `STEP_STARTED`\n",
                "11. `STEP_FINISHED`\n",
                "12. `RUN_FINISHED`\n",
                "13. `RUN_ERROR`\n",
            ]
        ),
        cell_code(
            [
                "from gemini_hackathon.agents.adk_gemini_agent import AGUI_EVENT_TYPES, AgUiEvent\n",
                "\n",
                'print(f"13 AGUI events ({len(AGUI_EVENT_TYPES)}):")\n',
                "for i, evt in enumerate(AGUI_EVENT_TYPES, 1):\n",
                '    print(f"  {i:>2}. {evt}")\n',
            ]
        ),
        cell_md(
            [
                "## The `render_agui_events()` loop\n",
                "\n",
                "The 33-LOC loop that converts `google.adk.events.Event` objects into `AgUiEvent` instances:\n",
                "1. Iterates the ADK Event stream\n",
                '2. For each event with `author == "agent"`: emits TEXT_MESSAGE_CONTENT + TOOL_CALL_* for function_calls\n',
                "3. For each event with non-agent author: emits TOOL_CALL_RESULT for function_response\n",
                "4. Returns a list[AgUiEvent] that the FastAPI handler serialises to SSE\n",
            ]
        ),
        cell_code(
            [
                "import inspect\n",
                "from gemini_hackathon.agents.adk_gemini_agent import render_agui_events\n",
                "print(inspect.getsource(render_agui_events))\n",
            ]
        ),
        cell_md(
            [
                "## The SSE stream from `/api/copilotkit/chat/completions`\n",
                "\n",
                "The route handler in `gemini_hackathon/backend.py:_handle_agents_chat`:\n",
                "1. Parses the JSON body (message, user_id, session_id, subnation, role, cycle, ...)\n",
                "2. Calls `run_agent_turn(...)` to get back the `AgentTurnResult`\n",
                "3. Serialises the `events: list[AgUiEvent]` to SSE chunks\n",
                "4. The CopilotKit React provider in `web/src/routes/__root.tsx:14` consumes the SSE stream via `useFrontendTool` / `useRenderTool`\n",
            ]
        ),
    ]
    return notebook(cells)


# ---------------------------------------------------------------------------
# Notebook 3: copilotkit_runtime_config.ipynb — the CopilotKit integration
# ---------------------------------------------------------------------------


def build_copilotkit_runtime_config() -> dict:
    cells = [
        cell_md(
            [
                "# The CopilotKit Runtime + AGUI + TanStack Start Integration\n",
                "\n",
                "**What this notebook shows**: the CopilotKit React provider in `web/src/routes/__root.tsx:14` + the AGUI SSE stream + the `useFrontendTool` / `useRenderTool` patterns that surface the 5 ADK tools to the UI.\n",
                "\n",
                "**Source**: `web/src/routes/__root.tsx` + `web/src/components/marimo/MarimoEmbed.tsx`.\n",
            ]
        ),
        cell_md(
            [
                "## Layer 4 — The CopilotKit runtime + the route map\n",
                "\n",
                "The `__root.tsx` mounts the CopilotKit provider with:\n",
                "```tsx\n",
                '<CopilotKit runtimeUrl="/api/copilotkit/chat/completions" agent="gemini_hackathon_agent">\n',
                "  <Outlet />\n",
                "</CopilotKit>\n",
                "```\n",
                "\n",
                "The 8 routes that consume AGUI events:\n",
                "- `/` — per-subnation home\n",
                "- `/subjects` + `/subjects/$slug` — per-subject marimo embed\n",
                "- `/agents` — chat panel\n",
                "- `/find-resources` — cross-national resource discovery\n",
                "- `/compare` — DuckDB-WASM leaderboard\n",
                "- `/safeguarding` — per-subnation safeguarding policy\n",
                "- `/archipelago` — 8 subnations side-by-side\n",
                "- `/equivalency` — cross-jurisdiction equivalency UI\n",
            ]
        ),
        cell_code(
            [
                "import pathlib\n",
                "from collections import Counter\n",
                "\n",
                'routes_dir = pathlib.Path("web/src/routes")\n',
                'route_files = sorted(pathlib.Path(routes_dir).glob("**/*.tsx"))\n',
                'print(f"{len(route_files)} routes in web/src/routes/")\n',
                "for p in route_files:\n",
                "    print(f\"  - {p.relative_to('web/src/routes')}\")\n",
            ]
        ),
        cell_md(
            [
                "## The `useFrontendTool` / `useRenderTool` patterns\n",
                "\n",
                "The 5 ADK tools surface to the UI via CopilotKit's `useRenderTool`:\n",
                "- `lookup_outcome` → renders a syllabus-outcome card\n",
                "- `retrieve_resources` → renders a resource list\n",
                "- `find_similar_resources` → renders a cross-jurisdiction comparison table\n",
                "- `retrieve_safeguarding` → renders a safeguarding policy panel\n",
                "- `mark_answer` → renders a marking card with descriptor\n",
                "\n",
                "Plus the `mcp_servers: { stitch: { url: STITCH_MCP_URL, transport: 'sse' } }` runtime config for the Stitch MCP integration.\n",
            ]
        ),
    ]
    return notebook(cells)


# ---------------------------------------------------------------------------
# Notebook 4: fleet_primitives.ipynb — the 7 Fleet primitives
# ---------------------------------------------------------------------------


def build_fleet_primitives() -> dict:
    cells = [
        cell_md(
            [
                "# The 7 Fleet Primitives Wrapping the ADK Agent Tree\n",
                "\n",
                "**What this notebook shows**: the 7 Fleet primitives from `gemini_hackathon/agents/fleet/` (the byte-identical wholesale copy of `cianfhoghlaim/packages/fleet/src/cianfhoghlaim/fleet/`).\n",
                "\n",
                "**Source**: `gemini_hackathon/agents/fleet/{fleet_gateway,fleet_identity,fleet_model_armor,fleet_memory,fleet_observability,fleet_mcp_curriculum,fleet_agui}.py` — 3,444 LOC total.\n",
            ]
        ),
        cell_md(
            [
                "## The 7 Fleet primitives\n",
                "\n",
                "1. **FleetGateway** — single canonical entrypoint + keyword routing (`AGENT_NAMES` / `KEYWORD_TO_AGENT`)\n",
                "2. **FleetIdentity** — caller identity resolution (BetterAuth / JWT / anonymous)\n",
                "3. **FleetModelArmor** — input sanitisation (PII redaction, prompt-injection guard, jailbreak detection)\n",
                "4. **FleetMemory** — Letta-backed long-term memory (with in-memory fallback)\n",
                "5. **FleetObservability** — Langfuse + Logfire + MLflow + GCP-native OTel tracing\n",
                "6. **FleetMcpCurriculum** — the 14-subject MCP server (the ADK tools surface as MCP resources)\n",
                "7. **FleetAGUIBridge** — the CopilotKit + AGUI protocol adapter\n",
            ]
        ),
        cell_code(
            [
                "from gemini_hackathon.agents.fleet import (\n",
                "    FleetGateway, FleetIdentity, FleetModelArmor,\n",
                "    FleetMemory, FleetObservability, FleetMcpCurriculum, FleetAGUIBridge,\n",
                ")\n",
                "\n",
                "primitives = [\n",
                '    ("FleetGateway", FleetGateway, "Single canonical entrypoint + keyword routing"),\n',
                '    ("FleetIdentity", FleetIdentity, "Caller identity resolution (BetterAuth / JWT)"),\n',
                '    ("FleetModelArmor", FleetModelArmor, "Input sanitisation (PII / prompt-injection)"),\n',
                '    ("FleetMemory", FleetMemory, "Letta-backed long-term memory"),\n',
                '    ("FleetObservability", FleetObservability, "Langfuse + Logfire + MLflow + OTel"),\n',
                '    ("FleetMcpCurriculum", FleetMcpCurriculum, "14-subject MCP server"),\n',
                '    ("FleetAGUIBridge", FleetAGUIBridge, "CopilotKit + AGUI protocol adapter"),\n',
                "]\n",
                "for name, cls, doc in primitives:\n",
                '    print(f"  - {name}: {doc}")\n',
            ]
        ),
        cell_md(
            [
                "## How the primitives wrap `run_agent_turn()`\n",
                "\n",
                "Per `gemini_hackathon/agents/adk_gemini_agent.py:run_agent_turn()`:\n",
                "1. `ModelArmor.check_prompt(message)` (Fleet primitive #3) — blocks prompt injection + PII\n",
                "2. `Observability.trace(agent_name, user_id, session_id, subnation)` (Fleet primitive #5) — opens a trace\n",
                "3. `runner.run(user_id, session_id, new_message=content)` — the real ADK invocation\n",
                "4. `Observability.record_invocation(trace, ...)` (Fleet primitive #5) — emits the cost + tokens event\n",
                "5. `render_agui_events(raw_events)` → `AgUiEvent` for the `FleetAGUIBridge` (Fleet primitive #7) to surface to CopilotKit\n",
                "\n",
                "Identity is provided by `FleetIdentity.authenticate()` (Fleet primitive #2) and the long-term memory by `FleetMemory` (Fleet primitive #4). The 14-subject MCP server (Fleet primitive #6) is mounted alongside the agent for cross-subject tool calls.\n",
            ]
        ),
    ]
    return notebook(cells)


# ---------------------------------------------------------------------------
# Run all 4 generators
# ---------------------------------------------------------------------------


def main() -> None:
    base = pathlib.Path("notebooks/converted")
    notebooks = [
        ("google_adk_agent_tree.ipynb", build_google_adk_agent_tree),
        ("agui_event_protocol.ipynb", build_agui_event_protocol),
        ("copilotkit_runtime_config.ipynb", build_copilotkit_runtime_config),
        ("fleet_primitives.ipynb", build_fleet_primitives),
    ]
    for filename, builder in notebooks:
        write(base / filename, builder())
    print(f"\\nGenerated {len(notebooks)} ADK-focused notebooks in {base}/")


if __name__ == "__main__":
    main()
