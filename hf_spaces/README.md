# HF Spaces — gemini_hackathon_* (5 headline demos)

The 5 Hugging Face Spaces that ship for the gemini_hackathon All Things
Agentic 2026 hackathon. Each Space is a smaller, focused surface
of one stage of the British Isles education system.

  cianfhoghlaim/gemini_hackathon_aistear           — Aistear (Early Years 0-6)
  cianfhoghlaim/gemini_hackathon_bunscoil          — Bunscoil (Primary 4-12)
  cianfhoghlaim/gemini_hackathon_junior_cycle      — MeanScoil (Junior Cycle 12-15)
  cianfhoghlaim/gemini_hackathon_leaving_certificate — Scoil Sinsearach (LC 15-19)
  cianfhoghlaim/gemini_hackathon_editorial_studio   — Editorial Studio (the big canvas)

The Spaces are judge-shareable surfaces — clicking through one shows the
canonical gemini_hackathon editorial canvas for that stage.

Each Space:
  - Pins to `gradio >= 5.28.0, < 6.0`
  - Imports the studio from `gemini_hackathon_gradio` (the lift of
    `sruth/spaces/`)
  - Shows the same 5-stage British Isles education palette
  - Exposes its key nodes as MCP tools (`gr.mcp.start(workflow.app)`)
    so an agent harness can call into the Space

The big Cloud Run editorial studio (W12) is the analyst + power-user
surface; these 5 HF Spaces are the entry points.

To publish:
  1. `cd hf_spaces/gemini_hackathon_<stage>`
  2. `huggingface-cli login`
  3. `huggingface-cli upload cianfhoghlaim/gemini_hackathon_<stage> .`
  4. Wait for HF to build + serve the Space
"""
