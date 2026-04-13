const express = require('express');
const cors = require('cors');
const { v4: uuidv4 } = require('uuid');
const path = require('path');
const fs = require('fs');
const VideoGenerator = require('./videoGenerator');

const app = express();
const PORT = 3001;

app.use(cors());
app.use(express.json());
app.use('/outputs', express.static(path.join(__dirname, '../outputs')));
app.use(express.static(path.join(__dirname, '../frontend')));

// In-memory storage for batch jobs (in production, use a database)
const batchJobs = new Map();

// Initialize video generator
const videoGenerator = new VideoGenerator();

// Get all batches
app.get('/api/batches', (req, res) => {
  const batches = Array.from(batchJobs.values()).map(job => ({
    id: job.id,
    status: job.status,
    createdAt: job.createdAt,
    completedAt: job.completedAt,
    totalVideos: job.totalVideos,
    completedVideos: job.completedVideos,
    failedVideos: job.failedVideos,
    currentActivity: job.currentActivity,
    outputPaths: job.outputPaths || [],
  }));
  res.json(batches);
});

// Get status of a specific batch
app.get('/api/status/:batchId', (req, res) => {
  const { batchId } = req.params;
  const job = batchJobs.get(batchId);
  
  if (!job) {
    return res.status(404).json({ error: 'Batch not found' });
  }
  
  res.json({
    id: job.id,
    status: job.status,
    progress: job.completedVideos / job.totalVideos * 100,
    totalVideos: job.totalVideos,
    completedVideos: job.completedVideos,
    failedVideos: job.failedVideos,
    currentActivity: job.currentActivity,
    createdAt: job.createdAt,
    completedAt: job.completedAt,
    outputPaths: job.outputPaths || [],
    errors: job.errors || [],
  });
});

// Start batch generation
app.post('/api/generate-batch', async (req, res) => {
  try {
    const {
      numVideos = 10,
      videoDuration = 180, // 180 minutes
      theme = 'ocean',
      includeVoiceOver = true,
      voiceType = 'natural',
      outputFormat = 'mp4',
      resolution = '1920x1080',
      fps = 30,
    } = req.body;

    const batchId = uuidv4();
    
    const job = {
      id: batchId,
      status: 'pending',
      createdAt: new Date().toISOString(),
      completedAt: null,
      totalVideos: numVideos,
      completedVideos: 0,
      failedVideos: 0,
      currentActivity: 'Initializing...',
      outputPaths: [],
      errors: [],
      config: {
        numVideos,
        videoDuration,
        theme,
        includeVoiceOver,
        voiceType,
        outputFormat,
        resolution,
        fps,
      },
    };

    batchJobs.set(batchId, job);
    
    // Start processing in background
    processBatch(batchId, job).catch(err => {
      console.error('Batch processing error:', err);
      job.status = 'failed';
      job.currentActivity = `Failed: ${err.message}`;
      job.errors.push(err.message);
    });

    res.json({
      success: true,
      batchId,
      message: `Batch generation started with ${numVideos} videos`,
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

async function processBatch(batchId, job) {
  try {
    job.status = 'processing';
    job.currentActivity = 'Starting batch processing...';
    
    const outputDir = path.join(__dirname, '../outputs', batchId);
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }

    for (let i = 0; i < job.totalVideos; i++) {
      job.currentActivity = `Processing video ${i + 1}/${job.totalVideos}`;
      
      try {
        const videoPath = await videoGenerator.generateVideo({
          ...job.config,
          videoNumber: i + 1,
          outputDir,
          onProgress: (progress) => {
            job.currentActivity = `Video ${i + 1}: ${progress}`;
          },
        });

        job.outputPaths.push(videoPath);
        job.completedVideos++;
      } catch (error) {
        job.failedVideos++;
        job.errors.push(`Video ${i + 1}: ${error.message}`);
        console.error(`Error generating video ${i + 1}:`, error);
      }

      // Update job in storage
      batchJobs.set(batchId, job);
    }

    job.status = 'completed';
    job.completedAt = new Date().toISOString();
    job.currentActivity = 'Batch completed!';
    
  } catch (error) {
    job.status = 'failed';
    job.currentActivity = `Failed: ${error.message}`;
    job.errors.push(error.message);
  }
}

app.listen(PORT, () => {
  console.log(`Backend server running on http://localhost:${PORT}`);
  console.log(`Output directory: ${path.join(__dirname, '../outputs')}`);
});
