# Design Document: Marketing Website Separation

## Overview

This design document outlines the architecture for separating the marketing website from the Electron desktop application. The solution involves creating two independent React applications: a static marketing website for public consumption and a desktop application for authenticated users to generate backends.

## Architecture

### High-Level Structure

```
frontend/
├── website/                    # NEW: Static marketing site
│   ├── src/
│   │   ├── pages/              # Marketing pages
│   │   ├── components/         # UI components
│   │   ├── assets/             # Images, icons
│   │   ├── App.jsx             # Main app component
│   │   ├── main.jsx            # Entry point
│   │   └── index.css           # Global styles
│   ├── public/
│   │   ├── _redirects          # SPA routing for static hosts
│   │   └── assets/             # Public assets
│   ├── package.json
│   ├── vite.config.js
│   └── README.md
│
└── desktop/                    # RENAMED: Electron app (current frontend/)
    ├── electron/               # Electron main process
    ├── src/
    │   ├── pages/              # Generation pages only
    │   │   └── ChatPage.jsx    # Main generation UI
    │   ├── components/         # Desktop-specific components
    │   ├── context/            # Auth context
    │   ├── App.jsx             # Desktop app component
    │   ├── main.jsx            # Entry point
    │   └── index.css           # Global styles
    ├── public/
    ├── package.json
    ├── vite.config.js
    ├── electron-builder.yml
    └── README.md
```

### Component Distribution

#### Marketing Website Components

**Pages:**
- `LandingPage.jsx` - Hero, features overview, CTA to download
- `DownloadPage.jsx` - NEW: Platform detection, download links, requirements
- `DocsPage.jsx` - Getting started documentation
- `ApiReferencePage.jsx` - API documentation
- `CliGuidePage.jsx` - CLI usage guide
- `AboutPage.jsx` - Team and company information
- `ResearchPage.jsx` - Research articles listing
- `ResearchPostPage.jsx` - Individual research article view

**Components:**
- `Navbar.jsx` - Navigation bar (modified for marketing)
- `Footer.jsx` - Site footer
- `Hero.jsx` - Landing page hero section
- `Features.jsx` - Feature showcase
- `DemoSection.jsx` - Demo/preview section
- `Waitlist.jsx` - Waitlist signup section
- `WaitlistModal.jsx` - Waitlist modal
- `InteriusLogo.jsx` - Company logo
- `ThemeToggle.jsx` - Dark/light mode toggle
- `ScrollToTop.jsx` - Scroll restoration utility

#### Desktop App Components

**Pages:**
- `ChatPage.jsx` - Main generation interface
- `ProjectsPage.jsx` - OPTIONAL: Local projects management

**Components:**
- `LoginModal.jsx` - Authentication modal
- `Navbar.jsx` - Simplified navigation for desktop
- `InteriusLogo.jsx` - Company logo
- `ThemeToggle.jsx` - Dark/light mode toggle

**Context:**
- `AuthContext.jsx` - Authentication state management

**Services:**
- `docker-manager.cjs` - Docker lifecycle management
- `verify-runner.cjs` - Local verification testing

## Components and Interfaces

### Marketing Website

#### Download Page Component

```jsx
// website/src/pages/DownloadPage.jsx

import { useState, useEffect } from 'react';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';

export default function DownloadPage({ theme, onThemeToggle }) {
  const [os, setOS] = useState('');
  const [arch, setArch] = useState('');

  useEffect(() => {
    // Detect user's operating system
    const platform = navigator.platform.toLowerCase();
    const userAgent = navigator.userAgent.toLowerCase();
    
    if (platform.includes('mac') || userAgent.includes('mac')) {
      setOS('mac');
      // Detect Apple Silicon vs Intel
      setArch(navigator.userAgent.includes('ARM') ? 'arm64' : 'x64');
    } else if (platform.includes('win') || userAgent.includes('win')) {
      setOS('windows');
      setArch('x64');
    } else if (platform.includes('linux') || userAgent.includes('linux')) {
      setOS('linux');
      setArch('x64');
    } else {
      setOS('unknown');
    }
  }, []);

  const downloads = {
    mac: {
      name: 'macOS',
      url: 'https://github.com/yourorg/api-builder/releases/latest/download/Interius-macOS.dmg',
      size: '120 MB',
      requirements: ['macOS 10.15 or later', 'Docker Desktop', '4GB RAM'],
      instructions: [
        'Download the .dmg file',
        'Open the downloaded file',
        'Drag Interius to Applications',
        'Launch from Applications folder'
      ]
    },
    windows: {
      name: 'Windows',
      url: 'https://github.com/yourorg/api-builder/releases/latest/download/Interius-Setup.exe',
      size: '95 MB',
      requirements: ['Windows 10 or later', 'Docker Desktop', '4GB RAM'],
      instructions: [
        'Download the .exe installer',
        'Run the installer',
        'Follow the installation wizard',
        'Launch from Start menu'
      ]
    },
    linux: {
      name: 'Linux',
      url: 'https://github.com/yourorg/api-builder/releases/latest/download/Interius.AppImage',
      size: '110 MB',
      requirements: ['Ubuntu 20.04+ or equivalent', 'Docker', '4GB RAM'],
      instructions: [
        'Download the .AppImage file',
        'Make it executable: chmod +x Interius.AppImage',
        'Run: ./Interius.AppImage',
        'Or integrate with your desktop environment'
      ]
    }
  };

  const currentDownload = downloads[os] || downloads.mac;

  return (
    <>
      <Navbar theme={theme} onThemeToggle={onThemeToggle} />
      <div className="download-page">
        <section className="download-hero">
          <h1>Download Interius API Builder</h1>
          <p>Desktop app for AI-powered backend generation with local Docker testing</p>
        </section>

        <section className="download-primary">
          <h2>Download for {currentDownload.name}</h2>
          <a href={currentDownload.url} className="download-button">
            Download Now
          </a>
          <p className="download-size">{currentDownload.size}</p>
        </section>

        <section className="download-requirements">
          <h3>System Requirements</h3>
          <ul>
            {currentDownload.requirements.map((req, i) => (
              <li key={i}>{req}</li>
            ))}
          </ul>
        </section>

        <section className="download-instructions">
          <h3>Installation Instructions</h3>
          <ol>
            {currentDownload.instructions.map((step, i) => (
              <li key={i}>{step}</li>
            ))}
          </ol>
        </section>

        <section className="download-all-platforms">
          <h3>Other Platforms</h3>
          <div className="platform-grid">
            {Object.entries(downloads).map(([key, platform]) => (
              <div key={key} className="platform-card">
                <h4>{platform.name}</h4>
                <p>{platform.size}</p>
                <a href={platform.url}>Download</a>
              </div>
            ))}
          </div>
        </section>

        <section className="download-docker-notice">
          <h3>Docker Desktop Required</h3>
          <p>
            Interius uses Docker to deploy and test generated backends locally.
            If you don't have Docker Desktop installed, download it from:
          </p>
          <a href="https://www.docker.com/products/docker-desktop" target="_blank" rel="noopener noreferrer">
            docker.com/products/docker-desktop
          </a>
        </section>
      </div>
      <Footer />
    </>
  );
}
```

#### Updated Landing Page

```jsx
// website/src/pages/LandingPage.jsx

import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Hero from '../components/Hero';
import DemoSection from '../components/DemoSection';
import Features from '../components/Features';
import Waitlist from '../components/Waitlist';
import Footer from '../components/Footer';
import WaitlistModal from '../components/WaitlistModal';
import { useState } from 'react';

export default function LandingPage({ theme, onThemeToggle }) {
  const [waitlistOpen, setWaitlistOpen] = useState(false);
  const navigate = useNavigate();

  return (
    <>
      <Navbar theme={theme} onThemeToggle={onThemeToggle} />
      <Hero 
        onTryClick={() => navigate('/download')}  // Changed from login
        onOpenWaitlist={() => setWaitlistOpen(true)} 
      />
      <DemoSection onOpenDownload={() => navigate('/download')} />  {/* Changed */}
      <Features 
        onTryApp={() => navigate('/download')}  // Changed from login
        onOpenWaitlist={() => setWaitlistOpen(true)} 
      />
      <Waitlist 
        onTryApp={() => navigate('/download')}  // Changed from login
        onOpenWaitlist={() => setWaitlistOpen(true)} 
      />
      <WaitlistModal isOpen={waitlistOpen} onClose={() => setWaitlistOpen(false)} />
      <Footer />
    </>
  );
}
```

#### Marketing Website App Component

```jsx
// website/src/App.jsx

import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import ScrollToTop from './components/ScrollToTop';
import LandingPage from './pages/LandingPage';
import DownloadPage from './pages/DownloadPage';
import DocsPage from './pages/DocsPage';
import ApiReferencePage from './pages/ApiReferencePage';
import CliGuidePage from './pages/CliGuidePage';
import AboutPage from './pages/AboutPage';
import ResearchPage from './pages/ResearchPage';
import ResearchPostPage from './pages/ResearchPostPage';
import './App.css';

export default function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem('interius-theme') || 'light');

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('interius-theme', theme);
  }, [theme]);

  const toggleTheme = () => setTheme((p) => (p === 'dark' ? 'light' : 'dark'));

  return (
    <BrowserRouter>
      <ScrollToTop />
      <Routes>
        <Route path="/" element={<LandingPage theme={theme} onThemeToggle={toggleTheme} />} />
        <Route path="/download" element={<DownloadPage theme={theme} onThemeToggle={toggleTheme} />} />
        <Route path="/docs" element={<DocsPage theme={theme} onThemeToggle={toggleTheme} />} />
        <Route path="/api" element={<ApiReferencePage theme={theme} onThemeToggle={toggleTheme} />} />
        <Route path="/cli" element={<CliGuidePage theme={theme} onThemeToggle={toggleTheme} />} />
        <Route path="/about" element={<AboutPage theme={theme} onThemeToggle={toggleTheme} />} />
        <Route path="/research" element={<ResearchPage theme={theme} onThemeToggle={toggleTheme} />} />
        <Route path="/research/:id" element={<ResearchPostPage theme={theme} onThemeToggle={toggleTheme} />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
```

### Desktop App

#### Desktop App Component

```jsx
// desktop/src/App.jsx

import { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import ChatPage from './pages/ChatPage';
import LoginModal from './components/LoginModal';
import './App.css';

function AppContent() {
  const { user } = useAuth();
  const [loginOpen, setLoginOpen] = useState(!user);
  const [theme, setTheme] = useState(() => localStorage.getItem('interius-theme') || 'light');

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('interius-theme', theme);
  }, [theme]);

  useEffect(() => {
    // Show login modal if not authenticated
    if (!user) {
      setLoginOpen(true);
    }
  }, [user]);

  const toggleTheme = () => setTheme((p) => (p === 'dark' ? 'light' : 'dark'));

  return (
    <>
      {user ? (
        <ChatPage theme={theme} onThemeToggle={toggleTheme} />
      ) : (
        <div className="login-screen">
          <h1>Welcome to Interius API Builder</h1>
          <p>Sign in to start generating backends</p>
        </div>
      )}
      <LoginModal isOpen={loginOpen} onClose={() => setLoginOpen(false)} />
    </>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
```

## Data Models

### Download Configuration

```typescript
interface PlatformDownload {
  name: string;           // Display name (e.g., "macOS", "Windows")
  url: string;            // Download URL (GitHub Releases or direct)
  size: string;           // File size (e.g., "120 MB")
  requirements: string[]; // System requirements
  instructions: string[]; // Installation steps
}

interface DownloadConfig {
  mac: PlatformDownload;
  windows: PlatformDownload;
  linux: PlatformDownload;
}
```

### OS Detection

```typescript
interface OSDetection {
  os: 'mac' | 'windows' | 'linux' | 'unknown';
  arch: 'x64' | 'arm64' | 'ia32';
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Marketing Website Independence
*For any* deployment of the Marketing_Website, it should function completely without requiring authentication, backend API, or Electron-specific features.

**Validates: Requirements 1.3, 1.4**

### Property 2: Desktop App Authentication Requirement
*For any* launch of the Desktop_App, if the user is not authenticated, the login modal should be displayed and generation features should be inaccessible.

**Validates: Requirements 9.1, 9.2**

### Property 3: Download Page OS Detection
*For any* user visiting the Download page, the system should detect their operating system and display the appropriate download link as the primary option.

**Validates: Requirements 2.2, 2.3**

### Property 4: Content Preservation
*For any* page migrated from the original frontend to the Marketing_Website, all content, styling, and functionality (except authentication and generation) should be preserved.

**Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7**

### Property 5: Call-to-Action Consistency
*For any* call-to-action button on the Marketing_Website that previously triggered login, it should now navigate to the Download page.

**Validates: Requirements 6.1, 6.2, 6.3, 6.4**

### Property 6: Build Independence
*For any* build of the Marketing_Website or Desktop_App, it should complete successfully without requiring the other application's dependencies or files.

**Validates: Requirements 8.1, 8.2, 8.3**

### Property 7: Routing Completeness
*For any* valid route in the Marketing_Website, navigating to that route should display the correct page without errors.

**Validates: Requirements 5.1, 5.2, 5.3, 5.4**

## Error Handling

### Marketing Website

**404 Handling:**
- Invalid routes redirect to home page
- Clear error message for broken links
- Maintain navigation context

**Asset Loading:**
- Graceful fallback for missing images
- Loading states for dynamic content
- Error boundaries for component failures

### Desktop App

**Authentication Errors:**
- Clear error messages for login failures
- Network error handling
- Token expiration handling

**Docker Errors:**
- Docker not installed detection
- Docker not running detection
- Installation guidance display

## Testing Strategy

### Unit Tests

**Marketing Website:**
- Component rendering tests
- OS detection logic tests
- Navigation routing tests
- Theme toggle functionality tests

**Desktop App:**
- Authentication flow tests
- Component rendering tests
- Electron IPC tests

### Integration Tests

**Marketing Website:**
- Full page navigation flows
- Download page platform detection
- Theme persistence across pages

**Desktop App:**
- Login to generation flow
- Docker manager integration
- Verification runner integration

### Property-Based Tests

**Property 1: Marketing Website Independence**
- Test: Deploy Marketing_Website without backend
- Verify: All pages load and function correctly
- Verify: No authentication prompts appear
- Verify: No API calls are made

**Property 2: Desktop App Authentication Requirement**
- Test: Launch Desktop_App without stored credentials
- Verify: Login modal is displayed
- Verify: ChatPage is not accessible
- Test: Launch Desktop_App with valid credentials
- Verify: ChatPage is displayed immediately

**Property 3: Download Page OS Detection**
- Test: Visit Download page with various user agents (Mac, Windows, Linux)
- Verify: Correct OS is detected for each
- Verify: Appropriate download link is displayed as primary

**Property 4: Content Preservation**
- Test: Compare rendered output of migrated pages
- Verify: All text content matches original
- Verify: All images and assets are present
- Verify: Styling is consistent

**Property 5: Call-to-Action Consistency**
- Test: Click all CTA buttons on Marketing_Website
- Verify: All navigate to Download page (not login)
- Verify: No authentication modals appear

**Property 6: Build Independence**
- Test: Build Marketing_Website in isolation
- Verify: Build completes without errors
- Verify: No Desktop_App dependencies required
- Test: Build Desktop_App in isolation
- Verify: Build completes without errors
- Verify: No Marketing_Website dependencies required

**Property 7: Routing Completeness**
- Test: Navigate to all defined routes
- Verify: Each route renders correct page
- Verify: No 404 errors for valid routes
- Test: Navigate to invalid route
- Verify: Redirects to home page

### Manual Testing

**Marketing Website:**
- Visual regression testing
- Cross-browser compatibility (Chrome, Firefox, Safari, Edge)
- Mobile responsiveness
- Download links functionality

**Desktop App:**
- Electron packaging for all platforms
- Installation process on each OS
- Docker integration
- Generation workflow end-to-end

## Deployment

### Marketing Website Deployment

**Platform:** Netlify, Vercel, or GitHub Pages

**Build Command:**
```bash
cd frontend/website
npm install
npm run build
```

**Output Directory:** `frontend/website/dist`

**Environment Variables:** None required

**Redirects Configuration:**
```
# frontend/website/public/_redirects
/*    /index.html   200
```

### Desktop App Packaging

**Build Commands:**
```bash
cd frontend/desktop
npm install
npm run electron:build:mac     # macOS
npm run electron:build:win     # Windows
npm run electron:build:linux   # Linux
```

**Output Directory:** `frontend/desktop/dist-electron`

**Distribution:** GitHub Releases or direct download hosting

## Migration Steps

### Phase 1: Create Marketing Website Structure
1. Create `frontend/website/` directory
2. Set up package.json and Vite config
3. Create basic App.jsx and routing structure

### Phase 2: Copy Marketing Pages
1. Copy all non-generation pages to `website/src/pages/`
2. Copy shared components to `website/src/components/`
3. Copy assets and styles

### Phase 3: Create Download Page
1. Implement DownloadPage component
2. Add OS detection logic
3. Configure download links
4. Add installation instructions

### Phase 4: Update Call-to-Actions
1. Replace login CTAs with download navigation
2. Remove authentication references
3. Update Hero, Features, and other sections

### Phase 5: Restructure Desktop App
1. Rename `frontend/` to `frontend/desktop/`
2. Remove marketing pages
3. Simplify App.jsx to focus on generation
4. Update navigation

### Phase 6: Testing and Validation
1. Test Marketing_Website build and deployment
2. Test Desktop_App packaging
3. Verify all properties
4. Manual testing on all platforms

### Phase 7: Documentation
1. Update root README
2. Create Marketing_Website README
3. Create Desktop_App README
4. Update deployment guides
