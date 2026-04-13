#!/bin/bash

# Text-to-Video Nature Generator - Startup Script
# This script sets up and runs the application

set -e

echo "========================================"
echo "🌊 Text-to-Video Nature Generator"
echo "========================================"

# Check Python version
python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
echo "✓ Python version: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p outputs/{videos,audio,frames,logs}
mkdir -p models
mkdir -p presets

# Check for FFmpeg
if command -v ffmpeg &> /dev/null; then
    ffmpeg_version=$(ffmpeg -version | head -n1)
    echo "✓ FFmpeg found: $ffmpeg_version"
else
    echo "⚠️  WARNING: FFmpeg not found. Please install FFmpeg for video processing."
    echo "   On Ubuntu/Debian: sudo apt-get install ffmpeg"
    echo "   On macOS: brew install ffmpeg"
    echo "   On Windows: Download from ffmpeg.org"
fi

# Check CUDA availability
echo ""
echo "🎮 Checking GPU acceleration..."
python3 -c "
import torch
if torch.cuda.is_available():
    print(f'✓ CUDA available: {torch.cuda.get_device_name(0)}')
    print(f'  CUDA version: {torch.version.cuda}')
else:
    print('⚠️  CUDA not available - will use CPU mode')
    print('  Video generation will be slower')
" || echo "⚠️  PyTorch not installed yet"

echo ""
echo "========================================"
echo "Choose startup mode:"
echo "========================================"
echo "1) Start FastAPI backend only (port 8000)"
echo "2) Start Gradio UI only (port 7860)"
echo "3) Start both services"
echo "4) Interactive Python shell"
echo ""
read -p "Enter choice (1-4): " choice

case $choice in
    1)
        echo ""
        echo "🚀 Starting FastAPI backend..."
        echo "   API docs: http://localhost:8000/docs"
        echo ""
        cd backend && python main.py
        ;;
    2)
        echo ""
        echo "🎨 Starting Gradio UI..."
        echo "   UI: http://localhost:7860"
        echo ""
        python frontend/app.py
        ;;
    3)
        echo ""
        echo "🚀 Starting both services..."
        echo ""
        
        # Start backend in background
        cd backend
        python main.py &
        BACKEND_PID=$!
        cd ..
        
        echo "   Backend PID: $BACKEND_PID"
        echo "   API docs: http://localhost:8000/docs"
        
        sleep 3
        
        # Start Gradio UI
        echo "   UI: http://localhost:7860"
        python frontend/app.py
        
        # Cleanup on exit
        kill $BACKEND_PID 2>/dev/null || true
        ;;
    4)
        echo ""
        echo "🐍 Starting Python interactive shell..."
        python3
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac
