const { app, BrowserWindow, ipcMain, Menu } = require('electron');
const { spawn } = require('child_process');
const http = require('http');
const path = require('path');
const fs = require('fs');
const os = require('os');

// Optimize Chromium Engine parameters for production desktop performance
app.commandLine.appendSwitch('disable-http-cache');
app.commandLine.appendSwitch('enable-gpu-rasterization');
app.commandLine.appendSwitch('enable-zero-copy');
app.commandLine.appendSwitch('force-gpu-rasterization');
app.commandLine.appendSwitch('enable-fast-unload');

// Remove standard menu bar globally
Menu.setApplicationMenu(null);

let mainWindow;
let splashWindow;
let pythonProcess;

// =====================================================
// STARTUP LOGGING & ROTATION
// =====================================================
const logDir = app.getPath('userData');
const logFilePath = path.join(logDir, 'desktop_startup.log');
const maxLogs = 5;

try {
    // Shift older log files
    for (let i = maxLogs - 1; i >= 1; i--) {
        const oldPath = `${logFilePath}.${i}`;
        const newPath = `${logFilePath}.${i + 1}`;
        if (fs.existsSync(oldPath)) {
            fs.renameSync(oldPath, newPath);
        }
    }
    // Rename current log to .1
    if (fs.existsSync(logFilePath)) {
        fs.renameSync(logFilePath, `${logFilePath}.1`);
    }
} catch (_) {}

try { fs.writeFileSync(logFilePath, ''); } catch (_) {}

function log(message) {
    const timestamp = new Date().toISOString();
    const line = `[${timestamp}] ${message}\n`;
    try { fs.appendFileSync(logFilePath, line); } catch (_) {}
    console.log(message);
}

log('=== SPORTEXA Native Desktop Starting ===');

// ── Cross-Platform Path Resolution ────────────────────────────────
const backendCwd = path.resolve(__dirname, '..');

function findPythonExe() {
    const winPath = path.join(backendCwd, '.venv', 'Scripts', 'python.exe');
    if (fs.existsSync(winPath)) return winPath;

    const unixPath = path.join(backendCwd, '.venv', 'bin', 'python');
    if (fs.existsSync(unixPath)) return unixPath;

    return process.platform === 'win32' ? 'python' : 'python3';
}

function startPythonBackend() {
    const pythonExe = findPythonExe();
    log(`Starting Python Backend using: ${pythonExe}`);

    pythonProcess = spawn(pythonExe, ['-m', 'ai_machine.main'], {
        cwd: backendCwd,
        detached: false,
        env: { ...process.env, HEADLESS_AI: "1" }
    });

    pythonProcess.stdout.on('data', (data) => {
        log(`[AI Engine] ${data.toString().trim()}`);
    });

    pythonProcess.stderr.on('data', (data) => {
        log(`[AI Engine ERR] ${data.toString().trim()}`);
    });

    pythonProcess.on('close', (code) => {
        log(`Python process exited with code ${code}`);
    });

    pythonProcess.on('error', (err) => {
        log(`Failed to start Python backend: ${err.message}`);
    });
}

// ── Splash Window Creation ────────────────────────────────
function createSplashWindow() {
    log('Creating frameless splash window...');
    splashWindow = new BrowserWindow({
        width: 800,
        height: 520,
        frame: false,
        transparent: true,
        alwaysOnTop: true,
        resizable: false,
        center: true,
        backgroundColor: '#0F172A',
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false
        }
    });

    splashWindow.loadFile(path.join(__dirname, 'splash.html'));

    splashWindow.webContents.on('did-finish-load', () => {
        log('Splash window loaded. Querying system hardware...');
        splashWindow.webContents.send('init-specs', {
            appDataPath: app.getPath('userData'),
            appVersion: app.getVersion(),
            electronVersion: process.versions.electron,
            osInfo: {
                type: os.type(),
                release: os.release(),
                cpuModel: os.cpus()[0]?.model || 'Unknown CPU',
                totalMem: os.totalmem()
            }
        });
    });

    splashWindow.webContents.on('console-message', (event, level, message, line, sourceId) => {
        log(`[Splash Console] ${message} (from ${path.basename(sourceId)}:${line})`);
    });

    splashWindow.on('closed', () => {
        splashWindow = null;
    });
}

// ── Main Dashboard Window Creation ────────────────────────
function createMainWindow(safeMode = false) {
    log(`Creating main dashboard window (Safe Mode: ${safeMode})...`);
    mainWindow = new BrowserWindow({
        width: 1440,
        height: 900,
        show: false, // Hidden until loaded to prevent white flashes
        autoHideMenuBar: true,
        title: "SPORTEXA AI Pitch Machine",
        backgroundColor: '#020509',
        icon: path.join(__dirname, '..', 'ai_machine', 'ui', 'icon.ico'),
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            backgroundThrottling: false, // Prevents background processes from pausing
            spellcheck: false, // Reduces CPU overhead
            enableWebSQL: false
        }
    });

    // Remove window menu bar completely
    mainWindow.removeMenu();

    // Prevent default drag-and-drop page navigation
    mainWindow.webContents.on('will-navigate', (e) => {
        e.preventDefault();
    });

    // Strip visual zoom capabilities
    mainWindow.webContents.setVisualZoomLevelLimits(1, 1);

    // Inject Native App Behavior on Page Load
    mainWindow.webContents.on('did-finish-load', () => {
        // Suppress browser right-click context menu, browser reload keys, and page zooming
        const script = `
            document.addEventListener('contextmenu', e => e.preventDefault());
            document.addEventListener('keydown', e => {
                // Prevent F5, Ctrl+R, Cmd+R (reload)
                if (e.key === 'F5' || (e.ctrlKey && e.key === 'r') || (e.metaKey && e.key === 'r')) {
                    e.preventDefault();
                }
                // Prevent Ctrl+Plus, Ctrl+Minus, Ctrl+0 (zooming)
                if (e.ctrlKey && (e.key === '=' || e.key === '-' || e.key === '0')) {
                    e.preventDefault();
                }
            });
            document.addEventListener('wheel', e => {
                if (e.ctrlKey) {
                    e.preventDefault();
                }
            }, { passive: false });
        `;
        mainWindow.webContents.executeJavaScript(script);
    });

    // Clear session cache to ensure no stale/cached UI pages or assets are used
    mainWindow.webContents.session.clearCache().then(() => {
        log('Electron session cache cleared successfully.');
    }).catch(err => {
        log(`Failed to clear session cache: ${err.message}`);
    });

    const targetUrl = safeMode ? 'http://127.0.0.1:7777/dashboard?safemode=1' : 'http://127.0.0.1:7777/dashboard';
    
    // Load with headers that prevent server/client cached loads
    mainWindow.loadURL(targetUrl, {
        extraHeaders: 'pragma: no-cache\nCache-Control: no-cache, no-store, must-revalidate\n'
    });

    mainWindow.once('ready-to-show', () => {
        log('Main dashboard window is rendered. Transitioning...');
        if (splashWindow) {
            splashWindow.close();
            splashWindow = null;
        }
        mainWindow.show();
        mainWindow.maximize();
    });

    mainWindow.webContents.on('console-message', (event, level, message, line, sourceId) => {
        log(`[Main Console] ${message} (from ${path.basename(sourceId)}:${line})`);
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

// ── IPC Handlers ──────────────────────────────────────────
ipcMain.on('startup-complete', () => {
    log('Startup diagnostics passed completely.');
    createMainWindow(false);
});

ipcMain.on('startup-safe-mode', () => {
    log('User initiated Safe Mode bypass.');
    createMainWindow(true);
});

// ── App Lifecycle ─────────────────────────────────────────
app.whenReady().then(() => {
    startPythonBackend();
    createSplashWindow();

    app.on('activate', function () {
        if (BrowserWindow.getAllWindows().length === 0) createSplashWindow();
    });
});

app.on('window-all-closed', function () {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('will-quit', () => {
    log('App quitting — cleaning background Python processes...');
    if (pythonProcess) {
        if (process.platform !== 'win32') {
            try { process.kill(-pythonProcess.pid, 'SIGTERM'); } catch (_) {}
        }
        pythonProcess.kill();
    }
});

