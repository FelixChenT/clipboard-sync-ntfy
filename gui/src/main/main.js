const { app, BrowserWindow, Menu, Tray, ipcMain, dialog, shell } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const Store = require('electron-store');
const log = require('electron-log');

// Configure logging
log.transports.file.level = 'info';
log.transports.console.level = 'debug';

// Initialize store for settings
const store = new Store();

// Helper function to get resource paths
function getResourcePath(relativePath) {
  if (app.isPackaged) {
    // In production, resources are in the app.asar or Resources folder
    return path.join(process.resourcesPath, 'app', relativePath);
  } else {
    // In development, use relative path from the main.js location
    return path.join(__dirname, '../../..', relativePath);
  }
}

// Helper function to get Python executable path
function getPythonExecutablePath() {
  if (app.isPackaged) {
    // In production, try to find bundled Python or use system Python
    const bundledPython = path.join(process.resourcesPath, 'app', 'venv', 'bin', 'python');
    if (fs.existsSync(bundledPython)) {
      return bundledPython;
    }
    // Fallback to system Python
    return 'python3';
  } else {
    // In development, use the venv Python
    const venvPython = path.join(__dirname, '../../../venv/bin/python');
    if (fs.existsSync(venvPython)) {
      return venvPython;
    }
    return 'python3';
  }
}

class ClipboardSyncApp {
  constructor() {
    this.mainWindow = null;
    this.tray = null;
    this.pythonProcess = null;
    this.isQuitting = false;
    
    // Initialize app
    this.initializeApp();
  }

  initializeApp() {
    // Handle app ready
    app.whenReady().then(() => {
      this.createMainWindow();
      this.createTray();
      this.setupIPC();
      
      app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
          this.createMainWindow();
        }
      });
    });

    // Handle app window close
    app.on('window-all-closed', () => {
      if (process.platform !== 'darwin') {
        this.cleanup();
        app.quit();
      }
    });

    // Handle app before quit
    app.on('before-quit', () => {
      this.isQuitting = true;
      this.cleanup();
    });
  }

  createMainWindow() {
    this.mainWindow = new BrowserWindow({
      width: 800,
      height: 600,
      minWidth: 600,
      minHeight: 400,
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
        preload: path.join(__dirname, 'preload.js')
      },
      titleBarStyle: 'default', // Use default macOS title bar
      title: 'Clipboard Sync',
      show: false,
      // macOS specific window styling
      ...(process.platform === 'darwin' && {
        titleBarStyle: 'default',
        trafficLightPosition: { x: 20, y: 20 }
      })
    });

    // Load the React app
    const isDev = process.env.NODE_ENV === 'development';
    if (isDev) {
      this.mainWindow.loadURL('http://localhost:3000');
      this.mainWindow.webContents.openDevTools();
    } else {
      this.mainWindow.loadFile(path.join(__dirname, '../renderer/build/index.html'));
    }

    // Show window when ready
    this.mainWindow.once('ready-to-show', () => {
      this.mainWindow.show();
    });

    // Handle window close
    this.mainWindow.on('close', (event) => {
      if (!this.isQuitting) {
        event.preventDefault();
        this.mainWindow.hide();
      }
    });
  }

  createTray() {
    const { nativeImage } = require('electron');

    // Use custom icon or system template icon
    let trayIcon;
    try {
      // Try to load custom tray icon
      const iconPath = path.join(__dirname, '../assets/icons/icon-16.png');
      if (fs.existsSync(iconPath)) {
        trayIcon = nativeImage.createFromPath(iconPath);
        trayIcon = trayIcon.resize({ width: 16, height: 16 });
      } else {
        // Fallback to system template icon
        trayIcon = nativeImage.createFromNamedImage('NSStatusAvailable', [16, 16]);
        if (trayIcon.isEmpty()) {
          trayIcon = nativeImage.createEmpty();
        }
      }
    } catch (error) {
      log.warn('Failed to create tray icon:', error);
      trayIcon = nativeImage.createEmpty();
    }

    this.tray = new Tray(trayIcon);
    this.updateTrayMenu();
    this.tray.setToolTip('Clipboard Sync');

    this.tray.on('click', () => {
      this.mainWindow.show();
      this.mainWindow.focus();
    });
  }

  updateTrayMenu() {
    if (!this.tray) return;

    const isRunning = this.pythonProcess !== null;

    const contextMenu = Menu.buildFromTemplate([
      {
        label: 'Show Clipboard Sync',
        click: () => {
          this.mainWindow.show();
          this.mainWindow.focus();
        }
      },
      { type: 'separator' },
      {
        label: isRunning ? 'Stop Sync' : 'Start Sync',
        click: () => {
          if (isRunning) {
            this.stopPythonProcess();
          } else {
            this.startPythonProcess();
          }
        }
      },
      {
        label: `Status: ${isRunning ? 'Running' : 'Stopped'}`,
        enabled: false
      },
      { type: 'separator' },
      {
        label: 'Preferences...',
        click: () => {
          this.mainWindow.show();
          this.mainWindow.focus();
          this.sendToRenderer('switch-tab', 'config');
        }
      },
      { type: 'separator' },
      {
        label: 'Quit',
        click: () => {
          this.isQuitting = true;
          app.quit();
        }
      }
    ]);

    this.tray.setContextMenu(contextMenu);
  }

  setupIPC() {
    // Handle start sync
    ipcMain.handle('start-sync', async (event, config) => {
      try {
        await this.startPythonProcess(config);
        return { success: true };
      } catch (error) {
        log.error('Failed to start sync:', error);
        return { success: false, error: error.message };
      }
    });

    // Handle stop sync
    ipcMain.handle('stop-sync', async () => {
      try {
        await this.stopPythonProcess();
        return { success: true };
      } catch (error) {
        log.error('Failed to stop sync:', error);
        return { success: false, error: error.message };
      }
    });

    // Handle get config
    ipcMain.handle('get-config', async () => {
      try {
        return await this.loadConfig();
      } catch (error) {
        log.error('Failed to load config:', error);
        return this.getDefaultConfig();
      }
    });

    // Handle save config
    ipcMain.handle('save-config', async (event, config) => {
      try {
        await this.saveConfig(config);
        return { success: true };
      } catch (error) {
        log.error('Failed to save config:', error);
        return { success: false, error: error.message };
      }
    });

    // Handle get sync status
    ipcMain.handle('get-sync-status', () => {
      return {
        isRunning: this.pythonProcess !== null,
        pid: this.pythonProcess ? this.pythonProcess.pid : null
      };
    });

    // Handle open external URL
    ipcMain.handle('open-external', async (event, url) => {
      try {
        await shell.openExternal(url);
        return { success: true };
      } catch (error) {
        log.error('Failed to open external URL:', error);
        return { success: false, error: error.message };
      }
    });

    // Handle show message box
    ipcMain.handle('show-message-box', async (event, options) => {
      try {
        const result = await dialog.showMessageBox(this.mainWindow, options);
        return result;
      } catch (error) {
        log.error('Failed to show message box:', error);
        return { response: 0 };
      }
    });
  }

  async startPythonProcess(config = null) {
    if (this.pythonProcess) {
      log.info('Python process already running');
      return;
    }

    try {
      // Ensure config file exists and is valid
      await this.ensureConfigFile(config);

      // Get Python executable path
      const pythonPath = getPythonExecutablePath();
      const scriptPath = getResourcePath('main.py');

      // Check if script exists
      if (!fs.existsSync(scriptPath)) {
        throw new Error(`Python script not found at: ${scriptPath}`);
      }

      log.info(`Starting Python process: ${pythonPath} ${scriptPath}`);

      this.pythonProcess = spawn(pythonPath, [scriptPath], {
        cwd: getResourcePath(''),
        stdio: ['pipe', 'pipe', 'pipe'],
        env: { ...process.env, PYTHONUNBUFFERED: '1' }
      });

      // Handle process output
      this.pythonProcess.stdout.on('data', (data) => {
        const output = data.toString().trim();
        if (output) {
          log.info('Python stdout:', output);
          this.sendToRenderer('python-output', { type: 'stdout', data: output });
        }
      });

      this.pythonProcess.stderr.on('data', (data) => {
        const output = data.toString().trim();
        if (output) {
          log.error('Python stderr:', output);
          this.sendToRenderer('python-output', { type: 'stderr', data: output });
        }
      });

      // Handle process exit
      this.pythonProcess.on('exit', (code, signal) => {
        log.info(`Python process exited with code ${code}, signal ${signal}`);
        this.pythonProcess = null;
        this.sendToRenderer('sync-status-changed', { isRunning: false });

        // If process exited unexpectedly, notify user
        if (code !== 0 && code !== null) {
          this.sendToRenderer('python-output', {
            type: 'stderr',
            data: `Process exited unexpectedly with code ${code}`
          });
        }
      });

      // Handle process error
      this.pythonProcess.on('error', (error) => {
        log.error('Python process error:', error);
        this.pythonProcess = null;
        this.sendToRenderer('sync-status-changed', { isRunning: false });
        this.sendToRenderer('python-output', {
          type: 'stderr',
          data: `Process error: ${error.message}`
        });
      });

      this.sendToRenderer('sync-status-changed', {
        isRunning: true,
        pid: this.pythonProcess.pid
      });

      // Update tray menu
      if (this.tray) {
        this.updateTrayMenu();
      }

    } catch (error) {
      log.error('Failed to start Python process:', error);
      throw error;
    }
  }

  async ensureConfigFile(config) {
    const fs = require('fs').promises;
    const yaml = require('js-yaml');
    const configPath = getResourcePath('config/config.yaml');

    try {
      // Check if config directory exists
      const configDir = path.dirname(configPath);
      await fs.mkdir(configDir, { recursive: true });

      // If config is provided, write it to file
      if (config) {
        const yamlStr = yaml.dump(config);
        await fs.writeFile(configPath, yamlStr, 'utf8');
        log.info('Configuration file updated');
      } else {
        // Check if config file exists, if not create from example
        try {
          await fs.access(configPath);
        } catch (error) {
          const examplePath = getResourcePath('config/config.yaml.example');
          try {
            await fs.copyFile(examplePath, configPath);
            log.info('Created config file from example');
          } catch (copyError) {
            log.warn('Could not create config file from example:', copyError);
          }
        }
      }
    } catch (error) {
      log.error('Failed to ensure config file:', error);
      throw error;
    }
  }

  async stopPythonProcess() {
    if (!this.pythonProcess) {
      log.info('No Python process to stop');
      return;
    }

    try {
      log.info('Stopping Python process');
      this.pythonProcess.kill('SIGTERM');
      
      // Wait for process to exit
      await new Promise((resolve) => {
        const timeout = setTimeout(() => {
          if (this.pythonProcess) {
            this.pythonProcess.kill('SIGKILL');
          }
          resolve();
        }, 5000);

        if (this.pythonProcess) {
          this.pythonProcess.on('exit', () => {
            clearTimeout(timeout);
            resolve();
          });
        } else {
          clearTimeout(timeout);
          resolve();
        }
      });

      this.pythonProcess = null;
      this.sendToRenderer('sync-status-changed', { isRunning: false });

      // Update tray menu
      if (this.tray) {
        this.updateTrayMenu();
      }
      
    } catch (error) {
      log.error('Failed to stop Python process:', error);
      throw error;
    }
  }

  getPythonPath() {
    // This method is deprecated, use getPythonExecutablePath() instead
    return getPythonExecutablePath();
  }

  sendToRenderer(channel, data) {
    if (this.mainWindow && !this.mainWindow.isDestroyed()) {
      this.mainWindow.webContents.send(channel, data);
    }
  }

  async loadConfig() {
    const fs = require('fs').promises;
    const yaml = require('js-yaml');
    const configPath = getResourcePath('config/config.yaml');

    try {
      const configData = await fs.readFile(configPath, 'utf8');
      return yaml.load(configData);
    } catch (error) {
      log.warn('Could not load config file, using defaults:', error);
      return this.getDefaultConfig();
    }
  }

  async saveConfig(config) {
    const fs = require('fs').promises;
    const yaml = require('js-yaml');
    const configPath = getResourcePath('config/config.yaml');

    try {
      // Ensure config directory exists
      const configDir = path.dirname(configPath);
      await fs.mkdir(configDir, { recursive: true });

      const yamlStr = yaml.dump(config, {
        indent: 2,
        lineWidth: 120,
        noRefs: true
      });
      await fs.writeFile(configPath, yamlStr, 'utf8');
      log.info('Configuration saved successfully');
    } catch (error) {
      log.error('Failed to save configuration:', error);
      throw error;
    }
  }

  getDefaultConfig() {
    return {
      sender: {
        enabled: true,
        ntfy_topic_url: "https://ntfy.sh/YOUR_SEND_TOPIC_HERE",
        poll_interval_seconds: 1.0,
        request_timeout_seconds: 15,
        filename_prefix: "clipboard_content_"
      },
      receiver: {
        enabled: true,
        ntfy_server: "ntfy.sh",
        ntfy_topic: "YOUR_RECEIVE_TOPIC_HERE",
        reconnect_delay_seconds: 5,
        request_timeout_seconds: 15
      },
      logging: {
        level: "INFO"
      },
      macos: {
        image_support: true,
        image_uti_map: {
          "public.png": "png",
          "public.jpeg": "jpg",
          "com.compuserve.gif": "gif"
        }
      }
    };
  }

  cleanup() {
    if (this.pythonProcess) {
      this.pythonProcess.kill('SIGTERM');
      this.pythonProcess = null;
    }
  }
}

// Create app instance
new ClipboardSyncApp();
