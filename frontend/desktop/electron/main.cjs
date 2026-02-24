const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('node:path');

// Determine if we are in development mode (running from Vite)
const isDev = !app.isPackaged && process.env.NODE_ENV !== 'production';

let mainWindow;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        webPreferences: {
            preload: path.join(__dirname, 'preload.cjs'),
            // Security best practices:
            nodeIntegration: false,
            contextIsolation: true,
            sandbox: true,
        },
        // Customize for a sleek look
        titleBarStyle: 'hiddenInset',
        backgroundColor: '#ffffff', // Light theme default, will be overridden by CSS
    });

    if (isDev) {
        // In development, load the Vite dev server URL
        console.log('Loading local Vite server at http://localhost:5173');
        mainWindow.loadURL('http://localhost:5173');
        // Open the DevTools automatically
        mainWindow.webContents.openDevTools();
    } else {
        // In production, load the built index.html from Vite's dist folder
        mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
    }

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

// ---------------------------------------------------------------------------
// App Lifecycle
// ---------------------------------------------------------------------------

app.whenReady().then(() => {
    createWindow();

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on('window-all-closed', () => {
    // macOS behavior: keep app running until Cmd+Q
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

// ---------------------------------------------------------------------------
// IPC Handlers
// ---------------------------------------------------------------------------

ipcMain.handle('ping', () => 'pong');

const fs = require('fs-extra');
const AdmZip = require('adm-zip');
const axios = require('axios');
const dockerManager = require('./services/docker-manager.cjs');
const verifyRunner = require('./services/verify-runner.cjs');

// Docker detection handlers
ipcMain.handle('detect-docker', async () => {
    return await dockerManager.detectDocker();
});

ipcMain.handle('get-docker-guidance', async () => {
    return await dockerManager.getInstallGuidance();
});

// Deploy an existing project (for returning users — per docs: "Click Start on existing project")
ipcMain.handle('deploy-project', async (event, args) => {
    const { projectId, token, apiUrl } = args;
    if (!projectId || !token || !apiUrl) {
        return { success: false, error: 'Missing projectId, token, or apiUrl' };
    }
    try {
        const projRes = await axios.get(`${apiUrl}/projects/${projectId}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const { download_url } = projRes.data;
        if (!download_url) return { success: false, error: 'No download URL for project' };

        const zipRes = await axios.get(`${apiUrl}${download_url}`, {
            responseType: 'arraybuffer',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        const tempDir = path.join(app.getPath('temp'), `interius-gen-${projectId}`);
        await fs.emptyDir(tempDir);

        const zipPath = path.join(tempDir, 'project.zip');
        await fs.writeFile(zipPath, zipRes.data);

        const zip = new AdmZip(zipPath);
        zip.extractAllTo(tempDir, true);
        await fs.remove(zipPath);

        const items = await fs.readdir(tempDir);
        let projectDir = tempDir;
        if (items.length === 1 && (await fs.stat(path.join(tempDir, items[0]))).isDirectory()) {
            projectDir = path.join(tempDir, items[0]);
        }

        await dockerManager.deployProject(projectId, projectDir);
        return { success: true };
    } catch (err) {
        console.error('[IPC] deploy-project failed:', err.message);
        return {
            success: false,
            error: err.response?.data?.detail || err.message
        };
    }
});

ipcMain.handle('generate-and-verify', async (event, args) => {
    const { prompt, model, token, apiUrl } = args;
    console.log('[IPC] Received generate-and-verify request for', model);

    // Set up progress callback to forward Docker deployment progress to renderer
    dockerManager.setProgressCallback((progressData) => {
        console.log('[IPC] Docker progress:', progressData);
        event.sender.send('deployment-progress', progressData);
    });

    try {
        // Step 1: Tell Cloud API to generate the spec and the code via agents
        const genRes = await axios.post(`${apiUrl}/generate-from-prompt`, {
            prompt, model
        }, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        const { project_id, project_name, download_url, thread_id } = genRes.data;
        console.log(`[IPC] Cloud generation complete. Project ID: ${project_id}`);

        // Step 1.5: Fetch the project spec which verifyRunner needs
        const specRes = await axios.get(`${apiUrl}/projects/${project_id}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const spec = specRes.data.spec;

        // Step 2: Download the generated ZIP artifact bounds to the project uuid
        const zipUrl = `${apiUrl}${download_url}`;
        const zipRes = await axios.get(zipUrl, {
            responseType: 'arraybuffer',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        const tempDir = path.join(app.getPath('temp'), `interius-gen-${project_id}`);
        await fs.emptyDir(tempDir);

        const zipPath = path.join(tempDir, 'project.zip');
        await fs.writeFile(zipPath, zipRes.data);

        // Step 3: Unzip and delete the zip file
        const zip = new AdmZip(zipPath);
        zip.extractAllTo(tempDir, true);
        await fs.remove(zipPath);

        // Find the extracted project directory (since it's wrapped in a root folder)
        const items = await fs.readdir(tempDir);
        let projectDir = tempDir;
        if (items.length === 1 && (await fs.stat(path.join(tempDir, items[0]))).isDirectory()) {
            projectDir = path.join(tempDir, items[0]);
        }

        // --- Iterative Test & Fix Loop ---
        let currentPassedTests = false;
        let attempts = 1;
        const MAX_ATTEMPTS = 3;

        let currentDownloadUrl = download_url;
        let currentProjectDir = projectDir;

        while (!currentPassedTests && attempts <= MAX_ATTEMPTS) {
            console.log(`[IPC] Starting Docker local evaluation layer in ${currentProjectDir} (Attempt ${attempts})...`);
            
            // Send deploying phase event
            event.sender.send('deployment-progress', {
                phase: 'deploying',
                message: `Deploying project (Attempt ${attempts}/${MAX_ATTEMPTS})...`,
                attempt: attempts,
                maxAttempts: MAX_ATTEMPTS
            });
            
            try {
                await dockerManager.deployProject(project_id, currentProjectDir);
            } catch (err) {
                console.error(`[IPC] Docker deploy failed on attempt ${attempts}:`, err.message);
                // Send error progress event
                event.sender.send('deployment-progress', {
                    phase: 'error',
                    message: err.message,
                    attempt: attempts
                });
                throw err;
            }

            // Send verifying phase event
            event.sender.send('deployment-progress', {
                phase: 'verifying',
                message: 'Running endpoint verification tests...'
            });

            console.log('[IPC] Running endpoint verification simulations...');
            const testReport = await verifyRunner.runFullSuite(spec, (testProgress) => {
                event.sender.send('deployment-progress', testProgress);
            });
            console.log(`[IPC] Test suite passed: ${testReport.passed}`);
            currentPassedTests = testReport.passed;

            // Push the verification report to the cloud API endpoint
            try {
                await axios.post(`${apiUrl}/projects/${project_id}/verify-report`, testReport, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
            } catch (e) {
                console.error('[IPC] Failed to ship verification log to cloud:', e.message);
            }

            if (!currentPassedTests && attempts < MAX_ATTEMPTS) {
                console.log('[IPC] Tests failed. Triggering Auto-Fix via Cloud API...');
                await dockerManager.stopProject(project_id);

                const failedTests = testReport.results.filter(r => !r.passed).map(r => ({
                    method: r.method,
                    endpoint: r.endpoint,
                    error_message: r.error_message || 'Test failed'
                }));

                try {
                    // Trigger the cloud auto-fix agent
                    const fixRes = await axios.post(`${apiUrl}/projects/${project_id}/fix`, {
                        attempt_number: attempts,
                        failed_tests: failedTests
                    }, {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });

                    // Download the fixed ZIP artifact
                    currentDownloadUrl = fixRes.data.download_url;

                    const fixZipUrl = `${apiUrl}${currentDownloadUrl}`;
                    const fixZipRes = await axios.get(fixZipUrl, {
                        responseType: 'arraybuffer',
                        headers: { 'Authorization': `Bearer ${token}` }
                    });

                    const fixTempDir = path.join(app.getPath('temp'), `interius-gen-${project_id}-fix${attempts}`);
                    await fs.emptyDir(fixTempDir);

                    const fixZipPath = path.join(fixTempDir, 'project.zip');
                    await fs.writeFile(fixZipPath, fixZipRes.data);

                    const fixZip = new AdmZip(fixZipPath);
                    fixZip.extractAllTo(fixTempDir, true);
                    await fs.remove(fixZipPath);

                    const fixItems = await fs.readdir(fixTempDir);
                    currentProjectDir = fixTempDir;
                    if (fixItems.length === 1 && (await fs.stat(path.join(fixTempDir, fixItems[0]))).isDirectory()) {
                        currentProjectDir = path.join(fixTempDir, fixItems[0]);
                    }

                } catch (e) {
                    console.error('[IPC] Cloud API Auto-Fix failed:', e.message);
                    break;
                }
            } else if (!currentPassedTests && attempts === MAX_ATTEMPTS) {
                console.error('[IPC] Auto-fix exhausted all attempts. Failing the generation.');
                // Don't stop Docker here so the user can inspect the broken container if they want.
                break;
            }

            attempts++;
        }

        // Send completion event
        event.sender.send('deployment-progress', {
            phase: 'complete',
            message: 'Deployment and verification complete',
            success: currentPassedTests
        });

        // Return the final success state and updated download url
        return {
            success: true, // we keep success explicitly as our marker
            project_id,
            project_name,
            thread_id,
            download_url: currentDownloadUrl
        };

    } catch (error) {
        console.error('[IPC] Error in generation lifecycle:', error.response?.data || error.message);
        
        // Send error event
        event.sender.send('deployment-progress', {
            phase: 'error',
            message: error.response?.data?.detail || error.message
        });
        
        return {
            success: false,
            error: error.response?.data?.detail || error.message
        };
    }
});
