# Interius Marketing Website

Static marketing website for Interius API Builder, built with React, Vite, and React Router.

## Overview

This is the public-facing marketing website that provides information about Interius API Builder, including features, documentation, and download links for the desktop application.

## Structure

```
frontend/website/
├── src/
│   ├── pages/          # Page components
│   ├── components/     # Reusable UI components
│   ├── assets/         # Images, icons, etc.
│   ├── App.jsx         # Main app component with routing
│   ├── main.jsx        # Entry point
│   ├── App.css         # App styles
│   └── index.css       # Global styles
├── public/             # Static assets
├── index.html          # HTML template
├── vite.config.js      # Vite configuration
└── package.json        # Dependencies and scripts
```

## Development

### Prerequisites

- Node.js 18+ and npm

### Install Dependencies

```bash
npm install
```

### Run Development Server

```bash
npm run dev
```

The site will be available at `http://localhost:3000`

### Build for Production

```bash
npm run build
```

The built files will be in the `dist/` directory.

### Preview Production Build

```bash
npm run preview
```

## Deployment

This static site can be deployed to:
- Netlify
- Vercel
- GitHub Pages
- Any static hosting service

### Build Configuration

- **Build Command**: `npm run build`
- **Output Directory**: `dist`
- **Node Version**: 18+

### SPA Routing

For proper client-side routing, ensure your hosting platform redirects all routes to `index.html`. A `_redirects` file is included in the `public/` directory for Netlify.

## Features

- React 18 with modern hooks
- React Router for client-side routing
- Vite for fast development and optimized builds
- Theme toggle (light/dark mode)
- Responsive design
- SEO-friendly

## No Authentication Required

This marketing website does not include authentication or backend API calls. It is purely informational and directs users to download the desktop application for generation features.
