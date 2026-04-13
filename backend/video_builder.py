"""
Video Builder module for the Text-to-Video Nature Generator.
Handles video stitching, transitions, interpolation, and final encoding.
"""

import os
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger

# Handle both relative and absolute imports
try:
    from .config import settings
except ImportError:
    from config import settings


class VideoBuilder:
    """
    Builds final videos from generated clips with transitions,
    frame interpolation, and professional encoding.
    """
    
    def __init__(self):
        self.temp_dir = settings.OUTPUT_DIR / "temp"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("Initialized VideoBuilder")
    
    def build_video(
        self,
        clip_dirs: List[str],
        output_path: Path,
        fps: int = 30,
        target_fps: int = 60,
        transition_type: str = "crossfade",
        transition_duration: float = 1.0,
        enable_interpolation: bool = True,
        resolution: Optional[tuple] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Build a complete video from multiple clip directories.
        
        Args:
            clip_dirs: List of directories containing frame sequences
            output_path: Final output video path
            fps: Source frame rate
            target_fps: Target frame rate after interpolation
            transition_type: Type of transition between clips
            transition_duration: Duration of transitions in seconds
            enable_interpolation: Enable frame interpolation for smoother motion
            resolution: Output resolution (width, height)
            progress_callback: Progress update callback
            
        Returns:
            Dictionary with video information
        """
        logger.info(f"Building video from {len(clip_dirs)} clips")
        
        if resolution is None:
            resolution = settings.resolution_tuple
        
        width, height = resolution
        
        # Step 1: Create individual clip videos
        clip_videos = []
        for idx, clip_dir in enumerate(clip_dirs):
            clip_path = self.temp_dir / f"clip_{idx:04d}.mp4"
            
            clip_info = self._create_clip_video(
                clip_dir=clip_dir,
                output_path=clip_path,
                fps=fps,
                width=width,
                height=height
            )
            
            clip_videos.append(clip_info)
            
            if progress_callback:
                progress_callback(idx + 1, len(clip_dirs), "Creating clips")
        
        # Step 2: Concatenate clips with transitions
        concatenated_path = self.temp_dir / "concatenated.mp4"
        
        concat_info = self._concatenate_clips(
            clip_videos=clip_videos,
            output_path=concatenated_path,
            transition_type=transition_type,
            transition_duration=transition_duration
        )
        
        if progress_callback:
            progress_callback(len(clip_dirs) + 1, len(clip_dirs) + 2, "Concatenating")
        
        # Step 3: Apply frame interpolation if enabled
        final_video_path = output_path
        
        if enable_interpolation and target_fps > fps:
            logger.info(f"Applying frame interpolation: {fps} -> {target_fps} FPS")
            
            interpolated_path = self.temp_dir / "interpolated.mp4"
            
            self._interpolate_frames(
                input_path=concatenated_path,
                output_path=interpolated_path,
                source_fps=fps,
                target_fps=target_fps
            )
            
            # Move interpolated video to final location
            interpolated_path.rename(final_video_path)
            
            if progress_callback:
                progress_callback(len(clip_dirs) + 2, len(clip_dirs) + 2, "Interpolating")
        else:
            # Just copy the concatenated video
            concatenated_path.rename(final_video_path)
        
        # Get video statistics
        video_stats = self._get_video_stats(final_video_path)
        
        result = {
            "output_path": str(final_video_path),
            "duration_seconds": video_stats.get("duration", 0),
            "resolution": f"{width}x{height}",
            "fps": target_fps if enable_interpolation else fps,
            "num_clips": len(clip_dirs),
            "file_size_mb": video_stats.get("size_mb", 0),
            "created_at": datetime.now().isoformat()
        }
        
        logger.info(f"Video built successfully: {final_video_path}")
        return result
    
    def _create_clip_video(
        self,
        clip_dir: str,
        output_path: Path,
        fps: int,
        width: int,
        height: int
    ) -> Dict[str, Any]:
        """
        Create a video file from a directory of frames.
        
        Args:
            clip_dir: Directory containing PNG frames
            output_path: Output video path
            fps: Frame rate
            width: Video width
            height: Video height
            
        Returns:
            Clip information dictionary
        """
        clip_dir = Path(clip_dir)
        
        # Check if frames exist
        frames = sorted(clip_dir.glob("frame_*.png"))
        
        if not frames:
            raise ValueError(f"No frames found in {clip_dir}")
        
        logger.info(f"Creating video from {len(frames)} frames in {clip_dir}")
        
        # Use FFmpeg to create video from frames
        ffmpeg_cmd = [
            "ffmpeg",
            "-y",  # Overwrite output
            "-framerate", str(fps),
            "-i", str(clip_dir / "frame_%04d.png"),
            "-vf", f"scale={width}:{height}",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "18",  # High quality
            "-pix_fmt", "yuv420p",
            "-an",  # No audio
            str(output_path)
        ]
        
        try:
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            return {
                "path": str(output_path),
                "frames": len(frames),
                "fps": fps,
                "duration": len(frames) / fps
            }
            
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg error: {e.stderr}")
            raise
    
    def _concatenate_clips(
        self,
        clip_videos: List[Dict[str, Any]],
        output_path: Path,
        transition_type: str = "crossfade",
        transition_duration: float = 1.0
    ) -> Dict[str, Any]:
        """
        Concatenate multiple video clips with transitions.
        
        Args:
            clip_videos: List of clip video information dictionaries
            output_path: Output video path
            transition_type: Transition type (crossfade, fade, none)
            transition_duration: Duration of each transition
            
        Returns:
            Concatenation result information
        """
        logger.info(f"Concatenating {len(clip_videos)} clips with {transition_type} transitions")
        
        if len(clip_videos) == 1:
            # Single clip, just copy
            import shutil
            shutil.copy(clip_videos[0]["path"], output_path)
            return {"path": str(output_path), "clips": 1}
        
        # Create concat list file
        concat_list_path = self.temp_dir / "concat_list.txt"
        
        with open(concat_list_path, 'w') as f:
            for clip in clip_videos:
                f.write(f"file '{clip['path']}'\n")
        
        if transition_type == "none":
            # Simple concatenation without transitions
            ffmpeg_cmd = [
                "ffmpeg",
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_list_path),
                "-c", "copy",
                str(output_path)
            ]
            
            try:
                subprocess.run(ffmpeg_cmd, capture_output=True, text=True, check=True)
                return {"path": str(output_path), "clips": len(clip_videos)}
            except subprocess.CalledProcessError as e:
                logger.error(f"FFmpeg concat error: {e.stderr}")
                raise
        else:
            # Crossfade transition
            # Build complex filter for crossfade
            num_clips = len(clip_videos)
            
            # Calculate total duration
            total_duration = sum(clip["duration"] for clip in clip_videos)
            
            # For simplicity, use xfade filter for adjacent clips
            filter_complex = ""
            
            if num_clips == 2:
                filter_complex = (
                    f"[0][1]xfade=transition={transition_type}:duration={transition_duration}:offset={clip_videos[0]['duration'] - transition_duration}[v]"
                )
            else:
                # Chain multiple xfades
                offset = clip_videos[0]["duration"] - transition_duration
                filter_complex = (
                    f"[0][1]xfade=transition={transition_type}:duration={transition_duration}:offset={offset}[v1];"
                )
                
                prev_output = "v1"
                for i in range(2, num_clips):
                    offset += clip_videos[i - 1]["duration"] - transition_duration
                    current_output = f"v{i}"
                    
                    if i == num_clips - 1:
                        current_output = "v"
                    
                    filter_complex += (
                        f"[{prev_output}][{i}]xfade=transition={transition_type}:duration={transition_duration}:offset={offset}[{current_output}];"
                    )
                    prev_output = current_output
            
            input_args = []
            for clip in clip_videos:
                input_args.extend(["-i", clip["path"]])
            
            ffmpeg_cmd = [
                "ffmpeg",
                "-y"
            ] + input_args + [
                "-filter_complex", filter_complex,
                "-map", "[v]",
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "18",
                "-pix_fmt", "yuv420p",
                "-an",
                str(output_path)
            ]
            
            try:
                subprocess.run(ffmpeg_cmd, capture_output=True, text=True, check=True)
                return {"path": str(output_path), "clips": len(clip_videos)}
            except subprocess.CalledProcessError as e:
                logger.error(f"FFmpeg xfade error: {e.stderr}")
                # Fallback to simple concat
                logger.warning("Falling back to simple concatenation")
                import shutil
                
                # Create new concat list with re-encoded clips
                simple_concat_path = self.temp_dir / "simple_concat.mp4"
                
                simple_cmd = [
                    "ffmpeg",
                    "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", str(concat_list_path),
                    "-c", "copy",
                    str(simple_concat_path)
                ]
                
                subprocess.run(simple_cmd, capture_output=True, text=True, check=True)
                shutil.move(simple_concat_path, output_path)
                
                return {"path": str(output_path), "clips": len(clip_videos), "fallback": True}
    
    def _interpolate_frames(
        self,
        input_path: Path,
        output_path: Path,
        source_fps: int,
        target_fps: int
    ):
        """
        Interpolate frames to increase frame rate using FFmpeg's minterpolate.
        
        Args:
            input_path: Input video path
            output_path: Output video path
            source_fps: Source frame rate
            target_fps: Target frame rate
        """
        logger.info(f"Interpolating frames from {source_fps} to {target_fps} FPS")
        
        # Calculate interpolation factor
        factor = target_fps / source_fps
        
        ffmpeg_cmd = [
            "ffmpeg",
            "-y",
            "-i", str(input_path),
            "-vf", f"minterpolate=fps={target_fps}:mi_mode=mci:me_mode=bidir",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-an",
            str(output_path)
        ]
        
        try:
            subprocess.run(ffmpeg_cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg interpolation error: {e.stderr}")
            # Fallback: duplicate frames
            logger.warning("Falling back to frame duplication")
            
            fallback_cmd = [
                "ffmpeg",
                "-y",
                "-i", str(input_path),
                "-vf", f"fps={target_fps}",
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "18",
                "-pix_fmt", "yuv420p",
                "-an",
                str(output_path)
            ]
            
            subprocess.run(fallback_cmd, capture_output=True, text=True, check=True)
    
    def _get_video_stats(self, video_path: Path) -> Dict[str, Any]:
        """
        Get video file statistics using ffprobe.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dictionary with video statistics
        """
        try:
            import subprocess
            import json
            
            # Get file size
            file_size_mb = video_path.stat().st_size / (1024 * 1024)
            
            # Get duration using ffprobe
            probe_cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                str(video_path)
            ]
            
            result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            
            duration = float(data.get("format", {}).get("duration", 0))
            
            # Get stream info
            video_stream = None
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video":
                    video_stream = stream
                    break
            
            width = video_stream.get("width", 0) if video_stream else 0
            height = video_stream.get("height", 0) if video_stream else 0
            fps_str = video_stream.get("r_frame_rate", "0/1") if video_stream else "0/1"
            
            # Parse FPS
            if "/" in fps_str:
                num, den = map(int, fps_str.split("/"))
                fps = num / den if den > 0 else 0
            else:
                fps = float(fps_str)
            
            return {
                "duration": duration,
                "size_mb": round(file_size_mb, 2),
                "width": width,
                "height": height,
                "fps": round(fps, 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting video stats: {e}")
            return {"duration": 0, "size_mb": 0, "width": 0, "height": 0, "fps": 0}
    
    def cleanup_temp(self):
        """Clean up temporary files."""
        import shutil
        
        if self.temp_dir.exists():
            try:
                shutil.rmtree(self.temp_dir)
                logger.info("Cleaned up temporary files")
            except Exception as e:
                logger.error(f"Error cleaning temp files: {e}")


# Global builder instance
builder = VideoBuilder()
