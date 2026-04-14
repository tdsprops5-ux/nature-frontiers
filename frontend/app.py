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

# Add backend to path and ensure it's treated as a package
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

# Import backend modules (now works with proper __init__.py)
from config import settings
from utils import list_presets, get_preset_info, enhance_prompt
from pipeline import pipeline
from audio import audio_generator


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


# Create Gradio interface
with gr.Blocks(title=settings.APP_NAME, theme=gr.themes.Base()) as demo:
    
    gr.Markdown(f"""
    # 🌊 {settings.APP_NAME}
    
    Generate long-form nature videos from text prompts using AI.
    Supports videos up to {settings.MAX_DURATION_MINUTES} minutes.
    """)
    
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
    video_output = gr.Video(label="Generated Video")
    
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
    
    # Footer
    gr.Markdown(f"""
    ---
    **Version:** {settings.APP_VERSION} | 
    **Device:** {settings.device} |
    **Max Duration:** {settings.MAX_DURATION_MINUTES} minutes
    
    Generated videos are saved to: `{settings.VIDEO_OUTPUT_DIR}`
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
