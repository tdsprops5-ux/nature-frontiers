const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
    },
    icon: path.join(__dirname, 'frontend/assets/icon.png'),
  });

  mainWindow.loadFile(path.join(__dirname, 'frontend', 'index.html'));
  
  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// IPC handlers for communication with renderer process
ipcMain.handle('start-batch-generation', async (event, config) => {
  const axios = require('axios');
  try {
    const response = await axios.post('http://localhost:3001/api/generate-batch', config);
    return { success: true, data: response.data };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

ipcMain.handle('get-generation-status', async (event, batchId) => {
  const axios = require('axios');
  try {
    const response = await axios.get(`http://localhost:3001/api/status/${batchId}`);
    return { success: true, data: response.data };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

ipcMain.handle('get-all-batches', async () => {
  const axios = require('axios');
  try {
    const response = await axios.get('http://localhost:3001/api/batches');
    return { success: true, data: response.data };
  } catch (error) {
    return { success: false, error: error.message };
  }
});
