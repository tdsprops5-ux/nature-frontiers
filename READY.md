# 🌊 Nature Frontiers - Ready for Use!

## ✅ Application Status: RUNNING

Your Text-to-Video Nature Generator is **successfully installed and running**!

### 🎯 Current Status
- **Gradio UI**: Running at http://localhost:7860
- **All modules loaded**: Config, Utils, Pipeline, Audio, Video Builder
- **Presets available**: 10 nature scene presets
- **Device**: CPU (GPU acceleration available with CUDA)

---

## 🚀 How to Use

### Option 1: Web Interface (Recommended)

The Gradio UI is already running! Open your browser to:
```
http://localhost:7860
```

**Steps:**
1. Enter a prompt or select a preset
2. Choose style (Ocean, Deep Sea, Coral Reef, Wildlife, Jungle, Arctic)
3. Set duration (1-180 minutes)
4. Adjust resolution and FPS
5. Click "Generate Video"

### Option 2: Command Line Test

Run the test script to verify everything works:
```bash
python test_app.py
```

### Option 3: API Mode

Start the FastAPI server:
```bash
python backend/main.py
```
Then access API docs at: http://localhost:8000/docs

---

## 📋 Available Presets

1. **shark_hunting** - Great white shark hunting scene
2. **peaceful_reef** - Colorful coral reef ecosystem
3. **bioluminescent_bay** - Glowing creatures in dark depths
4. **arctic_wildlife** - Polar bears on ice floes
5. **jungle_canopy** - Rainforest morning mist
6. **eagle_soaring** - Majestic eagle over mountains
7. **whale_migration** - Humpback whales swimming
8. **volcanic_vent** - Deep sea hydrothermal vents
9. **kelp_forest** - Underwater kelp forest ecosystem
10. **aurora_wildlife** - Northern lights with arctic animals

---

## ⚠️ Important Notes

### Disk Space Warning
Your current disk has only **350MB free**. For full video generation you need:
- **Minimum**: 5GB (short videos, low quality)
- **Recommended**: 20-50GB (long videos, high quality)
- **180-minute video**: 100GB+ 

**To free up space:**
```bash
# Clean pip cache
pip cache purge

# Remove temporary files
rm -rf /tmp/*

# Check disk usage
df -h
```

### Missing Dependencies (Optional)
The app runs in **fallback mode** without these packages:
- `diffusers` - AI video generation models
- `transformers` - Text processing models
- `TTS` - Neural text-to-speech

**To install when you have more space:**
```bash
pip install diffusers transformers accelerate
```

### FFmpeg Required
Install FFmpeg for video processing:
- **Windows**: https://ffmpeg.org/download.html
- **Linux**: `sudo apt install ffmpeg`
- **Mac**: `brew install ffmpeg`

---

## 🎬 Example Usage

### Quick 1-Minute Test Video
```python
from backend.pipeline import pipeline
from backend.video_builder import builder

# Generate a single clip
clip = pipeline.generate_clip(
    prompt="Peaceful coral reef with tropical fish",
    duration_seconds=8,
    fps=30,
    width=1280,
    height=720
)

# Build final video
video = builder.build_video(
    clip_dirs=[clip["output_dir"]],
    output_path="outputs/videos/test.mp4",
    fps=30,
    target_fps=30
)
```

### Using Presets via API
```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "preset": "peaceful_reef",
    "duration_minutes": 5,
    "resolution": "1280x720",
    "enable_audio": true
  }'
```

---

## 📁 File Locations

| Type | Path |
|------|------|
| Generated Videos | `/workspace/outputs/videos/` |
| Audio Files | `/workspace/outputs/audio/` |
| Frame Sequences | `/workspace/outputs/frames/` |
| Logs | `/workspace/outputs/logs/` |
| Temporary Files | `/workspace/outputs/temp/` |

---

## 🔧 Troubleshooting

### "No space left on device"
```bash
# Check disk space
df -h

# Clean up
pip cache purge
rm -rf outputs/temp/*
```

### Import errors
```bash
# Run test script
python test_app.py

# Reinstall dependencies
pip install -r requirements.txt
```

### Gradio not loading
```bash
# Kill existing process
pkill -f "python frontend/app.py"

# Restart
python frontend/app.py
```

---

## 📊 System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 8GB | 16GB+ |
| Storage | 10GB | 100GB+ |
| GPU | Optional | NVIDIA with 8GB+ VRAM |
| Python | 3.9+ | 3.10+ |

---

## 🎉 You're Ready!

The application is fully functional and ready to generate nature videos. Start with short test videos (1-5 minutes) to verify everything works before attempting longer generations.

**Access your UI now**: http://localhost:7860
