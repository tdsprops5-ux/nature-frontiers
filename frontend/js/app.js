// Ocean Wildlife Video Generator - Frontend Application

class VideoGeneratorApp {
    constructor() {
        this.batches = [];
        this.refreshInterval = null;
        this.init();
    }

    init() {
        this.cacheElements();
        this.attachEventListeners();
        this.loadBatches();
        this.startAutoRefresh();
        this.logActivity('Application initialized', 'info');
    }

    cacheElements() {
        // Form elements
        this.configForm = document.getElementById('configForm');
        this.generateBtn = document.getElementById('generateBtn');
        this.refreshBtn = document.getElementById('refreshBtn');

        // Stats elements
        this.totalBatchesEl = document.getElementById('totalBatches');
        this.processingBatchesEl = document.getElementById('processingBatches');
        this.completedBatchesEl = document.getElementById('completedBatches');
        this.failedBatchesEl = document.getElementById('failedBatches');

        // Activity log
        this.logEntriesEl = document.getElementById('logEntries');

        // Batches list
        this.batchesListEl = document.getElementById('batchesList');
    }

    attachEventListeners() {
        this.configForm.addEventListener('submit', (e) => this.handleFormSubmit(e));
        this.refreshBtn.addEventListener('click', () => this.loadBatches());
    }

    async handleFormSubmit(e) {
        e.preventDefault();

        const formData = new FormData(this.configForm);
        const config = {
            numVideos: parseInt(formData.get('numVideos')),
            videoDuration: parseInt(formData.get('videoDuration')),
            theme: formData.get('theme'),
            includeVoiceOver: formData.get('includeVoiceOver') === 'on',
            voiceType: formData.get('voiceType'),
            outputFormat: formData.get('outputFormat'),
            resolution: formData.get('resolution'),
            fps: parseInt(formData.get('fps')),
        };

        this.logActivity(`Starting batch generation: ${config.numVideos} videos, ${config.videoDuration}min each`, 'info');
        this.setGeneratingState(true);

        try {
            let result;
            
            // Check if we're in Electron or browser
            if (window.electronAPI) {
                result = await window.electronAPI.startBatchGeneration(config);
            } else {
                // Fallback to fetch API
                const response = await fetch('http://localhost:3001/api/generate-batch', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(config),
                });
                result = await response.json();
            }

            if (result.success) {
                this.logActivity(`Batch started successfully! ID: ${result.batchId}`, 'success');
                await this.loadBatches();
            } else {
                throw new Error(result.error || 'Failed to start batch');
            }
        } catch (error) {
            this.logActivity(`Error: ${error.message}`, 'error');
            alert(`Failed to start batch generation: ${error.message}`);
        } finally {
            this.setGeneratingState(false);
        }
    }

    async loadBatches() {
        try {
            let result;

            if (window.electronAPI) {
                result = await window.electronAPI.getAllBatches();
            } else {
                const response = await fetch('http://localhost:3001/api/batches');
                result = { success: true, data: await response.json() };
            }

            if (result.success) {
                this.batches = result.data;
                this.updateStats();
                this.renderBatches();
            }
        } catch (error) {
            console.error('Failed to load batches:', error);
            this.logActivity(`Failed to load batches: ${error.message}`, 'error');
        }
    }

    updateStats() {
        const total = this.batches.length;
        const processing = this.batches.filter(b => b.status === 'processing').length;
        const completed = this.batches.filter(b => b.status === 'completed').length;
        const failed = this.batches.filter(b => b.status === 'failed').length;

        this.totalBatchesEl.textContent = total;
        this.processingBatchesEl.textContent = processing;
        this.completedBatchesEl.textContent = completed;
        this.failedBatchesEl.textContent = failed;
    }

    renderBatches() {
        if (this.batches.length === 0) {
            this.batchesListEl.innerHTML = `
                <div class="empty-state">No batch jobs yet. Start your first generation!</div>
            `;
            return;
        }

        this.batchesListEl.innerHTML = this.batches.map(batch => this.renderBatchItem(batch)).join('');
    }

    renderBatchItem(batch) {
        const progress = batch.totalVideos > 0 
            ? Math.round((batch.completedVideos / batch.totalVideos) * 100) 
            : 0;

        const createdAt = new Date(batch.createdAt).toLocaleString();
        const completedAt = batch.completedAt ? new Date(batch.completedAt).toLocaleString() : 'In progress';

        return `
            <div class="batch-item ${batch.status}">
                <div class="batch-header">
                    <span class="batch-id">📁 ${batch.id.substring(0, 8)}...</span>
                    <span class="batch-status ${batch.status}">${batch.status}</span>
                </div>
                
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${progress}%"></div>
                </div>
                
                <div class="batch-details">
                    <div class="batch-detail">
                        <div class="batch-detail-label">Theme</div>
                        <div class="batch-detail-value">${batch.config?.theme || 'ocean'}</div>
                    </div>
                    <div class="batch-detail">
                        <div class="batch-detail-label">Total Videos</div>
                        <div class="batch-detail-value">${batch.totalVideos}</div>
                    </div>
                    <div class="batch-detail">
                        <div class="batch-detail-label">Completed</div>
                        <div class="batch-detail-value">${batch.completedVideos}</div>
                    </div>
                    <div class="batch-detail">
                        <div class="batch-detail-label">Failed</div>
                        <div class="batch-detail-value">${batch.failedVideos || 0}</div>
                    </div>
                    <div class="batch-detail">
                        <div class="batch-detail-label">Started</div>
                        <div class="batch-detail-value">${createdAt}</div>
                    </div>
                    <div class="batch-detail">
                        <div class="batch-detail-label">Completed</div>
                        <div class="batch-detail-value">${completedAt}</div>
                    </div>
                </div>
                
                <div class="batch-activity">
                    🔄 ${batch.currentActivity || 'Waiting...'}
                </div>
                
                ${batch.outputPaths && batch.outputPaths.length > 0 ? `
                    <div style="margin-top: 10px;">
                        <strong>Output Files:</strong>
                        <ul style="margin-top: 5px; margin-left: 20px; font-size: 0.85rem;">
                            ${batch.outputPaths.slice(0, 3).map(path => `<li>${path}</li>`).join('')}
                            ${batch.outputPaths.length > 3 ? `<li>... and ${batch.outputPaths.length - 3} more files</li>` : ''}
                        </ul>
                    </div>
                ` : ''}
                
                ${batch.errors && batch.errors.length > 0 ? `
                    <div style="margin-top: 10px; color: var(--danger-color); font-size: 0.85rem;">
                        <strong>Errors:</strong>
                        <ul style="margin-top: 5px; margin-left: 20px;">
                            ${batch.errors.map(err => `<li>${err}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}
            </div>
        `;
    }

    logActivity(message, type = 'info') {
        const timestamp = new Date().toLocaleTimeString();
        const entry = document.createElement('div');
        entry.className = `log-entry ${type}`;
        entry.innerHTML = `<strong>[${timestamp}]</strong> ${message}`;
        
        this.logEntriesEl.insertBefore(entry, this.logEntriesEl.firstChild);

        // Keep only last 50 entries
        while (this.logEntriesEl.children.length > 50) {
            this.logEntriesEl.removeChild(this.logEntriesEl.lastChild);
        }
    }

    setGeneratingState(isGenerating) {
        this.generateBtn.disabled = isGenerating;
        this.generateBtn.innerHTML = isGenerating 
            ? '⏳ Generating...' 
            : '🎬 Start Batch Generation';
    }

    startAutoRefresh() {
        // Refresh batch status every 3 seconds
        this.refreshInterval = setInterval(() => {
            this.loadBatches();
        }, 3000);
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new VideoGeneratorApp();
});

// Handle page unload
window.addEventListener('beforeunload', () => {
    if (window.app) {
        window.app.stopAutoRefresh();
    }
});
