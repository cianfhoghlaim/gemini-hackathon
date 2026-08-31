"""gemini_hackathon_gradio._common.demo_recorder — programmatic demo recording.

Lifted from `sruth/spaces/_common/demo_recorder.py` and adapted for the
5-stage British Isles education palette. Used by the editorial canvas
(W12) for the demo video: instead of manually clicking through every
feature, record a `DemoSequence` and emit a storyboard + voiceover
script.

The stage palette replaces the Celtic element palette (talamh →
Aistear, uisce → Bunscoil, tine → MeanScoil, aer → Scoil Sinsearach,
anam → Ollscoil).

Usage:

    from gemini_hackathon_gradio._common.demo_recorder import (
        DemoSequence, record_interaction, render_storyboard,
    )
    seq = DemoSequence(title="An Scrudu (LC Past Paper Heatmap)", stage="scoil_sinsearach")
    seq.add("input_pdf", "lc_chem_2024.pdf")
    seq.add("extract_btn.click", None)
    seq.add("output_heatmap", "...")
    render_storyboard(seq, "storyboard.png")
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

# The 5-stage palette (matches theme.EDUCATION_PALETTE)
STAGE_LABELS: dict[str, str] = {
    "aistear": "Aistear (Early Years)",
    "bunscoil": "Bunscoil (Primary)",
    "meanscoil": "MeanScoil (Junior Cycle)",
    "scoil_sinsearach": "Scoil Sinsearach (Senior Cycle / Leaving Certificate)",
    "ollscoil": "Ollscoil (Tertiary)",
}


@dataclass
class DemoStep:
    """A single recorded interaction step."""

    timestamp: float
    component_id: str
    value: Any
    note: str = ""


@dataclass
class DemoSequence:
    """A full demo sequence for one studio."""

    title: str
    stage: str  # aistear, bunscoil, meanscoil, scoil_sinsearach, ollscoil
    steps: list[DemoStep] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    voiceover_lines: list[str] = field(default_factory=list)

    def add(
        self,
        component_id: str,
        value: Any,
        note: str = "",
    ) -> None:
        """Record a single interaction step."""
        elapsed = time.time() - self.started_at
        self.steps.append(
            DemoStep(
                timestamp=elapsed,
                component_id=component_id,
                value=value,
                note=note,
            )
        )

    def add_voiceover(self, line: str) -> None:
        """Add a voiceover line at the current timestamp."""
        self.voiceover_lines.append(line)

    @property
    def total_duration(self) -> float:
        """Estimated total duration in seconds (1 step ~= 3s)."""
        return max(len(self.steps) * 3.0, 15.0)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dict (for JSON sidecar)."""
        return {
            "title": self.title,
            "stage": self.stage,
            "stage_label": STAGE_LABELS.get(self.stage, self.stage),
            "total_duration_s": self.total_duration,
            "steps": [
                {
                    "timestamp": s.timestamp,
                    "component_id": s.component_id,
                    "value": s.value,
                    "note": s.note,
                }
                for s in self.steps
            ],
            "voiceover_lines": list(self.voiceover_lines),
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


def record_interaction(
    sequence: DemoSequence,
    component_id: str,
    value: Any,
    note: str = "",
) -> None:
    """Convenience wrapper around sequence.add()."""
    sequence.add(component_id, value, note)


def render_storyboard(
    sequence: DemoSequence,
    output_path: str,
    *,
    width: int = 1920,
    height: int = 1080,
    bg_color: str = "#1d1d2f",  # Hades base
    fg_color: str = "#d8d4cc",  # Hades bone
) -> None:
    """Render a 16:9 storyboard PNG from a DemoSequence.

    Pure-Python PNG renderer (no PIL / reportlab dep). Writes a flat PNG
    with the title + each step as a labelled block.

    Note: this is a *minimal* storyboard renderer — it produces a single
    PNG with all steps stacked vertically. For a full multi-frame storyboard,
    use FFmpeg / the Hackathon video tools. The output PNG is suitable for
    upload as a "demo flow" social-card image.
    """

    # Layout constants
    padding = 40
    line_height = 28
    step_height = line_height * 4  # each step gets 4 lines (component, value, note, divider)
    title_height = line_height * 2
    total_height = padding + title_height + step_height * max(1, len(sequence.steps)) + padding

    # Build the pixel buffer: 3 bytes per pixel (RGB).
    # Each scanline is row-major left-to-right, top-to-bottom.
    buf = bytearray()
    bg = _parse_hex_color(bg_color)
    fg = _parse_hex_color(fg_color)
    accent = _parse_hex_color("#cc9966")  # Scoil Sinsearach gold (default accent)

    # Build a minimal pixel buffer: solid background + drawn rectangles.
    # True text rendering is non-trivial without a font; we use a simple
    # pseudo-text: each character is a 5×7 glyph drawn from a hard-coded
    # 5×7 bitmap font (the canonical 'mini-font').
    font = _MINI_FONT

    def text_width(s: str) -> int:
        return len(s) * 6  # 5 px char + 1 px spacing

    def draw_rect(y: int, _h: int, _color: tuple[int, int, int]) -> None:
        pass  # placeholder; not pixel-rendering rects in the minimal version

    def draw_text(x: int, y: int, s: str, color: tuple[int, int, int]) -> None:
        for ch in s:
            glyph = font.get(ch.upper(), font[" "])
            for ry, row in enumerate(glyph):
                for rx, bit in enumerate(row):
                    if bit:
                        px = x + rx
                        py = y + ry
                        if 0 <= px < width and 0 <= py < total_height:
                            idx = (py * width + px) * 3
                            buf[idx] = color[0]
                            buf[idx + 1] = color[1]
                            buf[idx + 2] = color[2]
            x += 6

    # Fill background
    for _ in range(total_height * width):
        buf.extend(bg)

    # Title
    draw_text(padding, padding, sequence.title[:60], accent)
    draw_text(padding, padding + line_height, sequence.stage_label, fg)

    # Steps
    y = padding + title_height
    for i, step in enumerate(sequence.steps, 1):
        line = f"{i:>2}. {step.component_id}  t={step.timestamp:5.2f}s"
        draw_text(padding, y, line[:80], fg)
        y += line_height
        if step.value is not None:
            v = repr(step.value) if not isinstance(step.value, str) else step.value
            draw_text(padding + 20, y, "value: " + v[:70], fg)
            y += line_height
        if step.note:
            draw_text(padding + 20, y, "note: " + step.note[:70], fg)
            y += line_height
        y += line_height  # divider gap

    # PNG-encode the buffer (RGB, 8-bit).
    _write_png(output_path, width, total_height, bytes(buf))


def _parse_hex_color(hex_color: str) -> tuple[int, int, int]:
    """Parse a hex color string (#RRGGBB or #RGB) into an (R, G, B) tuple."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _write_png(path: str, width: int, height: int, data: bytes) -> None:
    """Write an RGB PNG to disk. Pure-Python (no PIL)."""
    import struct
    import zlib

    def chunk(typ: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + typ
            + payload
            + struct.pack(">I", zlib.crc32(typ + payload) & 0xFFFFFFFF)
        )

    # Filter byte 0 (None) per scanline.
    raw = bytearray()
    stride = width * 3
    for y in range(height):
        raw.append(0)
        raw.extend(data[y * stride : (y + 1) * stride])

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")

    with open(path, "wb") as f:
        f.write(png)


# A minimal 5x7 bitmap font for A-Z, 0-9, space, dot, dash.
# Each row is 7 bits (top to bottom), MSB is leftmost column.
_MINI_FONT: dict[str, tuple[int, ...]] = {
    " ": (0, 0, 0, 0, 0),
    "A": (0x7E, 0x11, 0x11, 0x11, 0x7E),
    "B": (0x7F, 0x49, 0x49, 0x49, 0x36),
    "C": (0x3E, 0x41, 0x41, 0x41, 0x22),
    "D": (0x7F, 0x41, 0x41, 0x22, 0x1C),
    "E": (0x7F, 0x49, 0x49, 0x49, 0x41),
    "F": (0x7F, 0x09, 0x09, 0x09, 0x01),
    "G": (0x3E, 0x41, 0x49, 0x49, 0x7A),
    "H": (0x7F, 0x08, 0x08, 0x08, 0x7F),
    "I": (0x00, 0x41, 0x7F, 0x41, 0x00),
    "J": (0x20, 0x40, 0x41, 0x3F, 0x01),
    "K": (0x7F, 0x08, 0x14, 0x22, 0x41),
    "L": (0x7F, 0x40, 0x40, 0x40, 0x40),
    "M": (0x7F, 0x02, 0x04, 0x02, 0x7F),
    "N": (0x7F, 0x04, 0x08, 0x10, 0x7F),
    "O": (0x3E, 0x41, 0x41, 0x41, 0x3E),
    "P": (0x7F, 0x09, 0x09, 0x09, 0x06),
    "Q": (0x3E, 0x41, 0x51, 0x21, 0x5E),
    "R": (0x7F, 0x09, 0x19, 0x29, 0x46),
    "S": (0x46, 0x49, 0x49, 0x49, 0x31),
    "T": (0x01, 0x01, 0x7F, 0x01, 0x01),
    "U": (0x3F, 0x40, 0x40, 0x40, 0x3F),
    "V": (0x1F, 0x20, 0x40, 0x20, 0x1F),
    "W": (0x7F, 0x20, 0x18, 0x20, 0x7F),
    "X": (0x63, 0x14, 0x08, 0x14, 0x63),
    "Y": (0x07, 0x08, 0x70, 0x08, 0x07),
    "Z": (0x61, 0x51, 0x49, 0x45, 0x43),
    "0": (0x3E, 0x51, 0x49, 0x45, 0x3E),
    "1": (0x00, 0x42, 0x7F, 0x40, 0x00),
    "2": (0x62, 0x51, 0x49, 0x49, 0x46),
    "3": (0x22, 0x41, 0x49, 0x49, 0x36),
    "4": (0x18, 0x14, 0x12, 0x7F, 0x10),
    "5": (0x2F, 0x49, 0x49, 0x49, 0x31),
    "6": (0x3E, 0x49, 0x49, 0x49, 0x32),
    "7": (0x01, 0x01, 0x71, 0x09, 0x07),
    "8": (0x36, 0x49, 0x49, 0x49, 0x36),
    "9": (0x26, 0x49, 0x49, 0x49, 0x3E),
    ".": (0x00, 0x00, 0x60, 0x60, 0x00),
    "-": (0x08, 0x08, 0x08, 0x08, 0x08),
}


__all__ = [
    "STAGE_LABELS",
    "DemoSequence",
    "DemoStep",
    "record_interaction",
    "render_storyboard",
]
