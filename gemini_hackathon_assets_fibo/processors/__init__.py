"""gemini_hackathon_assets_fibo.processors — texture / image post-processing.

Lifted from `cianfhoghlaim/docs/sruth/tuath/asset_generation/processors/texture_processor.py`
and reduced to the operations the education system needs:

  - texture_processor.py: ResizeMode + TextureFormat + resize / format
    conversion / subject watermark (used by the editorial canvas and
    the certificate compositing in W14)
"""

from gemini_hackathon_assets_fibo.processors.texture_processor import (
    PIL_AVAILABLE,
    ResizeMode,
    TextureFormat,
    apply_subject_watermark,
    convert_format,
    resize_image,
    save_image,
)

__all__ = [
    "PIL_AVAILABLE",
    "ResizeMode",
    "TextureFormat",
    "apply_subject_watermark",
    "convert_format",
    "resize_image",
    "save_image",
]
