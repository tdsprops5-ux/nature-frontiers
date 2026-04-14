"""
Backend package for Text-to-Video Nature Generator.
"""

from .config import settings
from .utils import (
    list_presets,
    get_preset_info,
    enhance_prompt,
    generate_prompt_variations,
    calculate_clip_count,
    generate_seo_metadata,
    save_seo_metadata
)
from .pipeline import pipeline
from .video_builder import builder
from .audio import audio_generator

__all__ = [
    "settings",
    "list_presets",
    "get_preset_info",
    "enhance_prompt",
    "generate_prompt_variations",
    "calculate_clip_count",
    "generate_seo_metadata",
    "save_seo_metadata",
    "pipeline",
    "builder",
    "audio_generator"
]
