# Building Interius API Builder Desktop App

This guide explains how to build distributable packages of the Interius API Builder Electron app.

## Prerequisites

1. **Node.js 18+** installed
2. **npm** or **yarn** package manager
3. **Platform-specific requirements:**
   - **macOS**: Xcode Command Line Tools
   - **Windows**: Windows SDK, Visual Studio Build Tools
   - **Linux**: Standard build tools (`build-essential` on Debian/Ubuntu)

## Installation

Install dependencies:

```bash
cd frontend
npm install
```

## Development Build

Run the app in development mode with hot reload:

```bash
npm run electron:dev
```

This starts:
- Vite dev server on `http://localhost:5173`
- Electron app loading the dev server

## Production Builds

### Build for Current Platform

```bash
npm run electron:build
```

This creates a distributable package for your current platform in `dist-electron/`.

### Build for Specific Platforms

**macOS:**
```bash
npm run electron:build:mac
```

Outputs:
- `dist-electron/Interius API Builder-1.0.0.dmg` (installer)
- `dist-electron/Interius API Builder-1.0.0-mac.zip` (portable)
- `dist-electron/Interius API Builder-1.0.0-arm64.dmg` (Apple Silicon)
- `dist-electron/Interius API Builder-1.0.0-x64.dmg` (Intel)

**Windows:**
```bash
npm run electron:build:win
```

Outputs:
- `dist-electron/Interius API Builder Setup 1.0.0.exe` (installer)
- `dist-electron/Interius API Builder 1.0.0.exe` (portable)

**Linux:**
```bash
npm run electron:build:linux
```

Outputs:
- `dist-electron/Interius API Builder-1.0.0.AppImage` (universal)
- `dist-electron/interius-api-builder_1.0.0_amd64.deb` (Debian/Ubuntu)
- `dist-electron/interius-api-builder-1.0.0.x86_64.rpm` (Fedora/RHEL)

### Build for All Platforms

```bash
npm run electron:build:all
```

**Note:** Cross-platform builds have limitations:
- macOS builds can only be created on macOS
- Windows builds work best on Windows (but can be built on macOS/Linux with Wine)
- Linux builds can be created on any platform

## Code Signing & Notarization

### macOS

For distribution outside the Mac App Store, you need:

1. **Apple Developer Account** ($99/year)
2. **Developer ID Application Certificate**
3. **App-specific password** for notarization

Set environment variables:

```bash
export APPLE_ID="your-apple-id@example.com"
export APPLE_ID_PASSWORD="xxxx-xxxx-xxxx-xxxx"  # App-specific password
export APPLE_TEAM_ID="XXXXXXXXXX"  # Your team ID
```

Then build:

```bash
npm run electron:build:mac
```

The app will be automatically signed and notarized.

### Windows

For code signing on Windows:

1. Obtain a **Code Signing Certificate** (e.g., from DigiCert, Sectigo)
2. Set environment variables:

```bash
set CSC_LINK=path\to\certificate.pfx
set CSC_KEY_PASSWORD=your-certificate-password
```

Then build:

```bash
npm run electron:build:win
```

### Skip Code Signing (Development)

To build without code signing:

```bash
export CSC_IDENTITY_AUTO_DISCOVERY=false
npm run electron:build
```

## Auto-Updates

The app is configured to check for updates from GitHub releases.

### Setup

1. Create a GitHub repository (e.g., `interius/api-builder-desktop`)
2. Update `electron-builder.yml`:
   ```yaml
   publish:
     provider: github
     owner: your-org
     repo: your-repo
   ```
3. Generate a GitHub token with `repo` scope
4. Set environment variable:
   ```bash
   export GH_TOKEN="your-github-token"
   ```

### Publishing a Release

1. Update version in `package.json`
2. Build and publish:
   ```bash
   npm run electron:build -- --publish always
   ```

This uploads the build artifacts to GitHub Releases and generates update manifests.

## Build Configuration

The build is configured in `electron-builder.yml`. Key settings:

- **App ID**: `com.interius.apibuilder`
- **Product Name**: `Interius API Builder`
- **Output Directory**: `dist-electron/`
- **Compression**: Maximum (smaller file size)
- **Asar**: Enabled (faster startup)

### Customizing the Build

Edit `electron-builder.yml` to customize:

- App icons (place in `assets/`)
- File associations
- Auto-update settings
- Installer options
- Platform-specific settings

## Icons

Place app icons in `frontend/assets/`:

- **macOS**: `icon.icns` (512x512 minimum)
- **Windows**: `icon.ico` (256x256 minimum)
- **Linux**: `icon.png` (512x512 minimum)

Generate icons from a single PNG:

```bash
# Install icon generator
npm install -g electron-icon-maker

# Generate all icon formats
electron-icon-maker --input=icon.png --output=assets
```

## Troubleshooting

### Build Fails on macOS

**Error:** "No identity found"

**Solution:** Either:
1. Obtain a Developer ID certificate from Apple
2. Or disable code signing: `export CSC_IDENTITY_AUTO_DISCOVERY=false`

### Build Fails on Windows

**Error:** "wine not found"

**Solution:** Install Wine (for cross-platform builds):
```bash
# macOS
brew install wine-stable

# Linux
sudo apt-get install wine
```

### App Won't Start

**Error:** "App is damaged and can't be opened"

**Solution:** The app needs to be notarized (macOS) or signed (Windows). For development:
```bash
# macOS: Remove quarantine attribute
xattr -cr "dist-electron/mac/Interius API Builder.app"
```

### Large File Size

The app bundle includes Node.js and Chromium, so it's typically 100-200 MB.

To reduce size:
- Enable `asar: true` (already enabled)
- Use `compression: maximum` (already enabled)
- Exclude unnecessary `node_modules` in `electron-builder.yml`

## CI/CD Integration

### GitHub Actions

Create `.github/workflows/build.yml`:

```yaml
name: Build and Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [macos-latest, windows-latest, ubuntu-latest]
    
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: 18
      
      - name: Install dependencies
        run: |
          cd frontend
          npm install
      
      - name: Build
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          cd frontend
          npm run electron:build -- --publish always
```

## Distribution

### macOS

- **DMG**: Drag-and-drop installer (recommended)
- **ZIP**: Portable version
- Distribute via:
  - Direct download
  - GitHub Releases
  - Homebrew Cask (advanced)

### Windows

- **NSIS Installer**: Full installer with uninstaller
- **Portable EXE**: No installation required
- Distribute via:
  - Direct download
  - GitHub Releases
  - Chocolatey (advanced)
  - Microsoft Store (requires certification)

### Linux

- **AppImage**: Universal, no installation
- **DEB**: Debian/Ubuntu package
- **RPM**: Fedora/RHEL package
- Distribute via:
  - Direct download
  - GitHub Releases
  - Snap Store (requires setup)
  - Flathub (requires setup)

## Testing Builds

Before distributing:

1. **Test on clean machines** (VMs recommended)
2. **Verify auto-updates** work
3. **Check code signing** (macOS/Windows)
4. **Test Docker integration** on each platform
5. **Verify all features** work in production build

## Support

For build issues:
- Check [electron-builder docs](https://www.electron.build/)
- Review [Electron docs](https://www.electronjs.org/docs)
- Open an issue on GitHub

## License

See LICENSE file in the root directory.
