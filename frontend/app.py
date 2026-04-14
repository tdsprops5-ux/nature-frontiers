"""
Gradio UI for the Text-to-Video Nature Generator.
Provides a simple web interface for video generation.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import gradio as gr
from loguru import logger
import json

# Add backend to path and ensure it's treated as a package
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

# Import backend modules (now works with proper __init__.py)
from config import settings
from utils import list_presets, get_preset_info, enhance_prompt
from pipeline import pipeline
from audio import audio_generator


def get_generated_videos():
    """Get list of all generated videos."""
    video_dir = settings.VIDEO_OUTPUT_DIR
    if not video_dir.exists():
        return []
    
    videos = []
    for ext in ["*.mp4", "*.avi", "*.mov"]:
        videos.extend(list(video_dir.glob(ext)))
    
    # Sort by modification time (newest first)
    videos.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    return videos


def get_video_metadata(video_path):
    """Extract metadata from video file."""
    try:
        stat = video_path.stat()
        size_mb = stat.st_size / (1024 * 1024)
        created = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
        
        # Try to find associated metadata file
        metadata_file = video_path.with_suffix(".json")
        metadata = {}
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
        
        return {
            "name": video_path.name,
            "path": str(video_path),
            "size_mb": round(size_mb, 2),
            "created": created,
            "metadata": metadata
        }
    except Exception as e:
        logger.error(f"Error getting metadata for {video_path}: {e}")
        return None


def list_videos_ui():
    """List all generated videos in a gallery format."""
    videos = get_generated_videos()
    
    if not videos:
        return [], "No videos generated yet."
    
    video_list = []
    info_text = f"Found {len(videos)} generated video(s):\n\n"
    
    for video_path in videos[:20]:  # Limit to 20 most recent
        meta = get_video_metadata(video_path)
        if meta:
            video_list.append(str(video_path))
            duration = meta.get('metadata', {}).get('duration_minutes', 'N/A')
            style = meta.get('metadata', {}).get('style', 'N/A')
            prompt = meta.get('metadata', {}).get('prompt', 'No prompt saved')[:80]
            
            info_text += f"🎬 **{meta['name']}**\n"
            info_text += f"   Size: {meta['size_mb']} MB | Created: {meta['created']}\n"
            info_text += f"   Style: {style} | Duration: {duration} min\n"
            info_text += f"   Prompt: {prompt}...\n\n"
    
    return video_list, info_text


def delete_video_ui(video_path):
    """Delete a specific video file."""
    if not video_path:
        return "❌ No video selected", []
    
    try:
        video_file = Path(video_path)
        if video_file.exists():
            # Delete video and associated files
            video_file.unlink()
            
            # Delete metadata if exists
            metadata_file = video_file.with_suffix(".json")
            if metadata_file.exists():
                metadata_file.unlink()
            
            # Delete audio if exists
            audio_file = video_file.with_name(f"{video_file.stem}_audio.wav")
            if audio_file.exists():
                audio_file.unlink()
            
            logger.info(f"Deleted video: {video_file.name}")
            return f"✅ Deleted: {video_file.name}", list_videos_ui()[0]
        else:
            return "❌ Video file not found", []
    except Exception as e:
        logger.error(f"Error deleting video: {e}")
        return f"❌ Error: {str(e)}", []


def initialize_models():
    """Initialize AI models."""
    try:
        logger.info("Loading AI models...")
        pipeline.load_models()
        if settings.ENABLE_AUDIO:
            audio_generator.load_models()
        return "✅ Models loaded successfully"
    except Exception as e:
        return f"⚠️ Model loading warning: {str(e)}"


def generate_video_ui(
    prompt,
    style,
    duration_minutes,
    resolution,
    fps,
    enable_audio,
    audio_type,
    quality,
    progress=gr.Progress()
):
    """Generate video through Gradio interface."""
    
    job_id = f"gradio_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    try:
        # Enhance prompt
        enhanced_prompt = enhance_prompt(prompt, style)
        
        yield f"🎬 Enhanced prompt: {enhanced_prompt[:100]}...", None
        
        # Calculate clips needed
        from utils import calculate_clip_count
        num_clips = calculate_clip_count(duration_minutes, 8)
        
        yield f"📊 Will generate {num_clips} clips for {duration_minutes} minute video", None
        
        # Generate prompt variations
        from utils import generate_prompt_variations
        prompt_variations = generate_prompt_variations(enhanced_prompt, num_clips)
        
        # Generate clips
        clip_dirs = []
        width, height = map(int, resolution.split('x'))
        
        for idx, prompt_var in enumerate(prompt_variations):
            yield f"🎥 Generating clip {idx + 1}/{num_clips}: {prompt_var[:50]}...", None
            
            clip_info = pipeline.generate_clip(
                prompt=prompt_var,
                duration_seconds=8,
                fps=fps,
                width=min(width, 1280),  # Limit for speed
                height=min(height, 720)
            )
            
            clip_dirs.append(clip_info["output_dir"])
            progress((idx + 1) / num_clips * 0.6)  # 60% for clip generation
        
        # Build video
        yield "🎞️ Building final video with transitions...", None
        
        output_path = settings.VIDEO_OUTPUT_DIR / f"{timestamp}_{style}_final.mp4"
        
        from video_builder import builder
        
        video_info = builder.build_video(
            clip_dirs=clip_dirs,
            output_path=output_path,
            fps=fps,
            target_fps=60,
            transition_type="crossfade",
            enable_interpolation=True
        )
        
        progress(0.8)
        yield f"✅ Video created: {output_path.name}", str(output_path)
        
        # Generate audio if enabled
        if enable_audio:
            yield "🔊 Generating ambient audio...", str(output_path)
            
            audio_path = settings.AUDIO_OUTPUT_DIR / f"{timestamp}_ambient.wav"
            
            audio_generator.generate_ambient_sound(
                sound_type=style,
                duration_seconds=video_info["duration_seconds"],
                output_path=audio_path
            )
            
            # Add audio to video
            final_path = settings.VIDEO_OUTPUT_DIR / f"{timestamp}_{style}_with_audio.mp4"
            
            audio_generator.add_audio_to_video(
                video_path=output_path,
                audio_path=audio_path,
                output_path=final_path,
                volume=0.3
            )
            
            progress(0.95)
            yield f"✅ Added audio track", str(final_path)
            
            output_path = final_path
        
        # Generate SEO metadata
        yield "📝 Generating SEO metadata...", str(output_path)
        
        from utils import generate_seo_metadata, save_seo_metadata
        
        seo_data = generate_seo_metadata(
            prompt=prompt,
            duration_minutes=duration_minutes,
            style=style,
            video_filename=output_path.name
        )
        
        save_seo_metadata(seo_data, settings.LOG_OUTPUT_DIR)
        
        progress(1.0)
        
        # Clean up
        if not settings.SAVE_INTERMEDIATE:
            builder.cleanup_temp()
        
        yield f"🎉 Generation complete! Saved to: {output_path}", str(output_path)
        
    except Exception as e:
        logger.error(f"Error in UI generation: {e}")
        yield f"❌ Error: {str(e)}", None


def get_preset_prompts():
    """Get preset prompts for dropdown."""
    presets = list_presets()
    return {p["name"]: p["prompt"] for p in presets}


def update_prompt_from_preset(preset_name):
    """Update prompt field when preset is selected."""
    if preset_name:
        preset_info = get_preset_info(preset_name)
        if preset_info:
            return preset_info["prompt"]
    return ""


# Create Gradio interface with multiple tabs
with gr.Blocks(title=settings.APP_NAME, theme=gr.themes.Base()) as demo:
    
    gr.Markdown(f"""
    # 🌊 {settings.APP_NAME}
    
    Generate long-form nature videos from text prompts using AI.
    Supports videos up to {settings.MAX_DURATION_MINUTES} minutes.
    """)
    
    # Create tabs for different sections
    with gr.Tabs():
        
        # Tab 1: Video Generation
        with gr.TabItem("🎬 Generate Video"):
            
            with gr.Row():
                with gr.Column(scale=2):
                    gr.Markdown("### 📝 Video Settings")
                    
                    # Prompt input
                    prompt_input = gr.Textbox(
                        label="Prompt",
                        placeholder="Describe your desired video scene (e.g., 'Deep ocean with bioluminescent creatures')",
                        lines=3
                    )
                    
                    # Preset selector
                    preset_dropdown = gr.Dropdown(
                        label="Or choose a preset",
                        choices=[""] + [p["name"] for p in list_presets()],
                        info="Select a preset to auto-fill the prompt"
                    )
                    
                    preset_dropdown.change(
                        fn=update_prompt_from_preset,
                        inputs=[preset_dropdown],
                        outputs=[prompt_input]
                    )
                    
                    # Style selector
                    style_selector = gr.Radio(
                        choices=list(settings.STYLE_PRESETS.keys()),
                        value="ocean",
                        label="Style Preset"
                    )
                    
                    # Duration slider
                    duration_slider = gr.Slider(
                        minimum=1,
                        maximum=settings.MAX_DURATION_MINUTES,
                        value=5,
                        step=1,
                        label="Duration (minutes)"
                    )
                    
                    # Resolution selector
                    resolution_selector = gr.Radio(
                        choices=["1920x1080", "1280x720", "1024x576"],
                        value="1280x720",
                        label="Resolution"
                    )
                    
                    # FPS selector
                    fps_selector = gr.Slider(
                        minimum=24,
                        maximum=60,
                        value=30,
                        step=6,
                        label="Frame Rate (FPS)"
                    )
                    
                with gr.Column(scale=1):
                    gr.Markdown("### ⚙️ Advanced Options")
                    
                    # Audio options
                    enable_audio = gr.Checkbox(
                        value=True,
                        label="Enable Audio"
                    )
                    
                    audio_type_selector = gr.Radio(
                        choices=["ambient", "narration", "both"],
                        value="ambient",
                        label="Audio Type"
                    )
                    
                    # Quality preset
                    quality_selector = gr.Radio(
                        choices=["low", "medium", "high"],
                        value="medium",
                        label="Quality Preset"
                    )
                    
                    # Model status
                    model_status = gr.Textbox(
                        label="Model Status",
                        interactive=False
                    )
                    
                    # Load models button
                    load_models_btn = gr.Button("🔄 Load/Reload Models", variant="secondary")
                    load_models_btn.click(
                        fn=initialize_models,
                        outputs=[model_status]
                    )
            
            # Generate button
            generate_btn = gr.Button("🎬 Generate Video", variant="primary", size="lg")
            
            # Progress and output
            progress_output = gr.Textbox(label="Progress", interactive=False)
            video_output = gr.Video(label="Generated Video Preview")
            
            # Examples
            gr.Markdown("### 💡 Example Prompts")
            
            examples = gr.Dataset(
                components=[prompt_input],
                samples=[
                    ["Deep ocean trench with glowing bioluminescent jellyfish, dark blue water, mysterious atmosphere"],
                    ["Peaceful coral reef ecosystem with colorful tropical fish swimming gently"],
                    ["Arctic ice landscape with polar bear walking on ice floe, aurora borealis in night sky"],
                    ["Dense rainforest canopy with morning mist and shafts of sunlight"],
                    ["Majestic eagle soaring over mountain peaks at golden hour"]
                ]
            )
            
            # Connect generate button
            generate_btn.click(
                fn=generate_video_ui,
                inputs=[
                    prompt_input,
                    style_selector,
                    duration_slider,
                    resolution_selector,
                    fps_selector,
                    enable_audio,
                    audio_type_selector,
                    quality_selector
                ],
                outputs=[progress_output, video_output]
            )
        
        # Tab 2: Video Gallery & Download
        with gr.TabItem("📁 Video Gallery"):
            
            gr.Markdown("### 🎬 Your Generated Videos")
            gr.Markdown("Browse, preview, and download your previously generated videos.")
            
            # Video gallery
            video_gallery = gr.Gallery(
                label="Video Gallery",
                show_label=False,
                columns=3,
                rows=2,
                height=400,
                object_fit="cover"
            )
            
            # Selected video info
            selected_video_path = gr.Textbox(
                label="Selected Video Path",
                interactive=False,
                visible=True
            )
            
            video_info_text = gr.Textbox(
                label="Video Details",
                lines=8,
                interactive=False
            )
            
            # Action buttons
            with gr.Row():
                refresh_btn = gr.Button("🔄 Refresh Gallery", variant="secondary")
                download_btn = gr.File(label="📥 Download Video", interactive=True)
                delete_btn = gr.Button("🗑️ Delete Video", variant="stop")
            
            # Status message
            gallery_status = gr.Textbox(label="Status", interactive=False)
            
            # Connect gallery functions
            refresh_btn.click(
                fn=list_videos_ui,
                outputs=[video_gallery, video_info_text]
            )
            
            # When a video is selected in gallery
            def select_video(video):
                if video:
                    meta = get_video_metadata(Path(video))
                    if meta:
                        return str(meta['path']), f"Selected: {meta['name']}\nSize: {meta['size_mb']} MB\nCreated: {meta['created']}\n\nMetadata:\n{json.dumps(meta.get('metadata', {}), indent=2)}"
                return "", "No video selected"
            
            # Auto-update when gallery selection changes (using hidden state)
            video_gallery.select(
                fn=lambda evt: select_video(evt.value if hasattr(evt, 'value') else None),
                inputs=None,
                outputs=[selected_video_path, video_info_text]
            )
            
            # Download button - create downloadable file
            def prepare_download(video_path):
                if video_path and Path(video_path).exists():
                    return video_path
                return None
            
            download_btn.change(
                fn=prepare_download,
                inputs=[selected_video_path],
                outputs=[download_btn]
            )
            
            # Delete button
            delete_btn.click(
                fn=delete_video_ui,
                inputs=[selected_video_path],
                outputs=[gallery_status, video_gallery]
            )
            
            # Auto-load videos on tab click
            demo.load(
                fn=list_videos_ui,
                outputs=[video_gallery, video_info_text]
            )
        
        # Tab 3: Workflow & Logs
        with gr.TabItem("📊 Workflow & Logs"):
            
            gr.Markdown("### 📈 Generation Workflow")
            gr.Markdown("Track the status of your video generation jobs.")
            
            # Current workflow status
            workflow_status = gr.Textbox(
                label="Current Workflow Status",
                lines=5,
                interactive=False,
                value="Ready to generate videos. Select 'Generate Video' tab to start."
            )
            
            # Log output
            gr.Markdown("### 📝 Recent Activity Log")
            
            log_output = gr.Textbox(
                label="Activity Log",
                lines=15,
                interactive=False,
                value="Application started successfully.\nWaiting for user input..."
            )
            
            # Refresh logs button
            refresh_logs_btn = gr.Button("🔄 Refresh Logs", variant="secondary")
            
            def get_recent_logs():
                """Get recent log entries."""
                log_file = settings.LOG_OUTPUT_DIR / "app.log"
                if log_file.exists():
                    try:
                        with open(log_file, 'r') as f:
                            lines = f.readlines()
                            # Get last 50 lines
                            recent = lines[-50:] if len(lines) > 50 else lines
                            return ''.join(recent)
                    except Exception as e:
                        return f"Error reading log file: {e}"
                return "No log file found yet. Logs will appear here after generating videos."
            
            refresh_logs_btn.click(
                fn=get_recent_logs,
                outputs=[log_output]
            )
    
    # Footer
    gr.Markdown(f"""
    ---
    **Version:** {settings.APP_VERSION} | 
    **Device:** {settings.device} |
    **Max Duration:** {settings.MAX_DURATION_MINUTES} minutes
    
    Generated videos are saved to: `{settings.VIDEO_OUTPUT_DIR}`
    
    ### Quick Start Guide:
    1. Go to **Generate Video** tab
    2. Enter a prompt or select a preset
    3. Adjust settings (duration, quality, etc.)
    4. Click **Generate Video**
    5. Wait for processing (progress shown in real-time)
    6. View and download from **Video Gallery** tab
    """)


if __name__ == "__main__":
    logger.info(f"Starting Gradio UI on port {settings.GRADIO_PORT}")
    
    # Initialize models on startup
    initialize_models()
    
    demo.launch(
        server_name="0.0.0.0",
        server_port=settings.GRADIO_PORT,
        share=False,
        show_error=True
    )
