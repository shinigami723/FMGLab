const { contextBridge, ipcRenderer } = require('electron');

// Expose IPC methods to the renderer (frontend)
contextBridge.exposeInMainWorld('electron', {
    sendToPython: (data) => ipcRenderer.send('send-to-python', data),
    receiveFromPython: (callback) => ipcRenderer.on('receive-from-python', callback)
});
