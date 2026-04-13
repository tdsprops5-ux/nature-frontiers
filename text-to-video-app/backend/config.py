"""
Configuration settings for the Text-to-Video Nature Generator.
Centralizes all application settings, paths, and model configurations.
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application configuration with environment variable support."""
    
    # Application Settings
    APP_NAME: str = "Text-to-Video Nature Generator"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # Server Settings
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    GRADIO_PORT: int = Field(default=7860, env="GRADIO_PORT")
    
    # Hardware Acceleration
    USE_CUDA: bool = Field(default=True, env="USE_CUDA")
    CUDA_DEVICE: int = Field(default=0, env="CUDA_DEVICE")
    NUM_WORKERS: int = Field(default=4, env="NUM_WORKERS")
    MIXED_PRECISION: bool = Field(default=True, env="MIXED_PRECISION")
    
    # Model Settings
    MODEL_CACHE: Path = Field(default=Path("./models"), env="MODEL_CACHE")
    MODEL_TYPE: str = Field(default="modelscape", env="MODEL_TYPE")  # modelscape, animatediff, svd
    MODEL_ID_TEXT2VIDEO: str = Field(
        default="damo-vilab/text-to-video-ms-1.7b",
        env="MODEL_ID_TEXT2VIDEO"
    )
    MODEL_ID_IMAGE: str = Field(
        default="stabilityai/stable-diffusion-xl-base-1.0",
        env="MODEL_ID_IMAGE"
    )
    MODEL_ID_TTS: str = Field(
        default="tts_models/en/ljspeech/tacotron2-DDC",
        env="MODEL_ID_TTS"
    )
    
    # Video Generation Settings
    DEFAULT_RESOLUTION: str = Field(default="1920x1080", env="DEFAULT_RESOLUTION")
    MAX_RESOLUTION: int = Field(default=1920, env="MAX_RESOLUTION")
    DEFAULT_FPS: int = Field(default=30, env="DEFAULT_FPS")
    TARGET_FPS: int = Field(default=60, env="TARGET_FPS")
    CLIP_DURATION_SECONDS: int = Field(default=8, env="CLIP_DURATION_SECONDS")
    MAX_CLIP_DURATION: int = Field(default=10, env="MAX_CLIP_DURATION")
    MIN_CLIP_DURATION: int = Field(default=4, env="MIN_CLIP_DURATION")
    
    # Long Video Settings
    MAX_DURATION_MINUTES: int = Field(default=180, env="MAX_DURATION_MINUTES")
    TRANSITION_TYPE: str = Field(default="crossfade", env="TRANSITION_TYPE")
    TRANSITION_DURATION: float = Field(default=1.0, env="TRANSITION_DURATION")
    
    # Quality Settings
    QUALITY_PRESET: str = Field(default="high", env="QUALITY_PRESET")  # low, medium, high
    CONTRAST_BOOST: float = Field(default=1.3, env="CONTRAST_BOOST")
    SATURATION_BOOST: float = Field(default=1.1, env="SATURATION_BOOST")
    SHARPNESS_ENHANCE: float = Field(default=1.2, env="SHARPNESS_ENHANCE")
    
    # Processing Options
    ENABLE_INTERPOLATION: bool = Field(default=True, env="ENABLE_INTERPOLATION")
    ENABLE_UPSCALING: bool = Field(default=False, env="ENABLE_UPSCALING")
    ENABLE_AUDIO: bool = Field(default=True, env="ENABLE_AUDIO")
    SAVE_INTERMEDIATE: bool = Field(default=False, env="SAVE_INTERMEDIATE")
    
    # Output Settings
    OUTPUT_DIR: Path = Field(default=Path("./outputs"), env="OUTPUT_DIR")
    VIDEO_OUTPUT_DIR: Path = Field(default=Path("./outputs/videos"), env="VIDEO_OUTPUT_DIR")
    AUDIO_OUTPUT_DIR: Path = Field(default=Path("./outputs/audio"), env="AUDIO_OUTPUT_DIR")
    FRAME_OUTPUT_DIR: Path = Field(default=Path("./outputs/frames"), env="FRAME_OUTPUT_DIR")
    LOG_OUTPUT_DIR: Path = Field(default=Path("./outputs/logs"), env="LOG_OUTPUT_DIR")
    
    # Format Settings
    OUTPUT_FORMAT: str = Field(default="mp4", env="OUTPUT_FORMAT")
    VIDEO_CODEC: str = Field(default="libx264", env="VIDEO_CODEC")
    AUDIO_CODEC: str = Field(default="aac", env="AUDIO_CODEC")
    VIDEO_BITRATE: str = Field(default="10M", env="VIDEO_BITRATE")
    AUDIO_BITRATE: str = Field(default="192k", env="AUDIO_BITRATE")
    
    # Batch Processing
    BATCH_QUEUE_SIZE: int = Field(default=10, env="BATCH_QUEUE_SIZE")
    BATCH_CONCURRENT: int = Field(default=1, env="BATCH_CONCURRENT")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FILE: Path = Field(default=Path("./outputs/logs/app.log"), env="LOG_FILE")
    
    # Style Presets
    STYLE_PRESETS: Dict[str, Dict[str, Any]] = {
        "ocean": {
            "prompt_suffix": "deep blue ocean water, underwater scene, marine life, cinematic lighting",
            "contrast": 1.3,
            "saturation": 1.2,
            "temperature": "cool",
            "color_grading": "deep_ocean"
        },
        "deep_sea": {
            "prompt_suffix": "abyssal depths, bioluminescent creatures, dark water, mysterious atmosphere",
            "contrast": 1.4,
            "saturation": 1.0,
            "temperature": "cool",
            "color_grading": "bioluminescent"
        },
        "coral_reef": {
            "prompt_suffix": "vibrant coral reef, tropical fish, clear turquoise water, sunlight filtering",
            "contrast": 1.2,
            "saturation": 1.4,
            "temperature": "warm",
            "color_grading": "tropical"
        },
        "wildlife": {
            "prompt_suffix": "wild animals in natural habitat, documentary style, dramatic lighting",
            "contrast": 1.3,
            "saturation": 1.1,
            "temperature": "neutral",
            "color_grading": "documentary"
        },
        "jungle": {
            "prompt_suffix": "dense rainforest, lush vegetation, morning mist, shafts of sunlight",
            "contrast": 1.2,
            "saturation": 1.3,
            "temperature": "warm",
            "color_grading": "rainforest"
        },
        "arctic": {
            "prompt_suffix": "ice landscapes, polar wildlife, cold atmosphere, aurora borealis",
            "contrast": 1.3,
            "saturation": 0.9,
            "temperature": "cool",
            "color_grading": "arctic"
        }
    }
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure directories exist
        self._create_directories()
    
    def _create_directories(self):
        """Create necessary output directories if they don't exist."""
        directories = [
            self.OUTPUT_DIR,
            self.VIDEO_OUTPUT_DIR,
            self.AUDIO_OUTPUT_DIR,
            self.FRAME_OUTPUT_DIR,
            self.LOG_OUTPUT_DIR,
            self.MODEL_CACHE
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    @property
    def device(self) -> str:
        """Get the compute device (cuda or cpu)."""
        if self.USE_CUDA:
            try:
                import torch
                if torch.cuda.is_available():
                    return f"cuda:{self.CUDA_DEVICE}"
            except ImportError:
                pass
        return "cpu"
    
    @property
    def resolution_tuple(self) -> tuple:
        """Parse resolution string into tuple."""
        width, height = map(int, self.DEFAULT_RESOLUTION.split('x'))
        return (width, height)
    
    def get_quality_preset(self, preset_name: str) -> Dict[str, Any]:
        """Get quality settings for a specific preset."""
        presets = {
            "low": {
                "resolution": "1280x720",
                "fps": 24,
                "clip_duration": 4,
                "interpolation": False,
                "contrast": 1.0
            },
            "medium": {
                "resolution": "1920x1080",
                "fps": 30,
                "clip_duration": 6,
                "interpolation": True,
                "contrast": 1.2
            },
            "high": {
                "resolution": "1920x1080",
                "fps": 60,
                "clip_duration": 8,
                "interpolation": True,
                "contrast": 1.3
            },
            "ultra": {
                "resolution": "3840x2160",
                "fps": 60,
                "clip_duration": 10,
                "interpolation": True,
                "contrast": 1.4
            }
        }
        return presets.get(preset_name, presets["medium"])


# Global settings instance
settings = Settings()
