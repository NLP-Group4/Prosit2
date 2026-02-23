# Deployment Guide

**Date:** February 23, 2026  
**Status:** Production-Ready  
**Architecture:** Cloud Backend + Electron Desktop App

---

## Overview

The Backend Generation Platform is designed with a **cloud + desktop split architecture**:

- **Backend (Cloud)** - FastAPI platform API deployed to cloud infrastructure (located in `backend/` directory)
- **Frontend (Desktop)** - Electron app packaged for user download (located in `frontend/` directory)

This guide covers deploying the backend to the cloud and packaging the Electron app for distribution.

**Note:** The backend code is now organized in the `backend/` directory. All deployment commands should be run from the `backend/` directory unless otherwise specified.

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────┐
│                    Cloud Infrastructure                      │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Backend API (FastAPI)                               │  │
│  │  - User authentication                               │  │
│  │  - Project generation (LLM agents)                   │  │
│  │  - Code generation                                   │  │
│  │  - Auto-fix                                          │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  PostgreSQL Database                                 │  │
│  │  - User accounts                                     │  │
│  │  - Project metadata                                  │  │
│  │  - Verification results                              │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ HTTPS API
                           │
┌─────────────────────────────────────────────────────────────┐
│                    User's Computer                           │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Electron Desktop App                                │  │
│  │  - Login/Register UI                                 │  │
│  │  - Project management                                │  │
│  │  - Local Docker deployment                           │  │
│  │  - Verification runner                               │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Docker (User's Machine)                             │  │
│  │  - Runs generated backends locally                   │  │
│  │  - Verification testing                              │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Part 1: Deploy Backend to Cloud

### Prerequisites

- Cloud provider account (AWS, Railway, Render, DigitalOcean, etc.)
- PostgreSQL database (managed or self-hosted)
- Domain name (optional but recommended)
- API keys (Google Gemini, Groq)

### Option A: Deploy to Railway (Recommended for Quick Start)

Railway provides easy deployment with automatic PostgreSQL provisioning.

#### 1. Prepare Backend for Deployment

The backend is already containerized and ready. No changes needed!

#### 2. Create Railway Project

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Navigate to backend directory
cd backend

# Initialize project
railway init
```

#### 3. Add PostgreSQL Database

```bash
# Add PostgreSQL service
railway add --database postgresql
```

#### 4. Set Environment Variables

In Railway dashboard, add these environment variables:

```env
# API Keys
GOOGLE_API_KEY=your-gemini-api-key
GROQ_API_KEY=your-groq-api-key

# Database (auto-provided by Railway)
PLATFORM_DATABASE_URL=${{Postgres.DATABASE_URL}}

# Security
PLATFORM_SECRET_KEY=your-secret-key-here

# CORS (allow Electron app)
CORS_ORIGINS=*

# Optional
GOOGLE_GENAI_USE_VERTEXAI=0
```

#### 5. Deploy

```bash
# Deploy backend
railway up

# Get deployment URL
railway domain
```

Your backend will be available at: `https://your-app.railway.app`

#### 6. Initialize Database

```bash
# Connect to Railway PostgreSQL
railway connect postgres

# Run schema (from backend directory)
\i config/database_setup.sql
```

### Option B: Deploy to AWS (Production-Grade)

#### Architecture

```
AWS ECS (Fargate) → Application Load Balancer → Route 53
                  ↓
              RDS PostgreSQL
```

#### 1. Prepare Docker Image

```bash
# Navigate to backend directory
cd backend

# Build and tag
docker build -t backend-api:latest .

# Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
docker tag backend-api:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/backend-api:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/backend-api:latest
```

#### 2. Create RDS PostgreSQL Database

```bash
# Create database
aws rds create-db-instance \
  --db-instance-identifier backend-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username admin \
  --master-user-password <password> \
  --allocated-storage 20
```

#### 3. Create ECS Task Definition

```json
{
  "family": "backend-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "containerDefinitions": [
    {
      "name": "api",
      "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/backend-api:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "PLATFORM_DATABASE_URL",
          "value": "postgresql://admin:<password>@<rds-endpoint>:5432/platform_db"
        },
        {
          "name": "GOOGLE_API_KEY",
          "value": "<your-key>"
        },
        {
          "name": "GROQ_API_KEY",
          "value": "<your-key>"
        },
        {
          "name": "PLATFORM_SECRET_KEY",
          "value": "<your-secret>"
        }
      ]
    }
  ]
}
```

#### 4. Create ECS Service with Load Balancer

```bash
# Create service
aws ecs create-service \
  --cluster backend-cluster \
  --service-name backend-api \
  --task-definition backend-api \
  --desired-count 2 \
  --launch-type FARGATE \
  --load-balancers targetGroupArn=<target-group-arn>,containerName=api,containerPort=8000
```

### Option C: Deploy to Render

#### 1. Create render.yaml

```yaml
services:
  - type: web
    name: backend-api
    env: docker
    dockerfilePath: ./Dockerfile
    envVars:
      - key: GOOGLE_API_KEY
        sync: false
      - key: GROQ_API_KEY
        sync: false
      - key: PLATFORM_SECRET_KEY
        generateValue: true
      - key: PLATFORM_DATABASE_URL
        fromDatabase:
          name: platform-db
          property: connectionString

databases:
  - name: platform-db
    databaseName: platform_db
    user: platform_user
```

#### 2. Deploy

```bash
# Connect to Render
render login

# Deploy
render deploy
```

---

## Part 2: Package Electron App for Distribution

### Prerequisites

- Node.js 18+ installed
- Code signing certificates (optional, for production)

### 1. Update API Endpoint Configuration

Update the Electron app to point to your cloud backend:

```javascript
// frontend/src/services/api-client.js

const API_BASE_URL = process.env.NODE_ENV === 'production'
  ? 'https://your-backend.railway.app'  // Your cloud backend URL
  : 'http://localhost:8000';            // Local development

export class ApiClient {
  constructor() {
    this.baseUrl = API_BASE_URL;
    this.token = null;
  }
  // ... rest of implementation
}
```

Or use environment variables:

```javascript
// frontend/electron/main.cjs

const API_URL = process.env.API_URL || 'https://your-backend.railway.app';

// Pass to renderer
mainWindow.webContents.send('config', { apiUrl: API_URL });
```

### 2. Build Electron App

```bash
cd frontend

# Install dependencies
npm install

# Build for your platform
npm run build

# Package for distribution
npm run package
```

### 3. Build for Multiple Platforms

#### macOS

```bash
# Build for macOS (requires macOS)
npm run package:mac

# Output: frontend/dist/Backend-Generator-1.0.0.dmg
```

#### Windows

```bash
# Build for Windows (can be done on any platform)
npm run package:win

# Output: frontend/dist/Backend-Generator-Setup-1.0.0.exe
```

#### Linux

```bash
# Build for Linux
npm run package:linux

# Output: frontend/dist/Backend-Generator-1.0.0.AppImage
```

#### Build All Platforms

```bash
# Build for all platforms (requires appropriate OS or CI)
npm run package:all
```

### 4. Code Signing (Production)

#### macOS

```bash
# Get Apple Developer certificate
# Add to Keychain

# Update electron-builder.yml
mac:
  identity: "Developer ID Application: Your Name (TEAM_ID)"
  hardenedRuntime: true
  gatekeeperAssess: false
  entitlements: "build/entitlements.mac.plist"
  entitlementsInherit: "build/entitlements.mac.plist"

# Build with signing
npm run package:mac
```

#### Windows

```bash
# Get code signing certificate (.pfx file)

# Update electron-builder.yml
win:
  certificateFile: "path/to/cert.pfx"
  certificatePassword: "password"

# Build with signing
npm run package:win
```

### 5. Auto-Update Configuration (Optional)

```javascript
// frontend/electron/main.cjs

const { autoUpdater } = require('electron-updater');

autoUpdater.setFeedURL({
  provider: 'github',
  owner: 'your-username',
  repo: 'your-repo'
});

autoUpdater.checkForUpdatesAndNotify();
```

---

## Part 3: Distribution

### Option A: Direct Download

1. Upload packaged apps to your website
2. Provide download links:
   - `Backend-Generator-1.0.0.dmg` (macOS)
   - `Backend-Generator-Setup-1.0.0.exe` (Windows)
   - `Backend-Generator-1.0.0.AppImage` (Linux)

### Option B: GitHub Releases

```bash
# Create release
gh release create v1.0.0 \
  frontend/dist/Backend-Generator-1.0.0.dmg \
  frontend/dist/Backend-Generator-Setup-1.0.0.exe \
  frontend/dist/Backend-Generator-1.0.0.AppImage \
  --title "Backend Generator v1.0.0" \
  --notes "Initial release"
```

### Option C: App Stores

#### Mac App Store

1. Create App Store Connect listing
2. Build with Mac App Store provisioning profile
3. Submit for review

#### Microsoft Store

1. Create Microsoft Partner Center listing
2. Package as MSIX
3. Submit for certification

---

## Part 4: Testing Deployment

### Test Backend API

```bash
# Health check
curl https://your-backend.railway.app/health

# Register user
curl -X POST https://your-backend.railway.app/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123!"}'

# Login
curl -X POST https://your-backend.railway.app/auth/login \
  -d "username=test@example.com&password=Test123!&grant_type=password"

# Generate project (with JWT token)
curl -X POST https://your-backend.railway.app/generate-from-prompt \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"A simple todo API"}'
```

### Test Electron App

1. Install packaged app on test machine
2. Launch app
3. Register/Login (should connect to cloud backend)
4. Generate a project
5. Deploy locally with Docker
6. Verify endpoints work

---

## Part 5: Monitoring & Maintenance

### Backend Monitoring

**Railway:**
- Built-in metrics dashboard
- Log streaming
- Automatic deployments from Git

**AWS:**
- CloudWatch for logs and metrics
- X-Ray for tracing
- CloudWatch Alarms for alerts

### Database Backups

**Railway:**
```bash
# Automated daily backups included
# Manual backup
railway run pg_dump > backup.sql
```

**AWS RDS:**
```bash
# Enable automated backups
aws rds modify-db-instance \
  --db-instance-identifier backend-db \
  --backup-retention-period 7 \
  --preferred-backup-window "03:00-04:00"
```

### Electron App Updates

Use `electron-updater` for automatic updates:

```javascript
// Check for updates on startup
app.on('ready', () => {
  autoUpdater.checkForUpdatesAndNotify();
});

// Download and install updates
autoUpdater.on('update-downloaded', () => {
  autoUpdater.quitAndInstall();
});
```

---

## Part 6: Environment-Specific Configuration

### Development

```env
# .env.development
API_URL=http://localhost:8000
NODE_ENV=development
```

### Staging

```env
# .env.staging
API_URL=https://staging-backend.railway.app
NODE_ENV=staging
```

### Production

```env
# .env.production
API_URL=https://backend.railway.app
NODE_ENV=production
```

---

## Deployment Checklist

### Backend Deployment

- [ ] Cloud provider account created
- [ ] PostgreSQL database provisioned
- [ ] Environment variables configured
- [ ] Database schema initialized
- [ ] Backend deployed and accessible
- [ ] Health check endpoint responding
- [ ] API endpoints tested
- [ ] CORS configured for Electron app
- [ ] SSL/TLS certificate configured
- [ ] Monitoring and logging enabled
- [ ] Backup strategy implemented

### Electron App Packaging

- [ ] API endpoint updated to cloud backend
- [ ] App built for target platforms
- [ ] Code signing configured (production)
- [ ] Auto-update configured (optional)
- [ ] App tested on clean machines
- [ ] Distribution method chosen
- [ ] Download links/releases published
- [ ] User documentation updated

---

## Troubleshooting

### Backend Issues

**Issue:** Database connection fails

**Solution:**
- Check `PLATFORM_DATABASE_URL` format
- Verify database is accessible from backend
- Check firewall rules

**Issue:** CORS errors in Electron app

**Solution:**
- Set `CORS_ORIGINS=*` in backend environment
- Or specify Electron app origin

### Electron App Issues

**Issue:** App can't connect to backend

**Solution:**
- Verify API_URL is correct
- Check network connectivity
- Verify backend is accessible

**Issue:** Docker not detected

**Solution:**
- Ensure Docker Desktop is installed
- Check Docker daemon is running
- Verify Docker socket permissions

---

## Cost Estimates

### Railway (Recommended for Start)

- **Hobby Plan:** $5/month
  - 500 hours of compute
  - PostgreSQL included
  - Perfect for MVP

- **Pro Plan:** $20/month
  - Unlimited compute
  - Better performance
  - Production-ready

### AWS (Production Scale)

- **ECS Fargate:** ~$15-30/month (2 tasks)
- **RDS PostgreSQL:** ~$15-25/month (db.t3.micro)
- **Load Balancer:** ~$16/month
- **Total:** ~$46-71/month

### Render

- **Starter:** $7/month (web service)
- **PostgreSQL:** $7/month
- **Total:** $14/month

---

## Next Steps

1. **Choose cloud provider** based on budget and requirements
2. **Deploy backend** following provider-specific guide
3. **Test backend API** with curl/Postman
4. **Update Electron app** with cloud backend URL
5. **Package Electron app** for your platform
6. **Test packaged app** on clean machine
7. **Distribute app** via chosen method
8. **Monitor and maintain** both components

---

## Related Documentation

- [Architecture Documentation](./architecture/cloud-electron.md)
- [Frontend Build Instructions](../frontend/BUILD.md)
- [Scripts Documentation](../scripts/README.md)
- [Main README](../README.md)

---

**Last Updated:** February 23, 2026  
**Status:** Production-Ready  
**Maintainer:** Development Team
