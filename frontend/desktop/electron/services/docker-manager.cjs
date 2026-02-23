/*
 * docker-manager.js
 * 
 * Manages the local deployment of generated backend projects and databases.
 * Runs `docker compose up --build` on the extracted API project directories.
 */
const { spawn, exec } = require('node:child_process');
const path = require('node:path');
const fs = require('fs-extra');
const { promisify } = require('node:util');
const os = require('node:os');

const execAsync = promisify(exec);

class DockerManager {
    constructor() {
        this.activeProjects = new Map();
        this.dockerAvailable = null; // Cache detection result
    }

    /**
     * Detects if Docker is installed and running.
     * @returns {Promise<{available: boolean, version?: string, error?: string}>}
     */
    async detectDocker() {
        // Return cached result if available
        if (this.dockerAvailable !== null) {
            return this.dockerAvailable;
        }

        try {
            // Check if docker command exists
            const { stdout: versionOutput } = await execAsync('docker --version');
            const version = versionOutput.trim();

            // Check if Docker daemon is running
            const { stdout: infoOutput } = await execAsync('docker info', { timeout: 5000 });
            
            // Check for Docker Compose V2
            const { stdout: composeOutput } = await execAsync('docker compose version');
            const composeVersion = composeOutput.trim();

            this.dockerAvailable = {
                available: true,
                version,
                composeVersion,
                info: 'Docker is installed and running'
            };

            console.log(`[DockerManager] Docker detected: ${version}`);
            console.log(`[DockerManager] Docker Compose: ${composeVersion}`);
            
            return this.dockerAvailable;

        } catch (error) {
            const errorMessage = error.message || error.toString();
            
            let detailedError = 'Docker is not available';
            let installUrl = '';

            // Determine the specific issue
            if (errorMessage.includes('command not found') || errorMessage.includes('not recognized')) {
                detailedError = 'Docker is not installed';
            } else if (errorMessage.includes('Cannot connect') || errorMessage.includes('daemon')) {
                detailedError = 'Docker is installed but not running';
            } else if (errorMessage.includes('compose')) {
                detailedError = 'Docker is installed but Docker Compose V2 is not available';
            }

            // Platform-specific install URLs
            const platform = os.platform();
            if (platform === 'darwin') {
                installUrl = 'https://docs.docker.com/desktop/install/mac-install/';
            } else if (platform === 'win32') {
                installUrl = 'https://docs.docker.com/desktop/install/windows-install/';
            } else {
                installUrl = 'https://docs.docker.com/desktop/install/linux-install/';
            }

            this.dockerAvailable = {
                available: false,
                error: detailedError,
                installUrl,
                platform
            };

            console.error(`[DockerManager] ${detailedError}`);
            return this.dockerAvailable;
        }
    }

    /**
     * Returns user-friendly install guidance based on platform.
     * @returns {Promise<{title: string, message: string, installUrl: string, steps: string[]}>}
     */
    async getInstallGuidance() {
        const detection = await this.detectDocker();
        
        if (detection.available) {
            return {
                title: 'Docker is Ready',
                message: 'Docker is installed and running correctly.',
                installUrl: '',
                steps: []
            };
        }

        const platform = os.platform();
        let title, message, steps;

        if (detection.error.includes('not installed')) {
            title = 'Docker Desktop Required';
            message = 'To deploy and test your generated backends locally, you need Docker Desktop installed.';
            
            if (platform === 'darwin') {
                steps = [
                    '1. Download Docker Desktop for Mac from the link below',
                    '2. Open the downloaded .dmg file',
                    '3. Drag Docker to your Applications folder',
                    '4. Launch Docker Desktop from Applications',
                    '5. Wait for Docker to start (you\'ll see a whale icon in your menu bar)',
                    '6. Restart this application'
                ];
            } else if (platform === 'win32') {
                steps = [
                    '1. Download Docker Desktop for Windows from the link below',
                    '2. Run the installer',
                    '3. Follow the installation wizard',
                    '4. Restart your computer if prompted',
                    '5. Launch Docker Desktop',
                    '6. Wait for Docker to start',
                    '7. Restart this application'
                ];
            } else {
                steps = [
                    '1. Visit the Docker Desktop installation page',
                    '2. Choose your Linux distribution',
                    '3. Follow the installation instructions',
                    '4. Start the Docker service',
                    '5. Restart this application'
                ];
            }
        } else if (detection.error.includes('not running')) {
            title = 'Docker Desktop Not Running';
            message = 'Docker is installed but not currently running. Please start Docker Desktop.';
            
            if (platform === 'darwin') {
                steps = [
                    '1. Open Docker Desktop from your Applications folder',
                    '2. Wait for the whale icon to appear in your menu bar',
                    '3. Click the whale icon and verify it says "Docker Desktop is running"',
                    '4. Try again in this application'
                ];
            } else if (platform === 'win32') {
                steps = [
                    '1. Search for "Docker Desktop" in the Start menu',
                    '2. Launch Docker Desktop',
                    '3. Wait for Docker to start (check the system tray)',
                    '4. Try again in this application'
                ];
            } else {
                steps = [
                    '1. Start the Docker service: sudo systemctl start docker',
                    '2. Verify Docker is running: docker info',
                    '3. Try again in this application'
                ];
            }
        } else {
            title = 'Docker Issue Detected';
            message = detection.error;
            steps = [
                '1. Check Docker Desktop is installed and running',
                '2. Try restarting Docker Desktop',
                '3. If issues persist, reinstall Docker Desktop from the link below'
            ];
        }

        return {
            title,
            message,
            installUrl: detection.installUrl,
            steps
        };
    }

    /**
     * Spawns docker-compose to build and spin up the project.
     * @param {string} projectId 
     * @param {string} projectPath Path to the extracted ZIP.
     * @returns {Promise<boolean>} Resolves true when healthy.
     */
    async deployProject(projectId, projectPath) {
        // Check Docker availability first
        const detection = await this.detectDocker();
        if (!detection.available) {
            const guidance = await this.getInstallGuidance();
            throw new Error(`${guidance.title}: ${guidance.message}\n\nPlease install Docker Desktop: ${guidance.installUrl}`);
        }

        return new Promise((resolve, reject) => {
            console.log(`[DockerManager] Deploying project ${projectId} from ${projectPath}`);
            const composeFile = path.join(projectPath, 'docker-compose.yml');

            if (!fs.existsSync(composeFile)) {
                return reject(new Error('Project is missing a docker-compose.yml file.'));
            }

            // Patch the generated docker-compose port to prevent collision with Cloud API on port 8000
            let composeContent = fs.readFileSync(composeFile, 'utf8');
            composeContent = composeContent.replace(/"8000:8000"|8000:8000/g, '"8001:8000"');
            fs.writeFileSync(composeFile, composeContent);

            // Using pure docker compose (V2) instead of docker-compose
            const dockerProcess = spawn('docker', ['compose', 'up', '--build', '-d'], {
                cwd: projectPath,
                stdio: ['ignore', 'pipe', 'pipe']
            });

            this.activeProjects.set(projectId, { path: projectPath, process: dockerProcess });

            dockerProcess.stdout.on('data', (data) => console.log(`[DOCKER ${projectId}]: ${data}`));
            dockerProcess.stderr.on('data', (data) => console.log(`[DOCKER ${projectId}]: ${data}`));

            dockerProcess.on('close', async (code) => {
                if (code !== 0) {
                    return reject(new Error(`Docker Compose failed with exit code ${code}`));
                }

                console.log(`[DockerManager] Containers started for ${projectId}. Waiting for health...`);
                try {
                    await this.waitForHealth(8001); // Wait for the backend running on patched port 8001
                    resolve(true);
                } catch (e) {
                    reject(e);
                }
            });
        });
    }

    /**
     * Polls the backend health endpoint.
     */
    async waitForHealth(port, maxAttempts = 30) {
        const url = `http://localhost:${port}/health`;
        for (let j = 0; j < maxAttempts; j++) {
            try {
                // Dynamically fetch using Node's native fetch
                const res = await fetch(url);
                if (res.ok) return true;
            } catch (e) {
                // Connection refused means container isn't ready
            }
            await new Promise(r => setTimeout(r, 1000));
        }
        throw new Error(`Service at ${url} never became healthy.`);
    }

    /**
     * Stops the running project and prunes its network.
     */
    async stopProject(projectId) {
        const project = this.activeProjects.get(projectId);
        if (!project) return;
        console.log(`[DockerManager] Stopping project ${projectId}...`);

        try {
            await execAsync(`cd "${project.path}" && docker compose down -v`);
            this.activeProjects.delete(projectId);
        } catch (e) {
            console.error(`[DockerManager] Failed to stop ${projectId}`, e);
        }
    }

    /**
     * Clears the Docker detection cache (useful for retrying after installation).
     */
    clearDetectionCache() {
        this.dockerAvailable = null;
    }
}

module.exports = new DockerManager();
