"""
Audio generation module for the Text-to-Video Nature Generator.
Handles TTS narration and background audio generation.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from loguru import logger

# Handle both relative and absolute imports
try:
    from .config import settings
except ImportError:
    from config import settings


class AudioGenerator:
    """
    Generates audio content including narration and ambient sounds.
    Uses local TTS models to avoid API dependencies.
    """
    
    def __init__(self):
        self.tts_model = None
        self.is_loaded = False
        self.device = settings.device
        
        logger.info(f"Initialized AudioGenerator on device: {self.device}")
    
    def load_models(self) -> bool:
        """
        Load TTS models for narration generation.
        
        Returns:
            True if models loaded successfully
        """
        if self.is_loaded:
            logger.info("TTS models already loaded")
            return True
        
        try:
            from TTS.api import TTS
            
            logger.info(f"Loading TTS model: {settings.MODEL_ID_TTS}")
            
            # Initialize TTS model
            self.tts_model = TTS(model_name=settings.MODEL_ID_TTS).to(self.device)
            
            self.is_loaded = True
            logger.info("TTS model loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error loading TTS model: {e}")
            logger.warning("Will use fallback mode for audio generation")
            return False
    
    def generate_narration(
        self,
        text: str,
        output_path: Path,
        speaker_wav: Optional[str] = None,
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Generate narration audio from text using TTS.
        
        Args:
            text: Text to convert to speech
            output_path: Output audio file path
            speaker_wav: Optional reference audio for voice cloning
            language: Language code
            
        Returns:
            Dictionary with audio information
        """
        logger.info(f"Generating narration: {text[:50]}...")
        
        # Ensure output directory exists
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            if self.tts_model is not None and self.is_loaded:
                # Use TTS model
                self.tts_model.tts_to_file(
                    text=text,
                    file_path=str(output_path),
                    speaker_wav=speaker_wav,
                    language=language
                )
                
                logger.info(f"Narration generated: {output_path}")
            else:
                # Fallback: Generate silent audio or simple tone
                logger.warning("No TTS model available, generating placeholder audio")
                self._generate_placeholder_audio(output_path, duration=len(text) * 0.1)
            
            # Get audio stats
            audio_stats = self._get_audio_stats(output_path)
            
            return {
                "output_path": str(output_path),
                "duration_seconds": audio_stats.get("duration", 0),
                "sample_rate": audio_stats.get("sample_rate", 44100),
                "text_length": len(text),
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating narration: {e}")
            raise
    
    def _generate_placeholder_audio(self, output_path: Path, duration: float = 5.0):
        """
        Generate a placeholder audio file when TTS is unavailable.
        Creates a silent WAV file.
        
        Args:
            output_path: Output file path
            duration: Duration in seconds
        """
        try:
            import wave
            import struct
            import math
            
            sample_rate = 44100
            num_samples = int(sample_rate * duration)
            
            # Generate silence (or very low amplitude noise)
            samples = []
            for i in range(num_samples):
                # Very subtle ambient noise
                t = i / sample_rate
                value = 100 * math.sin(2 * math.pi * 100 * t)  # Low frequency hum
                samples.append(int(value))
            
            # Write WAV file
            with wave.open(str(output_path), 'w') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                
                for sample in samples:
                    wav_file.writeframes(struct.pack('<h', sample))
            
            logger.info(f"Generated placeholder audio: {output_path}")
            
        except Exception as e:
            logger.error(f"Error generating placeholder audio: {e}")
            # Create empty file as last resort
            output_path.touch()
    
    def generate_ambient_sound(
        self,
        sound_type: str = "ocean",
        duration_seconds: float = 60.0,
        output_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Generate ambient background sounds procedurally.
        
        Args:
            sound_type: Type of ambient sound (ocean, rain, forest, etc.)
            duration_seconds: Duration of the audio
            output_path: Output file path
            
        Returns:
            Dictionary with audio information
        """
        logger.info(f"Generating ambient sound: {sound_type} for {duration_seconds}s")
        
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = settings.AUDIO_OUTPUT_DIR / f"ambient_{timestamp}.wav"
        else:
            output_path = Path(output_path)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            import numpy as np
            import wave
            import struct
            
            sample_rate = 44100
            num_samples = int(sample_rate * duration_seconds)
            
            # Generate different types of ambient sounds
            if sound_type == "ocean":
                samples = self._generate_ocean_sound(num_samples, sample_rate)
            elif sound_type == "rain":
                samples = self._generate_rain_sound(num_samples, sample_rate)
            elif sound_type == "forest":
                samples = self._generate_forest_sound(num_samples, sample_rate)
            elif sound_type == "wind":
                samples = self._generate_wind_sound(num_samples, sample_rate)
            else:
                samples = self._generate_ocean_sound(num_samples, sample_rate)
            
            # Normalize and convert to 16-bit
            max_val = max(abs(min(samples)), max(samples))
            if max_val > 0:
                samples = [int((s / max_val) * 32767 * 0.5) for s in samples]  # Reduce volume by 50%
            
            # Write stereo WAV
            with wave.open(str(output_path), 'w') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                
                for sample in samples:
                    wav_file.writeframes(struct.pack('<h', sample))
            
            return {
                "output_path": str(output_path),
                "duration_seconds": duration_seconds,
                "sample_rate": sample_rate,
                "sound_type": sound_type,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating ambient sound: {e}")
            # Fallback to placeholder
            self._generate_placeholder_audio(output_path, duration_seconds)
            
            return {
                "output_path": str(output_path),
                "duration_seconds": duration_seconds,
                "sample_rate": 44100,
                "sound_type": sound_type,
                "fallback": True,
                "generated_at": datetime.now().isoformat()
            }
    
    def _generate_ocean_sound(self, num_samples: int, sample_rate: int) -> List[float]:
        """Generate ocean wave sounds using synthesized audio."""
        import numpy as np
        import math
        
        samples = np.zeros(num_samples)
        t = np.arange(num_samples) / sample_rate
        
        # Low frequency waves (0.1-0.3 Hz)
        for freq in [0.1, 0.15, 0.2, 0.25]:
            amplitude = 0.3 / freq
            wave = amplitude * np.sin(2 * np.pi * freq * t)
            # Add some randomness
            noise = np.random.normal(0, 0.1, num_samples)
            samples += wave + noise
        
        # Higher frequency foam/bubbles (1-3 Hz)
        for freq in [1.0, 1.5, 2.0]:
            amplitude = 0.05
            wave = amplitude * np.sin(2 * np.pi * freq * t)
            samples += wave
        
        return samples.tolist()
    
    def _generate_rain_sound(self, num_samples: int, sample_rate: int) -> List[float]:
        """Generate rain sound using white noise with filtering."""
        import numpy as np
        
        # White noise base
        samples = np.random.normal(0, 0.3, num_samples)
        
        # Apply low-pass filter effect (simplified)
        filtered = np.zeros(num_samples)
        alpha = 0.1
        for i in range(1, num_samples):
            filtered[i] = alpha * samples[i] + (1 - alpha) * filtered[i-1]
        
        # Add occasional drops (higher amplitude spikes)
        drop_positions = np.random.choice(num_samples, size=num_samples // 100, replace=False)
        for pos in drop_positions:
            if pos < num_samples - 100:
                for j in range(100):
                    if pos + j < num_samples:
                        samples[pos + j] += 0.5 * np.exp(-j / 20) * np.random.random()
        
        return (samples + filtered).tolist()
    
    def _generate_forest_sound(self, num_samples: int, sample_rate: int) -> List[float]:
        """Generate forest ambience with bird-like chirps."""
        import numpy as np
        
        samples = np.zeros(num_samples)
        t = np.arange(num_samples) / sample_rate
        
        # Base wind/rustling (low frequency noise)
        noise = np.random.normal(0, 0.05, num_samples)
        samples += noise
        
        # Occasional bird chirps (high frequency bursts)
        chirp_interval = sample_rate * 3  # Every 3 seconds
        for start in range(0, num_samples, chirp_interval):
            if start + sample_rate < num_samples:  # 1 second chirp
                chirp_duration = min(sample_rate // 2, num_samples - start)
                for i in range(chirp_duration):
                    freq = 2000 + np.random.random() * 2000  # 2-4 kHz
                    envelope = np.exp(-i / (chirp_duration / 4))
                    samples[start + i] += 0.3 * envelope * np.sin(2 * np.pi * freq * i / sample_rate)
        
        return samples.tolist()
    
    def _generate_wind_sound(self, num_samples: int, sample_rate: int) -> List[float]:
        """Generate wind sound using filtered noise."""
        import numpy as np
        
        # Pink noise base
        samples = np.random.normal(0, 0.2, num_samples)
        
        # Multiple low-frequency oscillations
        t = np.arange(num_samples) / sample_rate
        for freq in [0.05, 0.1, 0.2]:
            modulation = 0.5 + 0.5 * np.sin(2 * np.pi * freq * t)
            samples *= modulation
        
        return samples.tolist()
    
    def merge_audio(
        self,
        audio_paths: List[str],
        output_path: Path,
        method: str = "concatenate"
    ) -> Dict[str, Any]:
        """
        Merge multiple audio files.
        
        Args:
            audio_paths: List of input audio file paths
            output_path: Output merged audio path
            method: Merge method (concatenate, mix)
            
        Returns:
            Dictionary with merged audio information
        """
        logger.info(f"Merging {len(audio_paths)} audio files using {method}")
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            import subprocess
            
            if method == "concatenate":
                # Create concat list
                concat_list_path = settings.OUTPUT_DIR / "temp" / "audio_concat.txt"
                concat_list_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(concat_list_path, 'w') as f:
                    for path in audio_paths:
                        f.write(f"file '{path}'\n")
                
                ffmpeg_cmd = [
                    "ffmpeg",
                    "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", str(concat_list_path),
                    "-c:a", "pcm_s16le",
                    str(output_path)
                ]
                
                subprocess.run(ffmpeg_cmd, capture_output=True, text=True, check=True)
                
            elif method == "mix":
                # Mix all audio files together
                inputs = []
                for path in audio_paths:
                    inputs.extend(["-i", path])
                
                filter_complex = f"[0:a]"
                for i in range(1, len(audio_paths)):
                    filter_complex += f"[{i}:a]"
                filter_complex += f"amix=inputs={len(audio_paths)}:duration=longest"
                
                ffmpeg_cmd = [
                    "ffmpeg",
                    "-y"
                ] + inputs + [
                    "-filter_complex", filter_complex,
                    "-c:a", "pcm_s16le",
                    str(output_path)
                ]
                
                subprocess.run(ffmpeg_cmd, capture_output=True, text=True, check=True)
            
            # Get stats
            audio_stats = self._get_audio_stats(output_path)
            
            return {
                "output_path": str(output_path),
                "duration_seconds": audio_stats.get("duration", 0),
                "num_inputs": len(audio_paths),
                "method": method,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error merging audio: {e}")
            raise
    
    def _get_audio_stats(self, audio_path: Path) -> Dict[str, Any]:
        """
        Get audio file statistics using ffprobe.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dictionary with audio statistics
        """
        try:
            import subprocess
            import json
            
            probe_cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                str(audio_path)
            ]
            
            result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            
            duration = float(data.get("format", {}).get("duration", 0))
            
            # Get stream info
            audio_stream = None
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "audio":
                    audio_stream = stream
                    break
            
            sample_rate = int(audio_stream.get("sample_rate", 44100)) if audio_stream else 44100
            
            return {
                "duration": duration,
                "sample_rate": sample_rate
            }
            
        except Exception as e:
            logger.error(f"Error getting audio stats: {e}")
            return {"duration": 0, "sample_rate": 44100}
    
    def add_audio_to_video(
        self,
        video_path: Path,
        audio_path: Path,
        output_path: Path,
        volume: float = 0.5
    ) -> Path:
        """
        Add audio track to a video file.
        
        Args:
            video_path: Input video path (no audio)
            audio_path: Audio file path
            output_path: Output video path with audio
            volume: Audio volume level (0.0-1.0)
            
        Returns:
            Path to output video
        """
        logger.info(f"Adding audio to video: {video_path} + {audio_path}")
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            import subprocess
            
            ffmpeg_cmd = [
                "ffmpeg",
                "-y",
                "-i", str(video_path),
                "-i", str(audio_path),
                "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease",
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "18",
                "-c:a", "aac",
                "-b:a", "192k",
                "-af", f"volume={volume}",
                "-shortest",
                "-pix_fmt", "yuv420p",
                str(output_path)
            ]
            
            subprocess.run(ffmpeg_cmd, capture_output=True, text=True, check=True)
            
            logger.info(f"Video with audio created: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error adding audio to video: {e}")
            raise


# Global audio generator instance
audio_generator = AudioGenerator()
