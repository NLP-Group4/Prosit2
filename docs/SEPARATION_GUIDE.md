# Backend/Frontend Separation Guide

**Quick Answer:** Your project is **already separated** and ready for independent deployment!

---

## Current Structure

```
api_builder/
├── backend/                    # Backend (Cloud-Ready) ✅
│   ├── app/                    # FastAPI platform API
│   ├── agents/                 # LLM agents
│   ├── config/                 # Configuration
│   ├── tests/                  # Test suite
│   ├── scripts/                # Utility scripts
│   ├── docker-compose.yml      # Cloud deployment
│   ├── Dockerfile              # Container definition
│   ├── requirements.txt        # Python dependencies
│   └── README.md               # Backend documentation
│
├── frontend/                   # Frontend Applications ✅
│   ├── website/                # Marketing Website (Static Site)
│   │   ├── src/                # React components and pages
│   │   │   ├── pages/          # Landing, Download, Docs, About, Research
│   │   │   ├── components/     # Navbar, Footer, Hero, Features, etc.
│   │   │   └── assets/         # Images and icons
│   │   ├── public/             # Static assets and _redirects
│   │   ├── package.json        # Node dependencies
│   │   ├── vite.config.js      # Vite build configuration
│   │   └── README.md           # Website documentation
│   │
│   └── desktop/                # Desktop App (Electron)
│       ├── electron/           # Electron main process
│       │   ├── main.cjs        # Electron entrypoint
│       │   ├── preload.cjs     # Preload script
│       │   └── services/       # Docker manager, verification runner
│       ├── src/                # React UI (generation interface)
│       │   ├── pages/          # ChatPage (generation UI)
│       │   ├── components/     # LoginModal, Navbar, etc.
│       │   └── context/        # AuthContext
│       ├── package.json        # Node dependencies
│       ├── electron-builder.yml # Build configuration
│       ├── BUILD.md            # Build instructions
│       └── README.md           # Desktop app documentation
│
├── docs/                       # Shared documentation
├── .env                        # Shared environment (gitignored)
└── README.md                   # Project overview
```

---

## What You Can Do Right Now

### 1. Deploy Backend to Cloud

The backend is **completely independent** and ready to deploy:

```bash
# Option A: Railway (Easiest)
cd backend
railway init
railway up

# Option B: Docker anywhere
cd backend
docker build -t backend-api .
docker run -p 8000:8000 backend-api

# Option C: AWS, Render, DigitalOcean, etc.
# See DEPLOYMENT_GUIDE.md
```

**Backend includes:**
- ✅ FastAPI application
- ✅ LLM agents (Gemini + Groq)
- ✅ PostgreSQL database
- ✅ JWT authentication
- ✅ Project generation
- ✅ Auto-fix
- ✅ Dockerized and ready

### 2. Deploy Marketing Website

The marketing website is **completely independent** and ready to deploy:

```bash
# Build for production
cd frontend/website
npm install
npm run build

# Deploy to Netlify (recommended)
netlify deploy --prod --dir=dist

# Or deploy to Vercel
vercel --prod

# Or deploy to GitHub Pages
# Push dist/ to gh-pages branch
```

**Marketing Website includes:**
- ✅ Landing page with product information
- ✅ Download page with platform detection
- ✅ Documentation pages (Docs, API, CLI)
- ✅ About and Research pages
- ✅ No authentication required
- ✅ Static site (fast, cheap hosting)

### 3. Package Desktop App

The desktop app is **completely independent** and ready to package:

```bash
# Build for macOS
cd frontend/desktop
npm install
npm run package:mac

# Build for Windows
npm run package:win

# Build for Linux
npm run package:linux
```

**Desktop App includes:**
- ✅ Electron desktop app
- ✅ React UI (generation interface)
- ✅ Docker manager
- ✅ Verification runner
- ✅ API client
- ✅ Authentication
- ✅ Build configuration

---

## How They Communicate

```
┌─────────────────────────────────────┐
│  Marketing Website (Static)         │
│  - Hosted on Netlify/Vercel         │
│  - No backend communication         │
│  - Download links to installers     │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  Desktop App (User's Computer)      │
│                                      │
│  ┌────────────────────────────────┐ │
│  │  API Client                    │ │
│  │  - Sends HTTP requests         │ │
│  │  - JWT authentication          │ │
│  └────────────────────────────────┘ │
└─────────────────────────────────────┘
                 │
                 │ HTTPS
                 │
┌─────────────────────────────────────┐
│  Backend API (Cloud)                │
│                                      │
│  ┌────────────────────────────────┐ │
│  │  FastAPI Endpoints             │ │
│  │  - /auth/login                 │ │
│  │  - /generate-from-prompt       │ │
│  │  - /projects/{id}/download     │ │
│  └────────────────────────────────┘ │
└─────────────────────────────────────┘
```

**Communication:**
- Marketing Website: Static site, no backend communication
- Desktop App: Makes HTTP requests to backend API
- Backend URL is configurable (localhost for dev, cloud for production)
- JWT tokens for authentication
- No tight coupling - pure REST API

---

## Configuration for Separation

### Backend Configuration

**No changes needed!** The backend is already designed to be deployed independently.

**Environment variables:**
```env
# .env (backend)
GOOGLE_API_KEY=your-key
GROQ_API_KEY=your-key
PLATFORM_DATABASE_URL=postgresql://...
PLATFORM_SECRET_KEY=your-secret
CORS_ORIGINS=*  # Allow Desktop App and Marketing Website
```

### Marketing Website Configuration

**No backend configuration needed!** The marketing website is static and doesn't communicate with the backend.

**Build configuration:**
```javascript
// frontend/website/vite.config.js
export default {
  base: '/',  // For root domain deployment
  build: {
    outDir: 'dist',
    // ... other build options
  }
}
```

### Desktop App Configuration

**Update API endpoint** to point to your cloud backend:

```javascript
// frontend/desktop/src/services/api-client.js

const API_BASE_URL = process.env.NODE_ENV === 'production'
  ? 'https://your-backend.railway.app'  // ← Change this
  : 'http://localhost:8000';

export class ApiClient {
  constructor() {
    this.baseUrl = API_BASE_URL;
    // ... rest of code
  }
}
```

That's it! No other changes needed.

---

## Deployment Workflow

### Step 1: Deploy Backend

```bash
# 1. Choose cloud provider (Railway, AWS, Render, etc.)
# 2. Deploy backend
cd backend
railway up

# 3. Get backend URL
railway domain
# Output: https://your-app.railway.app

# 4. Test backend
curl https://your-app.railway.app/health
```

### Step 2: Deploy Marketing Website

```bash
# 1. Build marketing website
cd frontend/website
npm install
npm run build

# 2. Deploy to Netlify (recommended)
netlify deploy --prod --dir=dist

# 3. Get website URL
# Output: https://your-site.netlify.app

# 4. Test website
# Visit https://your-site.netlify.app
# Verify all pages load
# Test download links
```

### Step 3: Update Desktop App

```bash
# 1. Update API endpoint in desktop app
cd frontend/desktop
# Edit src/services/api-client.js
# Change API_BASE_URL to your backend URL

# 2. Build desktop app
npm run build
```

### Step 4: Package Desktop App

```bash
# Package for distribution
npm run package:mac    # macOS
npm run package:win    # Windows
npm run package:linux  # Linux

# Output: frontend/desktop/dist/Backend-Generator-1.0.0.dmg (or .exe, .AppImage)
```

### Step 5: Upload Installers

```bash
# 1. Create GitHub release
# 2. Upload installers (.dmg, .exe, .AppImage)
# 3. Update download links in marketing website
# 4. Redeploy marketing website with updated links
```

### Step 6: Distribute

```bash
# Users visit marketing website
# Download installer for their platform
# Install desktop app
# App connects to cloud backend automatically
```

---

## What Stays Together vs. What Separates

### Backend (Cloud)

**Stays together:**
- `backend/app/` - FastAPI application
- `backend/agents/` - LLM agents
- `backend/config/` - Configuration
- `backend/tests/` - Test suite
- `backend/scripts/` - Utility scripts
- `backend/docker-compose.yml` - Deployment config

**Deployed as:** Single Docker container or cloud service

**Runs on:** Cloud infrastructure (Railway, AWS, etc.)

### Marketing Website (Static Site)

**Stays together:**
- `frontend/website/src/` - React components and pages
- `frontend/website/public/` - Static assets
- `frontend/website/package.json` - Dependencies

**Deployed as:** Static files (HTML, CSS, JS)

**Runs on:** CDN (Netlify, Vercel, GitHub Pages)

**Purpose:** Public information, documentation, download links

### Desktop App (Desktop)

**Stays together:**
- `frontend/desktop/electron/` - Electron main process
- `frontend/desktop/src/` - React UI (generation interface)
- `frontend/desktop/package.json` - Dependencies

**Packaged as:** Desktop application (.dmg, .exe, .AppImage)

**Runs on:** User's computer

**Purpose:** Generation interface, authentication, local Docker integration

---

## Benefits of This Architecture

### ✅ Independent Deployment

- Deploy backend without touching frontend
- Deploy marketing website without touching backend or desktop app
- Update desktop app without redeploying backend or website
- Different release cycles for each component

### ✅ Scalability

- Scale backend independently (add more servers)
- Marketing website served from CDN (fast, global)
- Desktop app runs on user's machine (no server load)
- Docker verification happens locally (free compute)

### ✅ Development

- Backend team works independently
- Marketing team works independently
- Desktop app team works independently
- Clear API contract between components

### ✅ Distribution

- Backend: One deployment for all users
- Marketing Website: Fast, cheap hosting on CDN
- Desktop App: Users download once, auto-update
- No server costs for marketing content

---

## Common Questions

### Q: Do I need to split the repository?

**A:** No! The current monorepo structure is perfect. You can:
- Keep everything in one repo (monorepo)
- Deploy backend from `backend/` directory
- Deploy marketing website from `frontend/website/` directory
- Package desktop app from `frontend/desktop/` directory
- Share documentation in `docs/`

### Q: Can I run everything locally for development?

**A:** Yes! That's the default:
```bash
# Terminal 1: Backend
cd backend
uvicorn app.main:app --reload

# Terminal 2: Marketing Website
cd frontend/website
npm run dev

# Terminal 3: Desktop App
cd frontend/desktop
npm run electron:dev
```

### Q: How do I update the backend URL in production?

**A:** For the desktop app, two options:

**Option 1: Hardcode in build**
```javascript
const API_BASE_URL = 'https://your-backend.railway.app';
```

**Option 2: Environment variable**
```javascript
const API_BASE_URL = process.env.API_URL || 'https://your-backend.railway.app';
```

Then build with:
```bash
API_URL=https://your-backend.railway.app npm run package
```

The marketing website doesn't need backend configuration.

### Q: Do I need separate databases?

**A:** No! One PostgreSQL database for the backend. The marketing website and desktop app don't need databases - the website is static, and the desktop app makes API calls.

### Q: Can users run the backend locally?

**A:** Yes! The generated backends run locally in Docker. The **platform backend** (your API) runs in the cloud.

### Q: How do I update download links on the marketing website?

**A:** Edit `frontend/website/src/pages/DownloadPage.jsx` and update the download URLs to point to your GitHub releases or hosting location. Then rebuild and redeploy the website.

---

## Quick Start Commands

### Deploy Backend to Railway

```bash
# From backend directory
cd backend
railway init
railway add --database postgresql
railway up
railway domain  # Get your URL
```

### Deploy Marketing Website to Netlify

```bash
# From website directory
cd frontend/website
npm install
npm run build
netlify deploy --prod --dir=dist
```

### Package Desktop App

```bash
# Update API URL first!
cd frontend/desktop
npm install
npm run package:mac  # or :win or :linux
```

### Test Everything

```bash
# Test backend
curl https://your-backend.railway.app/health

# Test marketing website
# Visit https://your-site.netlify.app
# Verify all pages load
# Test download links

# Test desktop app
# Install the packaged app
# Login/Register
# Generate a project
# Deploy locally
```

---

## Next Steps

1. **Read [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)** for detailed deployment instructions
2. **Choose a cloud provider** (Railway recommended for quick start)
3. **Deploy backend** following the guide
4. **Update frontend** with cloud backend URL
5. **Package frontend** for your platform
6. **Test and distribute**

---

## Summary

✅ **Your project is already separated and ready!**

- Backend: Independent, cloud-ready, Dockerized
- Marketing Website: Independent, static site, CDN-ready
- Desktop App: Independent, packageable, Electron app
- Communication: REST API over HTTPS (desktop app to backend)
- No restructuring needed
- Deploy backend → Deploy marketing website → Update desktop app URL → Package → Distribute

See [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) for step-by-step instructions.

---

**Last Updated:** February 23, 2026  
**Status:** Ready for Deployment
