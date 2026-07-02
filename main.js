const { app, BrowserWindow, dialog } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const os = require('os');
const fs = require('fs');
const http = require('http');

// =====================================================
// STARTUP LOGGING
// =====================================================
const logFilePath = path.join(app.getPath('userData'), 'startup.log');

// Clear previous log on each launch
try { fs.writeFileSync(logFilePath, ''); } catch (_) {}

function log(message) {
  const timestamp = new Date().toISOString();
  const line = `[${timestamp}] ${message}\n`;
  try { fs.appendFileSync(logFilePath, line); } catch (_) {}
  console.log(message);
}

log('=== Sportexa Desktop Starting ===');
log(`Platform: ${os.platform()} | Arch: ${os.arch()}`);
log(`Electron packaged: ${app.isPackaged}`);
log(`App path: ${app.getAppPath()}`);
log(`User data: ${app.getPath('userData')}`);

// =====================================================
// GLOBALS
// =====================================================
let mainWindow;
let backendProcess;
let aiProcess;

// =====================================================
// BACKEND LAUNCHER
// =====================================================
function startBackend() {
  const isWindows = os.platform() === 'win32';

  if (isWindows) {
    if (!app.isPackaged) {
      // ── DEV MODE: launch Python processes directly from .venv ──
      const pythonExe = path.join(__dirname, '.venv', 'Scripts', 'python.exe');
      log(`[DEV] Python executable: ${pythonExe}`);

      if (fs.existsSync(pythonExe)) {
        log('[DEV] Launching backend via .venv python...');
        backendProcess = spawn(pythonExe, ['-m', 'backend.app.main'], {
          cwd: __dirname,
          stdio: ['ignore', 'pipe', 'pipe']
        });

        log('[DEV] Launching AI engine via .venv python...');
        aiProcess = spawn(pythonExe, ['-m', 'ai_machine.main'], {
          cwd: __dirname,
          stdio: ['ignore', 'pipe', 'pipe']
        });
      } else {
        // Fallback to batch file if no .venv found
        const batPath = path.join(__dirname, 'START_FULL_SYSTEM.bat');
        log(`[DEV] .venv not found, falling back to: ${batPath}`);
        backendProcess = spawn('cmd.exe', ['/c', batPath], {
          cwd: __dirname,
          stdio: ['ignore', 'pipe', 'pipe']
        });
      }
    } else {
      // ── PACKAGED MODE: try PyInstaller executables first ──
      const backendExe = path.join(process.resourcesPath, 'dist', 'backend', 'backend.exe');
      const aiExe = path.join(process.resourcesPath, 'dist', 'ai_machine', 'ai_machine.exe');

      log(`[PROD] Looking for backend at: ${backendExe}`);
      log(`[PROD] Looking for AI engine at: ${aiExe}`);

      if (fs.existsSync(backendExe)) {
        log('[PROD] Found backend.exe — spawning...');
        backendProcess = spawn(backendExe, [], {
          cwd: process.resourcesPath,
          stdio: ['ignore', 'pipe', 'pipe']
        });

        if (fs.existsSync(aiExe)) {
          log('[PROD] Found ai_machine.exe — spawning...');
          aiProcess = spawn(aiExe, [], {
            cwd: process.resourcesPath,
            stdio: ['ignore', 'pipe', 'pipe']
          });
        } else {
          log('[WARN] ai_machine.exe not found — skipping AI engine');
        }
      } else {
        // Fallback: try the batch script bundled in resources
        const batFallback = path.join(process.resourcesPath, 'START_FULL_SYSTEM.bat');
        log(`[PROD] backend.exe not found. Falling back to: ${batFallback}`);
        backendProcess = spawn('cmd.exe', ['/c', batFallback], {
          cwd: process.resourcesPath,
          stdio: ['ignore', 'pipe', 'pipe']
        });
      }
    }
  } else {
    // ── LINUX / macOS ──
    const cwd = app.isPackaged ? process.resourcesPath : __dirname;
    log(`[UNIX] Launching backend in: ${cwd}`);
    backendProcess = spawn('sh', ['-c', 'python3 -m backend.app.main & python3 -m ai_machine.main'], {
      cwd,
      stdio: ['ignore', 'pipe', 'pipe']
    });
  }

  // ── Attach log streams ──
  if (backendProcess) {
    backendProcess.stdout.on('data', (data) => log(`Backend: ${data.toString().trim()}`));
    backendProcess.stderr.on('data', (data) => log(`Backend ERR: ${data.toString().trim()}`));
    backendProcess.on('error', (err) => log(`Backend SPAWN ERROR: ${err.message}`));
    backendProcess.on('close', (code) => log(`Backend process exited with code ${code}`));
  }

  if (aiProcess) {
    aiProcess.stdout.on('data', (data) => log(`AI Engine: ${data.toString().trim()}`));
    aiProcess.stderr.on('data', (data) => log(`AI Engine ERR: ${data.toString().trim()}`));
    aiProcess.on('error', (err) => log(`AI SPAWN ERROR: ${err.message}`));
    aiProcess.on('close', (code) => log(`AI Engine process exited with code ${code}`));
  }
}

// =====================================================
// HEALTH CHECK — wait for backend before loading UI
// =====================================================
function waitForBackend(attempt = 0) {
  const maxAttempts = 45; // up to ~45 seconds

  if (attempt > maxAttempts) {
    log(`Health check failed after ${maxAttempts} attempts.`);
    dialog.showErrorBox(
      'Sportexa — Startup Error',
      'The backend service did not start in time.\n\n' +
      `Check the log file at:\n${logFilePath}\n\n` +
      'Make sure no other instance is running on port 8001.'
    );
    if (mainWindow) {
      mainWindow.show();
    }
    return;
  }

  http.get('http://localhost:8001/health', (res) => {
    if (res.statusCode === 200) {
      log(`Health check passed on attempt ${attempt + 1}. Loading UI...`);
      if (mainWindow) {
        mainWindow.loadURL('http://localhost:8001');
        mainWindow.show();
      }
    } else {
      setTimeout(() => waitForBackend(attempt + 1), 1000);
    }
  }).on('error', () => {
    if (attempt % 5 === 0) {
      log(`Health check attempt ${attempt + 1}/${maxAttempts} — waiting...`);
    }
    setTimeout(() => waitForBackend(attempt + 1), 1000);
  });
}

// =====================================================
// WINDOW CREATION
// =====================================================
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    },
    title: 'Sportexa',
    autoHideMenuBar: true,
    show: false // Hidden until backend is ready
  });

  // Try loading a splash/loading page while waiting
  const loadingPath = path.join(__dirname, 'assets', 'loading.html');
  if (fs.existsSync(loadingPath)) {
    mainWindow.loadFile(loadingPath);
    mainWindow.show();
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Begin health-check polling
  waitForBackend();
}

// =====================================================
// APP LIFECYCLE
// =====================================================
app.on('ready', () => {
  log('App ready event fired.');
  startBackend();
  createWindow();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('quit', () => {
  log('App quitting — killing backend processes...');

  if (backendProcess && backendProcess.pid) {
    try {
      if (os.platform() === 'win32') {
        spawn('taskkill', ['/pid', String(backendProcess.pid), '/f', '/t']);
      } else {
        backendProcess.kill();
      }
    } catch (e) {
      log(`Error killing backend: ${e.message}`);
    }
  }

  if (aiProcess && aiProcess.pid) {
    try {
      if (os.platform() === 'win32') {
        spawn('taskkill', ['/pid', String(aiProcess.pid), '/f', '/t']);
      } else {
        aiProcess.kill();
      }
    } catch (e) {
      log(`Error killing AI engine: ${e.message}`);
    }
  }
});
