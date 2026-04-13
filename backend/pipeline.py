"""
Core video generation pipeline for the Text-to-Video Nature Generator.
Handles model loading, clip generation, and frame processing.
"""

import os
import gc
from pathlib import Path
from typing import List, Optional, Dict, Any, Generator
from datetime import datetime
from loguru import logger
import numpy as np
from PIL import Image

from .config import settings
from .utils import enhance_prompt, apply_color_grading


class VideoGenerationPipeline:
    """
    Main pipeline for generating video clips from text prompts.
    Supports multiple model backends and handles GPU memory management.
    """
    
    def __init__(self):
        self.device = settings.device
        self.text2video_model = None
        self.image_model = None
        self.upscaler = None
        self.is_loaded = False
        
        logger.info(f"Initialized VideoGenerationPipeline on device: {self.device}")
    
    def load_models(self, force_reload: bool = False) -> bool:
        """
        Load AI models for video and image generation.
        
        Args:
            force_reload: Force reload models even if already loaded
            
        Returns:
            True if models loaded successfully
        """
        if self.is_loaded and not force_reload:
            logger.info("Models already loaded")
            return True
        
        try:
            import torch
            from diffusers import DiffusionPipeline, StableDiffusionPipeline
            
            # Load text-to-video model
            logger.info(f"Loading text-to-video model: {settings.MODEL_ID_TEXT2VIDEO}")
            
            # Use ModelScope text-to-video model
            self.text2video_model = DiffusionPipeline.from_pretrained(
                settings.MODEL_ID_TEXT2VIDEO,
                torch_dtype=torch.float16 if settings.MIXED_PRECISION and self.device.startswith("cuda") else torch.float32,
                cache_dir=str(settings.MODEL_CACHE),
            )
            
            if self.device.startswith("cuda"):
                self.text2video_model = self.text2video_model.to(self.device)
                if settings.MIXED_PRECISION:
                    self.text2video_model.enable_xformers_memory_efficient_attention()
            
            self.text2video_model.enable_attention_slicing()
            
            # Load image generation model as fallback
            logger.info(f"Loading image model: {settings.MODEL_ID_IMAGE}")
            
            self.image_model = StableDiffusionPipeline.from_pretrained(
                settings.MODEL_ID_IMAGE,
                torch_dtype=torch.float16 if settings.MIXED_PRECISION and self.device.startswith("cuda") else torch.float32,
                cache_dir=str(settings.MODEL_CACHE),
            )
            
            if self.device.startswith("cuda"):
                self.image_model = self.image_model.to(self.device)
            
            self.image_model.enable_attention_slicing()
            
            self.is_loaded = True
            logger.info("All models loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            logger.warning("Will use fallback mode with placeholder generation")
            return False
    
    def unload_models(self):
        """Unload models to free GPU memory."""
        if self.text2video_model is not None:
            del self.text2video_model
            self.text2video_model = None
        
        if self.image_model is not None:
            del self.image_model
            self.image_model = None
        
        gc.collect()
        
        if self.device.startswith("cuda"):
            import torch
            torch.cuda.empty_cache()
        
        self.is_loaded = False
        logger.info("Models unloaded")
    
    def generate_clip(
        self,
        prompt: str,
        duration_seconds: int = 4,
        fps: int = 24,
        width: int = 512,
        height: int = 512,
        num_frames: Optional[int] = None,
        seed: Optional[int] = None,
        output_path: Optional[Path] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Generate a single video clip from a text prompt.
        
        Args:
            prompt: Text description of the scene
            duration_seconds: Duration of the clip in seconds
            fps: Frames per second
            width: Video width in pixels
            height: Video height in pixels
            num_frames: Number of frames (overrides duration/fps if specified)
            seed: Random seed for reproducibility
            output_path: Directory to save frames
            progress_callback: Callback function for progress updates
            
        Returns:
            Dictionary with clip information and frame paths
        """
        if num_frames is None:
            num_frames = duration_seconds * fps
        
        # Ensure we don't exceed model limits
        max_frames = getattr(settings, 'MAX_FRAMES_PER_CLIP', 48)
        num_frames = min(num_frames, max_frames)
        
        logger.info(f"Generating clip: {prompt[:50]}... ({num_frames} frames)")
        
        # Create output directory for frames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        clip_id = f"clip_{timestamp}"
        
        if output_path is None:
            output_path = settings.FRAME_OUTPUT_DIR / clip_id
        else:
            output_path = Path(output_path) / clip_id
        
        output_path.mkdir(parents=True, exist_ok=True)
        
        frames = []
        
        try:
            if self.text2video_model is not None and self.is_loaded:
                # Generate video frames using text-to-video model
                logger.info("Using text-to-video model")
                
                generator = None
                if seed is not None:
                    import torch
                    generator = torch.Generator(device=self.device).manual_seed(seed)
                
                # Generate video
                output = self.text2video_model(
                    prompt=prompt,
                    num_frames=num_frames,
                    height=height,
                    width=width,
                    num_inference_steps=25,
                    guidance_scale=9.0,
                    generator=generator,
                    callback=progress_callback
                )
                
                frames = output.frames[0] if hasattr(output, 'frames') else []
                
            elif self.image_model is not None and self.is_loaded:
                # Fallback: Generate individual frames with image model
                logger.info("Using image model for frame-by-frame generation")
                
                for frame_idx in range(num_frames):
                    # Add slight variation to prompt for each frame
                    frame_prompt = f"{prompt}, frame {frame_idx + 1} of {num_frames}"
                    
                    if seed is not None:
                        import torch
                        generator = torch.Generator(device=self.device).manual_seed(seed + frame_idx)
                    else:
                        generator = None
                    
                    result = self.image_model(
                        prompt=frame_prompt,
                        height=height,
                        width=width,
                        num_inference_steps=20,
                        guidance_scale=7.5,
                        generator=generator
                    )
                    
                    frame = result.images[0]
                    frames.append(frame)
                    
                    if progress_callback:
                        progress_callback(frame_idx + 1, num_frames)
            
            else:
                # Fallback mode: Generate placeholder frames
                logger.warning("No models available, generating placeholder frames")
                frames = self._generate_placeholder_frames(
                    prompt, num_frames, width, height, progress_callback
                )
            
            # Save frames
            saved_paths = []
            for idx, frame in enumerate(frames):
                # Apply color grading
                frame_array = np.array(frame)
                style_config = settings.STYLE_PRESETS.get("ocean", {})
                color_grade = style_config.get("color_grading", "deep_ocean")
                graded_frame = apply_color_grading(frame_array, color_grade)
                
                # Convert back to PIL Image
                graded_frame_pil = Image.fromarray(graded_frame)
                
                # Save frame
                frame_path = output_path / f"frame_{idx:04d}.png"
                graded_frame_pil.save(frame_path, quality=95)
                saved_paths.append(str(frame_path))
            
            clip_info = {
                "clip_id": clip_id,
                "prompt": prompt,
                "num_frames": len(frames),
                "fps": fps,
                "duration": len(frames) / fps,
                "width": width,
                "height": height,
                "frame_paths": saved_paths,
                "output_dir": str(output_path),
                "seed": seed,
                "generated_at": datetime.now().isoformat()
            }
            
            logger.info(f"Generated clip with {len(frames)} frames at {output_path}")
            return clip_info
            
        except Exception as e:
            logger.error(f"Error generating clip: {e}")
            raise
    
    def _generate_placeholder_frames(
        self,
        prompt: str,
        num_frames: int,
        width: int,
        height: int,
        progress_callback: Optional[callable] = None
    ) -> List[Image.Image]:
        """
        Generate placeholder frames when no models are available.
        Creates gradient-based abstract nature-like patterns.
        
        Args:
            prompt: Text prompt (used for color selection)
            num_frames: Number of frames to generate
            width: Frame width
            height: Frame height
            progress_callback: Progress callback
            
        Returns:
            List of PIL Images
        """
        logger.warning("Generating placeholder frames (no AI models)")
        
        frames = []
        
        # Determine base colors from prompt keywords
        prompt_lower = prompt.lower()
        if "ocean" in prompt_lower or "blue" in prompt_lower or "water" in prompt_lower:
            base_colors = [(0, 20, 60), (0, 60, 120), (0, 100, 160)]
        elif "jungle" in prompt_lower or "green" in prompt_lower or "forest" in prompt_lower:
            base_colors = [(0, 40, 20), (20, 80, 40), (40, 120, 60)]
        elif "arctic" in prompt_lower or "ice" in prompt_lower or "snow" in prompt_lower:
            base_colors = [(180, 200, 220), (150, 180, 210), (120, 160, 200)]
        elif "sunset" in prompt_lower or "orange" in prompt_lower or "warm" in prompt_lower:
            base_colors = [(180, 60, 20), (200, 100, 40), (220, 140, 60)]
        else:
            base_colors = [(20, 40, 80), (40, 80, 120), (60, 120, 160)]
        
        for frame_idx in range(num_frames):
            # Create gradient background
            img_array = np.zeros((height, width, 3), dtype=np.uint8)
            
            # Vertical gradient with slight animation
            t = frame_idx / num_frames
            for y in range(height):
                # Interpolate between colors based on y position and time
                ratio = y / height
                animated_ratio = (ratio + t * 0.2) % 1.0
                
                color_idx = int(animated_ratio * len(base_colors)) % len(base_colors)
                next_color_idx = (color_idx + 1) % len(base_colors)
                local_ratio = (animated_ratio * len(base_colors)) % 1.0
                
                r = int(base_colors[color_idx][0] * (1 - local_ratio) + base_colors[next_color_idx][0] * local_ratio)
                g = int(base_colors[color_idx][1] * (1 - local_ratio) + base_colors[next_color_idx][1] * local_ratio)
                b = int(base_colors[color_idx][2] * (1 - local_ratio) + base_colors[next_color_idx][2] * local_ratio)
                
                img_array[y, :] = [r, g, b]
            
            # Add some noise for texture
            noise = np.random.randint(-20, 20, (height, width, 3), dtype=np.int16)
            img_array = np.clip(img_array.astype(np.int16) + noise, 0, 255).astype(np.uint8)
            
            frames.append(Image.fromarray(img_array))
            
            if progress_callback:
                progress_callback(frame_idx + 1, num_frames)
        
        return frames
    
    def generate_from_images(
        self,
        image_paths: List[str],
        prompt: str = "",
        duration_seconds: int = 4,
        fps: int = 24
    ) -> Dict[str, Any]:
        """
        Generate video from a sequence of images (image-to-video).
        
        Args:
            image_paths: List of paths to input images
            prompt: Optional text prompt for guidance
            duration_seconds: Output video duration
            fps: Output frame rate
            
        Returns:
            Clip information dictionary
        """
        logger.info(f"Generating video from {len(image_paths)} images")
        
        # This would use an image-to-video model like Stable Video Diffusion
        # For now, we'll create a simple interpolation
        
        try:
            import cv2
            
            # Load images
            images = []
            for path in image_paths:
                img = cv2.imread(path)
                if img is not None:
                    images.append(img)
            
            if len(images) < 2:
                raise ValueError("Need at least 2 images for interpolation")
            
            # Calculate total frames needed
            total_frames = duration_seconds * fps
            
            # Simple frame interpolation
            interpolated_frames = []
            frames_per_transition = total_frames // (len(images) - 1)
            
            for i in range(len(images) - 1):
                img1 = images[i]
                img2 = images[i + 1]
                
                for j in range(frames_per_transition):
                    alpha = j / frames_per_transition
                    blended = cv2.addWeighted(img1, 1 - alpha, img2, alpha, 0)
                    interpolated_frames.append(blended)
            
            # Add last frame
            interpolated_frames.append(images[-1])
            
            # Save frames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            clip_id = f"clip_img_{timestamp}"
            output_path = settings.FRAME_OUTPUT_DIR / clip_id
            output_path.mkdir(parents=True, exist_ok=True)
            
            saved_paths = []
            for idx, frame in enumerate(interpolated_frames):
                frame_path = output_path / f"frame_{idx:04d}.png"
                cv2.imwrite(str(frame_path), frame)
                saved_paths.append(str(frame_path))
            
            return {
                "clip_id": clip_id,
                "prompt": prompt,
                "num_frames": len(interpolated_frames),
                "fps": fps,
                "duration": len(interpolated_frames) / fps,
                "frame_paths": saved_paths,
                "output_dir": str(output_path),
                "source_type": "images",
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating video from images: {e}")
            raise


# Global pipeline instance
pipeline = VideoGenerationPipeline()
