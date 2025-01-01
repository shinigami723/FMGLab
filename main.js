const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const treeKill = require('tree-kill');

let win;
let pythonProcess;

function createWindow() {
    win = new BrowserWindow({
        width: 800,
        height: 600,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js')
        }
    });

    win.loadFile(path.join(__dirname, 'templates', 'index.html')).catch((err) => {
        console.error("Failed to load index.html", err);
    });

    win.on('closed', () => {
        console.log('Window closed');
        if (pythonProcess) {
            treeKill(pythonProcess.pid, 'SIGTERM');
        }
        win = null;
    });
}

function startPythonBackend() {
    pythonProcess = spawn(path.join(__dirname, 'server.exe'));

    pythonProcess.stdout.on('data', (data) => {
        console.log(`stdout: ${data}`);
    });

    pythonProcess.stderr.on('data', (data) => {
        console.error(`stderr: ${data}`);
    });

    pythonProcess.on('close', (code) => {
        console.log(`Python process exited with code ${code}`);
    });
}

app.whenReady().then(() => {
    startPythonBackend();
    createWindow();

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on('before-quit', () => {
    console.log('App is about to quit');
    if (pythonProcess) {
        treeKill(pythonProcess.pid, 'SIGTERM');
    }
});

app.on('will-quit', () => {
    console.log('App will quit');
    if (pythonProcess) {
        treeKill(pythonProcess.pid, 'SIGTERM');
    }
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});
