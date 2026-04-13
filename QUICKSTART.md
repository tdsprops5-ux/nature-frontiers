# Quick Start Guide

## Option 1: Run as Web Application (Recommended)

Since the environment has limited disk space, you can run this as a web application without installing Electron.

### Backend Server

```bash
# Install minimal dependencies
npm install express cors uuid

# Start the backend server
node backend/server.js
```

The server will start on http://localhost:3001

### Frontend UI

Open `frontend/index.html` directly in your browser, or serve it with a simple HTTP server:

```bash
# Option A: Using Python
cd frontend
python -m http.server 8080

# Option B: Using Node.js (if http-server is available)
npx http-server frontend -p 8080
```

Then open http://localhost:8080 in your browser.

## Option 2: Full Desktop App (Requires More Disk Space)

If you have sufficient disk space (>500MB free):

```bash
npm install
npm start
```

## API Testing

You can test the API directly using curl:

```bash
# Start a batch generation
curl -X POST http://localhost:3001/api/generate-batch \
  -H "Content-Type: application/json" \
  -d '{
    "numVideos": 3,
    "videoDuration": 5,
    "theme": "ocean",
    "includeVoiceOver": true
  }'

# Check batch status
curl http://localhost:3001/api/batches
```

## FFmpeg Requirement

For actual video generation, you need FFmpeg installed:

**Ubuntu/Debian:**
```bash
sudo apt-get update && sudo apt-get install -y ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Without FFmpeg**, the app will create placeholder files for demonstration purposes.
