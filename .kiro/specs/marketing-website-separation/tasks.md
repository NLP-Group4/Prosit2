# Implementation Plan: Marketing Website Separation

## Overview

This plan outlines the tasks to separate the marketing website from the Electron desktop application, creating two independent applications with clear boundaries and responsibilities.

## Tasks

- [x] 1. Create Marketing Website Structure
  - Create `frontend/website/` directory
  - Set up package.json with React, Vite, React Router dependencies
  - Create Vite configuration for static site build
  - Set up basic directory structure (src/pages, src/components, src/assets, public)
  - _Requirements: 1.1, 8.1, 8.2_

- [x] 2. Set up Marketing Website Routing
  - [x] 2.1 Create App.jsx with React Router configuration
    - Set up BrowserRouter
    - Define routes for all marketing pages
    - Add 404 redirect to home
    - Implement theme management
    - _Requirements: 5.1, 5.3, 5.4_

  - [x] 2.2 Create main.jsx entry point
    - Set up React root
    - Import and render App component
    - _Requirements: 1.1_

  - [x] 2.3 Create _redirects file for SPA routing
    - Add `/*    /index.html   200` rule
    - Place in public/ directory
    - _Requirements: 5.5, 8.4_

- [x] 3. Migrate Shared Components
  - [x] 3.1 Copy Navbar component
    - Copy Navbar.jsx and Navbar.css
    - Remove login/signup buttons
    - Add Download button to navigation
    - Update links for marketing pages only
    - _Requirements: 4.1, 4.2, 6.4_

  - [x] 3.2 Copy Footer component
    - Copy Footer.jsx and Footer.css
    - Verify all links are appropriate for marketing site
    - _Requirements: 4.1, 4.2_

  - [x] 3.3 Copy utility components
    - Copy InteriusLogo.jsx
    - Copy ThemeToggle.jsx and ThemeToggle.css
    - Copy ScrollToTop.jsx
    - _Requirements: 4.1, 4.2, 4.3_

- [x] 4. Migrate Landing Page Components
  - [x] 4.1 Copy Hero component
    - Copy Hero.jsx and Hero.css
    - Update CTA buttons to navigate to /download instead of triggering login
    - _Requirements: 6.1, 6.2, 7.1_

  - [x] 4.2 Copy Features component
    - Copy Features.jsx and Features.css
    - Update CTA buttons to navigate to /download
    - _Requirements: 6.3, 7.1_

  - [x] 4.3 Copy DemoSection component
    - Copy DemoSection.jsx and DemoSection.css
    - Update any CTAs to navigate to /download
    - _Requirements: 7.1_

  - [x] 4.4 Copy Waitlist components
    - Copy Waitlist.jsx and Waitlist.css
    - Copy WaitlistModal.jsx and WaitlistModal.css
    - Update CTAs appropriately
    - _Requirements: 7.1_

  - [x] 4.5 Create LandingPage
    - Copy LandingPage.jsx
    - Remove authentication props
    - Update all CTAs to use navigate('/download')
    - Compose all landing components
    - _Requirements: 1.2, 6.1, 6.2, 6.3, 7.1_

- [x] 5. Create Download Page
  - [x] 5.1 Implement OS detection logic
    - Detect macOS (Intel vs Apple Silicon)
    - Detect Windows
    - Detect Linux
    - Handle unknown platforms
    - _Requirements: 2.2_

  - [x] 5.2 Create download configuration
    - Define download URLs for each platform
    - Define file sizes
    - Define system requirements
    - Define installation instructions
    - _Requirements: 2.4, 2.5, 2.6_

  - [x] 5.3 Build DownloadPage component
    - Create page layout with Navbar and Footer
    - Display detected OS as primary download
    - Show all platform options
    - Display system requirements
    - Display installation instructions
    - Add Docker Desktop notice
    - _Requirements: 2.1, 2.3, 2.4, 2.5, 2.6, 2.7_

  - [x] 5.4 Style Download Page
    - Create DownloadPage.css
    - Implement responsive design
    - Style download buttons prominently
    - Style platform cards
    - _Requirements: 2.1_

- [x] 6. Migrate Documentation Pages
  - [x] 6.1 Copy DocsPage
    - Copy DocsPage.jsx
    - Remove onOpenLogin prop
    - Verify all content is preserved
    - _Requirements: 1.2, 7.2_

  - [x] 6.2 Copy ApiReferencePage
    - Copy ApiReferencePage.jsx
    - Remove onOpenLogin prop
    - Verify all content is preserved
    - _Requirements: 1.2, 7.3_

  - [x] 6.3 Copy CliGuidePage
    - Copy CliGuidePage.jsx
    - Remove onOpenLogin prop
    - Verify all content is preserved
    - _Requirements: 1.2, 7.4_

- [x] 7. Migrate About and Research Pages
  - [x] 7.1 Copy AboutPage
    - Copy AboutPage.jsx
    - Remove onOpenLogin prop
    - Verify all content is preserved
    - _Requirements: 1.2, 7.5_

  - [x] 7.2 Copy ResearchPage
    - Copy ResearchPage.jsx
    - Remove onOpenLogin prop
    - Verify all content is preserved
    - _Requirements: 1.2, 7.6_

  - [x] 7.3 Copy ResearchPostPage
    - Copy ResearchPostPage.jsx
    - Remove onOpenLogin prop
    - Verify all content is preserved
    - _Requirements: 1.2, 7.6_

- [x] 8. Copy Assets and Styles
  - [x] 8.1 Copy global styles
    - Copy index.css
    - Copy App.css
    - Verify theme variables are included
    - _Requirements: 7.7, 11.2_

  - [x] 8.2 Copy assets
    - Copy all images from public/ and src/assets/
    - Copy icons and logos
    - Verify all assets are accessible
    - _Requirements: 11.1, 11.2, 11.4_

- [x] 9. Configure Marketing Website Build
  - [x] 9.1 Create Vite configuration
    - Configure build output directory
    - Configure base URL for deployment
    - Optimize for production
    - _Requirements: 8.2, 8.3, 8.5_

  - [x] 9.2 Add build scripts to package.json
    - Add `dev` script for development server
    - Add `build` script for production build
    - Add `preview` script for build preview
    - _Requirements: 8.1, 8.2_

  - [x] 9.3 Create README for Marketing Website
    - Document purpose and scope
    - Document build commands
    - Document deployment process
    - Document environment variables (if any)
    - _Requirements: 10.2, 10.4, 12.4_

- [x] 10. Checkpoint - Test Marketing Website Build
  - Build Marketing Website: `cd frontend/website && npm install && npm run build`
  - Verify build completes without errors
  - Verify all pages are accessible in preview
  - Verify all assets load correctly
  - Verify theme toggle works
  - Verify navigation works
  - _Requirements: 1.5, 8.3, 8.5_

- [x] 11. Restructure Desktop App
  - [x] 11.1 Rename frontend directory
    - Rename `frontend/` to `frontend/desktop/`
    - Update any absolute path references
    - _Requirements: 3.1_

  - [x] 11.2 Remove marketing pages from Desktop App
    - Delete LandingPage.jsx
    - Delete DocsPage.jsx
    - Delete ApiReferencePage.jsx
    - Delete CliGuidePage.jsx
    - Delete AboutPage.jsx
    - Delete ResearchPage.jsx
    - Delete ResearchPostPage.jsx
    - _Requirements: 3.2, 9.3_

  - [x] 11.3 Remove marketing components from Desktop App
    - Delete Hero.jsx and Hero.css
    - Delete Features.jsx and Features.css
    - Delete DemoSection.jsx and DemoSection.css
    - Delete Waitlist.jsx and Waitlist.css
    - Delete WaitlistModal.jsx and WaitlistModal.css
    - Keep: LoginModal, Navbar (simplified), InteriusLogo, ThemeToggle
    - _Requirements: 3.2_

  - [x] 11.4 Simplify Desktop App.jsx
    - Remove React Router (single page app)
    - Show LoginModal if not authenticated
    - Show ChatPage if authenticated
    - Remove marketing page routes
    - _Requirements: 3.2, 9.1, 9.2, 9.3_

  - [x] 11.5 Update Desktop Navbar
    - Simplify navigation (no marketing pages)
    - Keep theme toggle
    - Add logout functionality
    - Keep logo
    - _Requirements: 9.4_

  - [x] 11.6 Retain Electron services
    - Verify docker-manager.cjs is present
    - Verify verify-runner.cjs is present
    - Verify electron/main.cjs is present
    - Verify electron/preload.cjs is present
    - _Requirements: 3.4_

  - [x] 11.7 Retain authentication
    - Verify AuthContext.jsx is present
    - Verify LoginModal.jsx is present
    - Verify authentication flow works
    - _Requirements: 3.3_

- [x] 12. Update Desktop App Configuration
  - [x] 12.1 Update package.json paths
    - Verify all scripts reference correct paths
    - Verify electron main points to correct file
    - _Requirements: 3.1_

  - [x] 12.2 Update Vite configuration
    - Verify proxy configuration for API
    - Verify build configuration
    - _Requirements: 12.2_

  - [x] 12.3 Update electron-builder.yml
    - Verify file paths are correct
    - Verify build configuration
    - _Requirements: 3.1_

  - [x] 12.4 Create/Update Desktop README
    - Document purpose (generation app)
    - Document build and packaging commands
    - Document Electron-specific features
    - Document API endpoint configuration
    - _Requirements: 10.3, 10.4, 12.2, 12.3_

- [x] 13. Checkpoint - Test Desktop App Build
  - Build Desktop App: `cd frontend/desktop && npm install && npm run build`
  - Verify build completes without errors
  - Test Electron app: `npm run electron:dev`
  - Verify login modal appears
  - Verify authentication works
  - Verify ChatPage loads after login
  - Verify no marketing pages are accessible
  - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [x] 14. Update Root Documentation
  - [x] 14.1 Update root README.md
    - Document new frontend structure (website/ and desktop/)
    - Update quick start instructions
    - Add links to website and desktop READMEs
    - Update project structure diagram
    - _Requirements: 10.1, 10.4_

  - [x] 14.2 Update MONOREPO_COMPLETE.md
    - Update structure diagram to show website/ and desktop/
    - Document the separation
    - _Requirements: 10.1_

  - [x] 14.3 Update SEPARATION_GUIDE.md
    - Document Marketing Website deployment
    - Document Desktop App packaging
    - Update architecture diagrams
    - _Requirements: 10.4, 10.5_

- [ ] 15. Test Marketing Website Deployment
  - [ ] 15.1 Deploy to Netlify or Vercel
    - Connect repository
    - Configure build settings (build command, output directory)
    - Deploy
    - _Requirements: 1.5_

  - [ ] 15.2 Verify deployed site
    - Test all pages load
    - Test navigation works
    - Test download links (can be placeholder URLs initially)
    - Test theme toggle persists
    - Test on mobile devices
    - _Requirements: 1.5, 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 16. Test Desktop App Packaging
  - [ ] 16.1 Package for current platform
    - Run `npm run electron:build`
    - Verify installer is created
    - Install and test the packaged app
    - _Requirements: 3.1_

  - [ ] 16.2 Test packaged app functionality
    - Launch installed app
    - Verify login works
    - Verify generation works (if backend is available)
    - Verify Docker integration works
    - _Requirements: 9.1, 9.2_

- [ ] 17. Final Validation
  - [ ] 17.1 Verify Marketing Website independence
    - Confirm no authentication code present
    - Confirm no API calls to backend
    - Confirm no Electron-specific code
    - _Requirements: 1.3, 1.4_

  - [ ] 17.2 Verify Desktop App independence
    - Confirm no marketing pages present
    - Confirm authentication is required
    - Confirm Electron services work
    - _Requirements: 3.2, 3.3, 3.4_

  - [ ] 17.3 Cross-browser testing (Marketing Website)
    - Test on Chrome
    - Test on Firefox
    - Test on Safari
    - Test on Edge
    - _Requirements: 1.5_

  - [ ] 17.4 Cross-platform testing (Desktop App)
    - Test on macOS (if available)
    - Test on Windows (if available)
    - Test on Linux (if available)
    - _Requirements: 3.1_

- [ ] 18. Update Download Links
  - [ ] 18.1 Build Desktop App for all platforms
    - Run `npm run electron:build:all`
    - Verify all installers are created
    - _Requirements: 2.4_

  - [ ] 18.2 Upload to GitHub Releases
    - Create new release (e.g., v1.0.0)
    - Upload .dmg, .exe, .AppImage files
    - Write release notes
    - _Requirements: 2.4_

  - [ ] 18.3 Update Download Page URLs
    - Update download URLs in DownloadPage.jsx
    - Point to GitHub Releases or direct download URLs
    - Verify file sizes are accurate
    - _Requirements: 2.3, 2.4, 2.6_

  - [ ] 18.4 Test download links
    - Click each download link
    - Verify files download correctly
    - Verify file sizes match
    - _Requirements: 2.3, 2.4_

- [ ] 19. Final Documentation Review
  - Review all README files for accuracy
  - Verify all documentation reflects new structure
  - Verify deployment guides are complete
  - Verify all links work
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

## Notes

- Tasks marked with sub-tasks should be completed in order
- Checkpoints (tasks 10, 13) are critical validation points - do not proceed if issues are found
- The Marketing Website can be developed and deployed independently of Desktop App changes
- Desktop App restructuring should be done carefully to avoid breaking Electron functionality
- Test thoroughly on each platform before releasing installers
- Download links can initially point to placeholder URLs and be updated once installers are built

## Success Criteria

- Marketing Website builds and deploys successfully as a static site
- Marketing Website contains no authentication or generation code
- Desktop App packages successfully for all platforms
- Desktop App requires authentication and shows generation interface
- Both applications can be developed and deployed independently
- All documentation is updated and accurate
- Download links work and installers install correctly
