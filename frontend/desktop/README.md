# Interius API Builder - Desktop Application

The Interius API Builder Desktop Application is an Electron-based tool for generating production-ready FastAPI backends from natural language prompts. This application provides a local development environment with Docker integration for testing generated backends.

## Purpose

This desktop application is the **generation interface** for Interius API Builder. It provides:

- **AI-Powered Backend Generation**: Generate FastAPI backends from natural language descriptions
- **Local Docker Testing**: Deploy and test generated backends locally using Docker
- **Authentication**: Secure user authentication and project management
- **Offline Capability**: Work on projects locally with cloud sync

This is separate from the marketing website (`frontend/website/`), which provides informational content and download links.

## Prerequisites

Before running or building the desktop app, ensure you have:

- **Node.js** 18.x or later
- **npm** 9.x or later
- **Docker Desktop** (required for local backend testing)
  - Download from: https://www.docker.com/products/docker-desktop
- **Electron** (installed via npm dependencies)

## Installation

```bash
# Navigate to the desktop app directory
cd frontend/desktop

# Install dependencies
npm install
```

## Development

### Running in Development Mode

```bash
# Start the Vite dev server and Electron app
npm run electron:dev
```

This command:
1. Starts the Vite development server on port 5173
2. Waits for the server to be ready
3. Launches the Electron app with hot module replacement (HMR)

### Running Components Separately

```bash
# Run only the Vite dev server
npm run dev

# Run only Electron (requires dev server to be running)
npm run electron
```

### Development Workflow

1. Start the development server: `npm run electron:dev`
2. The app will open with the login screen
3. Sign in with your credentials
4. Use the ChatPage interface to generate backends
5. Changes to React components will hot-reload automatically
6. Changes to Electron main process require restarting the app

## Building and Packaging

### Build for Development Testing

```bash
# Build the React app without packaging
npm run build

# Preview the production build
npm run preview
```

### Package for Distribution

```bash
# Package for current platform
npm run electron:build

# Package for specific platforms
npm run electron:build:mac      # macOS (Intel + Apple Silicon)
npm run electron:build:win      # Windows (x64 + ia32)
npm run electron:build:linux    # Linux (AppImage, deb, rpm)

# Package for all platforms
npm run electron:build:all
```

### Build Output

Packaged applications are output to `dist-electron/`:

- **macOS**: `.dmg` installer and `.zip` archive
- **Windows**: `.exe` NSIS installer and portable `.exe`
- **Linux**: `.AppImage`, `.deb`, and `.rpm` packages

## Project Structure

```
frontend/desktop/
├── electron/                   # Electron main process
│   ├── main.cjs               # Main process entry point
│   ├── preload.cjs            # Preload script for IPC
│   └── services/              # Electron services
│       ├── docker-manager.cjs # Docker lifecycle management
│       └── verify-runner.cjs  # Local verification testing
├── src/                       # React application
│   ├── pages/                 # Application pages
│   │   └── ChatPage.jsx       # Main generation interface
│   ├── components/            # React components
│   │   ├── LoginModal.jsx     # Authentication modal
│   │   ├── Navbar.jsx         # Navigation bar
│   │   ├── InteriusLogo.jsx   # Company logo
│   │   └── ThemeToggle.jsx    # Dark/light mode toggle
│   ├── context/               # React context
│   │   └── AuthContext.jsx    # Authentication state
│   ├── App.jsx                # Main app component
│   ├── main.jsx               # React entry point
│   └── index.css              # Global styles
├── public/                    # Static assets
├── assets/                    # Build resources (icons, etc.)
├── package.json               # Dependencies and scripts
├── vite.config.js             # Vite configuration
├── electron-builder.yml       # Electron Builder configuration
└── README.md                  # This file
```

## Configuration

### API Endpoint Configuration

The desktop app communicates with the Interius backend API. Configure the API endpoint:

**Development:**
- Default: `http://127.0.0.1:8000`
- Override with environment variable: `VITE_API_URL`

```bash
# .env file (create in frontend/desktop/)
VITE_API_URL=http://localhost:8000
```

**Production:**
- The API endpoint is configured in the Electron main process
- Users can configure it through the app settings (if implemented)

### Vite Configuration

The Vite configuration (`vite.config.js`) includes:

- **React Plugin**: Fast Refresh for development
- **API Proxy**: Proxies `/api` requests to the backend during development
- **Build Output**: Builds to `dist/` directory

### Electron Builder Configuration

The Electron Builder configuration (`electron-builder.yml`) defines:

- **App ID**: `com.interius.apibuilder`
- **Product Name**: Interius API Builder
- **Output Directory**: `dist-electron/`
- **Platform Targets**: macOS (dmg, zip), Windows (nsis, portable), Linux (AppImage, deb, rpm)
- **Code Signing**: Configured for macOS notarization (requires Apple Developer account)
- **Auto-Update**: Configured for GitHub Releases

## Electron-Specific Features

### Docker Manager Service

Located in `electron/services/docker-manager.cjs`, this service:

- Detects if Docker Desktop is installed and running
- Manages Docker container lifecycle for generated backends
- Provides status updates to the renderer process via IPC

### Verification Runner Service

Located in `electron/services/verify-runner.cjs`, this service:

- Runs automated tests on generated backends
- Executes verification scripts in Docker containers
- Reports test results to the renderer process

### IPC Communication

The app uses Electron's IPC (Inter-Process Communication) for:

- Docker status checks
- Container management (start, stop, logs)
- File system operations
- Verification test execution

### Preload Script

The preload script (`electron/preload.cjs`) exposes safe APIs to the renderer process:

```javascript
// Available in renderer via window.electron
window.electron.docker.status()
window.electron.docker.start(containerId)
window.electron.docker.stop(containerId)
window.electron.verify.run(projectPath)
```

## Authentication

The desktop app requires authentication to access generation features:

1. **Login Modal**: Displayed on app launch if not authenticated
2. **AuthContext**: Manages authentication state across the app
3. **Token Storage**: Securely stores authentication tokens using `keytar`
4. **Session Persistence**: Maintains login state across app restarts

### Authentication Flow

1. User launches the app
2. If not authenticated, LoginModal is displayed
3. User enters credentials
4. App authenticates with the backend API
5. Token is stored securely
6. ChatPage (generation interface) is displayed

## Troubleshooting

### Docker Not Found

If the app reports that Docker is not found:

1. Ensure Docker Desktop is installed
2. Start Docker Desktop
3. Restart the Interius app

### Build Failures

If packaging fails:

1. Ensure all dependencies are installed: `npm install`
2. Clear the build cache: `rm -rf dist dist-electron`
3. Rebuild: `npm run electron:build`

### Development Server Issues

If the dev server won't start:

1. Check if port 5173 is already in use
2. Kill any existing processes: `lsof -ti:5173 | xargs kill -9`
3. Restart: `npm run electron:dev`

### Electron App Won't Launch

If Electron won't launch:

1. Check the console for errors
2. Ensure the dev server is running on port 5173
3. Try running components separately: `npm run dev` then `npm run electron`

## Testing

### Manual Testing

1. Launch the app: `npm run electron:dev`
2. Test authentication flow
3. Test backend generation
4. Test Docker integration
5. Test verification runner

### Automated Testing

(To be implemented)

## Deployment

### Creating a Release

1. Update version in `package.json`
2. Build for all platforms: `npm run electron:build:all`
3. Test installers on each platform
4. Create a GitHub Release
5. Upload installers to the release
6. Update download links on the marketing website

### Code Signing (macOS)

For macOS distribution, you need:

1. Apple Developer account
2. Developer ID Application certificate
3. App-specific password for notarization

Configure in `electron-builder.yml` and `scripts/notarize.js`.

### Auto-Updates

The app is configured for auto-updates via GitHub Releases:

1. Users are notified when a new version is available
2. Updates are downloaded in the background
3. Users can install updates on next launch

## Contributing

When contributing to the desktop app:

1. Follow the existing code structure
2. Test on multiple platforms if possible
3. Ensure Docker integration works
4. Update this README if adding new features
5. Do not include marketing content (that belongs in `frontend/website/`)

## Related Documentation

- **Marketing Website**: `frontend/website/README.md`
- **Backend API**: `backend/README.md`
- **Project Root**: `README.md`
- **Deployment Guide**: `docs/DEPLOYMENT_GUIDE.md`
- **Separation Guide**: `docs/SEPARATION_GUIDE.md`

## License

Copyright © 2026 Interius. All rights reserved.
