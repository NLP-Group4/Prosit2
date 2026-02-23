const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object to the browser environment.
contextBridge.exposeInMainWorld(
    'api', // Exposed to the renderer as `window.api`
    {
        ping: () => ipcRenderer.invoke('ping'),

        // Connects ChatPage.jsx generate fetch trigger to the Desktop lifecycle
        generateAndVerify: (args) => ipcRenderer.invoke('generate-and-verify', args),

        // Docker detection and guidance
        detectDocker: () => ipcRenderer.invoke('detect-docker'),
        getDockerGuidance: () => ipcRenderer.invoke('get-docker-guidance'),
    }
);
