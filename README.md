# 🌊 Ocean & Wildlife Video Generator

A powerful desktop application for generating high-contrast ocean, nature, and wildlife videos with voice-over narration in batch mode.

## Features

- **180-Minute Video Generation**: Create long-form nature documentaries up to 180 minutes
- **Batch Processing**: Generate multiple videos simultaneously
- **High Contrast Visuals**: Enhanced visual effects for stunning imagery
- **Voice-Over Narration**: Automated voice-over with customizable voice types
- **Real-Time Activity Monitoring**: Watch every step of the generation process
- **Multiple Themes**:
  - Ocean/Marine Life
  - Nature Landscapes
  - Wildlife/Safari
- **Customizable Output**:
  - Resolution: HD, Full HD, 4K
  - Frame Rate: 24, 30, 60 FPS
  - Formats: MP4, MOV, AVI

## Architecture

```
├── main.js              # Electron main process
├── preload.js           # Electron preload script
├── backend/
│   ├── server.js        # Express API server
│   └── videoGenerator.js # Video generation logic
├── frontend/
│   ├── index.html       # Main UI
│   ├── css/
│   │   └── styles.css   # Application styles
│   └── js/
│       └── app.js       # Frontend application logic
└── outputs/             # Generated videos directory
```

## Installation

### Prerequisites

- Node.js (v16 or higher)
- npm or yarn
- FFmpeg (installed on your system)

### Steps

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Install FFmpeg:**
   
   **macOS:**
   ```bash
   brew install ffmpeg
   ```
   
   **Windows:**
   ```bash
   # Download from https://ffmpeg.org/download.html
   # Add to PATH
   ```
   
   **Linux:**
   ```bash
   sudo apt-get install ffmpeg
   ```

## Usage

### Development Mode

1. **Start the backend server:**
   ```bash
   npm run dev
   ```

2. **Start the Electron app (in another terminal):**
   ```bash
   npm start
   ```

### Production Build

```bash
npm run build
```

## Configuration Options

When creating a batch, you can configure:

- **Theme**: Choose between Ocean, Nature, or Wildlife
- **Number of Videos**: 1-100 videos per batch
- **Duration**: 1-180 minutes per video
- **Resolution**: 
  - 1280x720 (HD)
  - 1920x1080 (Full HD)
  - 3840x2160 (4K)
- **Frame Rate**: 24, 30, or 60 FPS
- **Output Format**: MP4, MOV, or AVI
- **Voice-Over**: Enable/disable narration
- **Voice Type**: Natural, Documentary Style, or Calm & Soothing

## UI Features

### Activity Monitor
- Real-time statistics dashboard
- Total, processing, completed, and failed batch counts
- Detailed activity log with timestamps

### Batch Jobs Panel
- Progress bars for each batch
- Current activity status
- Output file paths
- Error reporting

### Configuration Panel
- Easy-to-use form interface
- Preset options for common configurations
- Validation for input values

## API Endpoints

### POST `/api/generate-batch`
Start a new batch generation job.

**Request Body:**
```json
{
  "numVideos": 5,
  "videoDuration": 180,
  "theme": "ocean",
  "includeVoiceOver": true,
  "voiceType": "natural",
  "outputFormat": "mp4",
  "resolution": "1920x1080",
  "fps": 30
}
```

**Response:**
```json
{
  "success": true,
  "batchId": "uuid-here",
  "message": "Batch generation started with 5 videos"
}
```

### GET `/api/batches`
Get all batch jobs.

### GET `/api/status/:batchId`
Get status of a specific batch job.

## Future Enhancements

- [ ] Integration with AI video generation APIs (RunwayML, Pika Labs)
- [ ] Text-to-Speech integration (Google TTS, ElevenLabs, Amazon Polly)
- [ ] Stock footage library integration
- [ ] Custom script upload for voice-overs
- [ ] Video editing capabilities
- [ ] Cloud storage integration
- [ ] Scheduled batch jobs
- [ ] Export presets

## Troubleshooting

### FFmpeg not found
Ensure FFmpeg is installed and added to your system PATH.

### Port already in use
The backend runs on port 3001. If this port is occupied, modify the PORT variable in `backend/server.js`.

### Video generation fails
Check that you have sufficient disk space for 180-minute videos (can be several GB per video).

## License

MIT License

## Support

For issues and feature requests, please open an issue on the repository.
