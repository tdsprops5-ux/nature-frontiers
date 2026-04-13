"""
Main FastAPI application for the Text-to-Video Nature Generator.
Provides REST API endpoints for video generation, batch processing, and status monitoring.
"""

import os
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio
from loguru import logger
from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from pipeline import pipeline, VideoGenerationPipeline
from video_builder import builder, VideoBuilder
from audio import audio_generator, AudioGenerator
from utils import (
    enhance_prompt, generate_prompt_variations, generate_seo_metadata,
    save_seo_metadata, list_presets, get_preset_info, calculate_clip_count,
    generate_batch_id
)


# Configure logging
logger.remove()
logger.add(
    str(settings.LOG_FILE),
    level=settings.LOG_LEVEL,
    rotation="10 MB",
    retention="7 days"
)
logger.add(
    sys.stdout,
    level=settings.LOG_LEVEL,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Generate long-form nature videos from text prompts using AI",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Can be restricted in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class GenerationRequest(BaseModel):
    """Request model for video generation."""
    prompt: str = Field(..., description="Text prompt describing the desired video")
    style: str = Field(default="ocean", description="Style preset (ocean, deep_sea, coral_reef, wildlife, jungle, arctic)")
    duration_minutes: int = Field(default=5, ge=1, le=180, description="Video duration in minutes (1-180)")
    resolution: str = Field(default="1920x1080", description="Output resolution")
    fps: int = Field(default=30, ge=24, le=60, description="Frame rate")
    target_fps: int = Field(default=60, ge=30, le=60, description="Target FPS after interpolation")
    clip_duration: int = Field(default=8, ge=4, le=10, description="Individual clip duration in seconds")
    enable_audio: bool = Field(default=True, description="Enable audio generation")
    audio_type: str = Field(default="ambient", description="Audio type (narration, ambient, both)")
    narration_text: Optional[str] = Field(default=None, description="Custom narration text")
    quality: str = Field(default="high", description="Quality preset (low, medium, high, ultra)")
    transition_type: str = Field(default="crossfade", description="Transition type between clips")
    seed: Optional[int] = Field(default=None, description="Random seed for reproducibility")
    batch_id: Optional[str] = Field(default=None, description="Batch ID for tracking")


class GenerationResponse(BaseModel):
    """Response model for video generation."""
    status: str
    job_id: str
    message: str
    estimated_time_minutes: float
    output_path: Optional[str] = None
    preview_path: Optional[str] = None
    seo_metadata: Optional[Dict[str, Any]] = None


class JobStatus(BaseModel):
    """Job status information."""
    job_id: str
    status: str  # pending, running, completed, failed
    progress: float  # 0-100
    current_step: str
    created_at: str
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


# Global state for job tracking
job_queue: Dict[str, Dict[str, Any]] = {}


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Device: {settings.device}")
    logger.info(f"Output directory: {settings.OUTPUT_DIR}")
    
    # Pre-load models in background
    asyncio.create_task(preload_models())


async def preload_models():
    """Pre-load AI models asynchronously."""
    try:
        logger.info("Pre-loading AI models...")
        pipeline.load_models()
        if settings.ENABLE_AUDIO:
            audio_generator.load_models()
        logger.info("Models loaded successfully")
    except Exception as e:
        logger.warning(f"Model pre-loading failed: {e}")
        logger.info("Models will be loaded on first request")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "device": settings.device,
        "endpoints": {
            "generate": "/generate",
            "presets": "/presets",
            "status": "/status/{job_id}",
            "jobs": "/jobs",
            "download": "/download/{filename}"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "device": settings.device,
        "models_loaded": pipeline.is_loaded
    }


@app.post("/generate", response_model=GenerationResponse)
async def generate_video(request: GenerationRequest, background_tasks: BackgroundTasks):
    """
    Generate a video from a text prompt.
    
    This endpoint starts the video generation process and returns immediately.
    Use the job_id to check status via /status/{job_id}.
    """
    job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{generate_batch_id().split('_')[-1]}"
    
    logger.info(f"Received generation request: {request.prompt[:50]}...")
    logger.info(f"Job ID: {job_id}")
    
    # Validate request
    if request.duration_minutes > settings.MAX_DURATION_MINUTES:
        raise HTTPException(
            status_code=400,
            detail=f"Duration exceeds maximum of {settings.MAX_DURATION_MINUTES} minutes"
        )
    
    # Enhance prompt with style
    enhanced_prompt = enhance_prompt(request.prompt, request.style)
    
    # Calculate number of clips needed
    num_clips = calculate_clip_count(request.duration_minutes, request.clip_duration)
    
    # Estimate generation time (rough estimate)
    estimated_time = num_clips * 2  # ~2 minutes per clip on GPU, much longer on CPU
    
    if not settings.USE_CUDA or settings.device == "cpu":
        estimated_time *= 20  # CPU is much slower
    
    # Create job entry
    job_queue[job_id] = {
        "status": "pending",
        "progress": 0,
        "current_step": "Initializing",
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "request": request.dict(),
        "enhanced_prompt": enhanced_prompt,
        "num_clips": num_clips,
        "error_message": None,
        "result": None
    }
    
    # Start generation in background
    background_tasks.add_task(process_generation, job_id, request, enhanced_prompt)
    
    return GenerationResponse(
        status="pending",
        job_id=job_id,
        message=f"Video generation started. Estimated time: {estimated_time:.1f} minutes",
        estimated_time_minutes=estimated_time
    )


async def process_generation(job_id: str, request: GenerationRequest, enhanced_prompt: str):
    """Process video generation in background."""
    try:
        job = job_queue[job_id]
        job["status"] = "running"
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        style_name = request.style
        
        # Output paths
        output_filename = f"{timestamp}_{style_name}_final.mp4"
        output_path = settings.VIDEO_OUTPUT_DIR / output_filename
        
        preview_filename = f"{timestamp}_{style_name}_preview.mp4"
        preview_path = settings.VIDEO_OUTPUT_DIR / preview_filename
        
        # Step 1: Generate prompt variations for diverse clips
        job["current_step"] = "Generating prompt variations"
        job["progress"] = 5
        
        prompt_variations = generate_prompt_variations(enhanced_prompt, request.num_clips)
        
        # Step 2: Generate individual clips
        job["current_step"] = "Generating video clips"
        clip_dirs = []
        
        for idx, prompt in enumerate(prompt_variations):
            job["current_step"] = f"Generating clip {idx + 1}/{len(prompt_variations)}"
            job["progress"] = 10 + (idx / len(prompt_variations)) * 60
            
            logger.info(f"Generating clip {idx + 1}: {prompt[:40]}...")
            
            # Determine resolution
            width, height = map(int, request.resolution.split('x'))
            
            # For very long videos, use lower resolution for speed
            if request.duration_minutes > 60:
                width = min(width, 1280)
                height = min(height, 720)
            
            clip_info = pipeline.generate_clip(
                prompt=prompt,
                duration_seconds=request.clip_duration,
                fps=request.fps,
                width=width,
                height=height,
                seed=request.seed + idx if request.seed else None
            )
            
            clip_dirs.append(clip_info["output_dir"])
        
        # Step 3: Build final video
        job["current_step"] = "Building final video"
        job["progress"] = 75
        
        logger.info("Building final video from clips")
        
        video_info = builder.build_video(
            clip_dirs=clip_dirs,
            output_path=output_path,
            fps=request.fps,
            target_fps=request.target_fps,
            transition_type=request.transition_type,
            enable_interpolation=request.target_fps > request.fps,
            resolution=tuple(map(int, request.resolution.split('x')))
        )
        
        # Step 4: Generate audio if enabled
        audio_path = None
        if request.enable_audio:
            job["current_step"] = "Generating audio"
            job["progress"] = 85
            
            if request.audio_type in ["narration", "both"] and request.narration_text:
                # Generate narration
                narration_path = settings.AUDIO_OUTPUT_DIR / f"{timestamp}_narration.wav"
                audio_generator.generate_narration(
                    text=request.narration_text,
                    output_path=narration_path
                )
                audio_path = narration_path
                
            elif request.audio_type in ["ambient", "both"]:
                # Generate ambient sound
                ambient_path = settings.AUDIO_OUTPUT_DIR / f"{timestamp}_ambient.wav"
                audio_generator.generate_ambient_sound(
                    sound_type=request.style,
                    duration_seconds=video_info["duration_seconds"],
                    output_path=ambient_path
                )
                audio_path = ambient_path
            
            # Add audio to video
            if audio_path and audio_path.exists():
                job["current_step"] = "Adding audio to video"
                job["progress"] = 90
                
                final_with_audio = settings.VIDEO_OUTPUT_DIR / f"{timestamp}_{style_name}_with_audio.mp4"
                
                audio_generator.add_audio_to_video(
                    video_path=output_path,
                    audio_path=audio_path,
                    output_path=final_with_audio,
                    volume=0.3  # Lower volume for background
                )
                
                # Update output path
                output_path = final_with_audio
        
        # Step 5: Generate SEO metadata
        job["current_step"] = "Generating SEO metadata"
        job["progress"] = 95
        
        seo_data = generate_seo_metadata(
            prompt=request.prompt,
            duration_minutes=request.duration_minutes,
            style=request.style,
            video_filename=output_path.name
        )
        
        seo_path = save_seo_metadata(seo_data, settings.LOG_OUTPUT_DIR)
        
        # Create preview (first 30 seconds)
        job["current_step"] = "Creating preview"
        
        try:
            import subprocess
            
            preview_cmd = [
                "ffmpeg",
                "-y",
                "-i", str(output_path),
                "-t", "30",
                "-c", "copy",
                str(preview_path)
            ]
            
            subprocess.run(preview_cmd, capture_output=True, text=True, check=True)
        except Exception as e:
            logger.warning(f"Could not create preview: {e}")
            preview_path = None
        
        # Clean up temporary files
        if not settings.SAVE_INTERMEDIATE:
            builder.cleanup_temp()
        
        # Mark job as completed
        job["status"] = "completed"
        job["progress"] = 100
        job["current_step"] = "Completed"
        job["completed_at"] = datetime.now().isoformat()
        job["result"] = {
            "output_path": str(output_path),
            "preview_path": str(preview_path) if preview_path else None,
            "seo_metadata": seo_data,
            "video_info": video_info
        }
        
        logger.info(f"Video generation completed: {output_path}")
        
    except Exception as e:
        logger.error(f"Error in video generation: {e}")
        job["status"] = "failed"
        job["error_message"] = str(e)
        job["completed_at"] = datetime.now().isoformat()


@app.get("/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get the status of a video generation job."""
    if job_id not in job_queue:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = job_queue[job_id]
    
    return JobStatus(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        current_step=job["current_step"],
        created_at=job["created_at"],
        completed_at=job["completed_at"],
        error_message=job["error_message"],
        result=job["result"]
    )


@app.get("/jobs")
async def list_jobs(limit: int = 10, status: Optional[str] = None):
    """List recent video generation jobs."""
    jobs = []
    
    for job_id, job_data in reversed(list(job_queue.items())):
        if status and job_data["status"] != status:
            continue
        
        jobs.append({
            "job_id": job_id,
            "status": job_data["status"],
            "progress": job_data["progress"],
            "current_step": job_data["current_step"],
            "created_at": job_data["created_at"],
            "prompt": job_data["request"]["prompt"][:50] + "..." if len(job_data["request"]["prompt"]) > 50 else job_data["request"]["prompt"]
        })
        
        if len(jobs) >= limit:
            break
    
    return {"jobs": jobs, "total": len(jobs)}


@app.get("/presets")
async def get_presets():
    """Get all available style presets."""
    return {
        "presets": list_presets(),
        "styles": list(settings.STYLE_PRESETS.keys())
    }


@app.get("/preset/{preset_name}")
async def get_preset(preset_name: str):
    """Get information about a specific preset."""
    preset_info = get_preset_info(preset_name)
    
    if not preset_info:
        raise HTTPException(status_code=404, detail="Preset not found")
    
    return preset_info


@app.get("/download/{filename:path}")
async def download_file(filename: str):
    """Download a generated video file."""
    file_path = settings.VIDEO_OUTPUT_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="video/mp4"
    )


@app.delete("/job/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a pending or running job."""
    if job_id not in job_queue:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = job_queue[job_id]
    
    if job["status"] in ["completed", "failed"]:
        return {"message": "Job already finished", "status": job["status"]}
    
    job["status"] = "cancelled"
    job["completed_at"] = datetime.now().isoformat()
    job["error_message"] = "Cancelled by user"
    
    return {"message": "Job cancelled successfully"}


@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for real-time job status updates."""
    await websocket.accept()
    
    try:
        while True:
            if job_id not in job_queue:
                await websocket.send_json({"error": "Job not found"})
                break
            
            job = job_queue[job_id]
            
            await websocket.send_json({
                "job_id": job_id,
                "status": job["status"],
                "progress": job["progress"],
                "current_step": job["current_step"],
                "message": f"{job['current_step']} ({job['progress']:.1f}%)"
            })
            
            if job["status"] in ["completed", "failed", "cancelled"]:
                break
            
            await asyncio.sleep(1)
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting server on {settings.HOST}:{settings.PORT}")
    
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower()
    )
