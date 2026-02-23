# Requirements Document: Marketing Website Separation

## Introduction

This specification defines the requirements for separating the marketing website from the Electron desktop application. The marketing website will be a standalone static site containing all informational content (landing, features, docs, research, about) without the generation functionality, which will remain exclusive to the downloadable Electron app.

## Glossary

- **Marketing_Website**: Static website with informational content and download links
- **Desktop_App**: Electron application with generation functionality and authentication
- **Generation_Component**: ChatPage and related generation UI (stays in Desktop_App)
- **Static_Content**: All pages that don't require authentication or generation (moves to Marketing_Website)
- **Download_Page**: New page on Marketing_Website for downloading Desktop_App installers

## Requirements

### Requirement 1: Marketing Website Structure

**User Story:** As a potential user, I want to visit a marketing website to learn about the product and download the desktop app, so that I can understand the value proposition before installing.

#### Acceptance Criteria

1. THE Marketing_Website SHALL be a separate React application in `frontend/website/` directory
2. THE Marketing_Website SHALL include all static pages from the current frontend (Landing, Features, Docs, API Reference, CLI Guide, About, Research)
3. THE Marketing_Website SHALL NOT include authentication functionality
4. THE Marketing_Website SHALL NOT include the ChatPage or generation components
5. THE Marketing_Website SHALL be deployable as a static site to Netlify, Vercel, or similar platforms

### Requirement 2: Download Page

**User Story:** As a potential user, I want to download the desktop app for my operating system, so that I can start generating backends locally.

#### Acceptance Criteria

1. THE Marketing_Website SHALL include a dedicated Download page
2. WHEN a user visits the Download page, THE System SHALL detect their operating system (macOS, Windows, Linux)
3. THE Download page SHALL display the appropriate installer download link for the detected OS
4. THE Download page SHALL show download links for all supported platforms (macOS, Windows, Linux)
5. THE Download page SHALL display system requirements (Docker Desktop, RAM, disk space)
6. THE Download page SHALL display file sizes for each installer
7. THE Download page SHALL include installation instructions for each platform

### Requirement 3: Desktop App Restructuring

**User Story:** As a developer, I want the desktop app to be clearly separated from the marketing website, so that each can be developed and deployed independently.

#### Acceptance Criteria

1. THE current `frontend/` directory SHALL be renamed to `frontend/desktop/`
2. THE Desktop_App SHALL retain only generation-related pages (ChatPage, ProjectsPage if exists)
3. THE Desktop_App SHALL retain authentication functionality (LoginModal, AuthContext)
4. THE Desktop_App SHALL retain Electron-specific services (docker-manager, verify-runner)
5. THE Desktop_App SHALL remove all static marketing pages (Landing, Features, Docs, etc.)

### Requirement 4: Shared Components

**User Story:** As a developer, I want to reuse common UI components between the marketing website and desktop app, so that I maintain consistent branding and reduce code duplication.

#### Acceptance Criteria

1. WHEN common components exist (Navbar, Footer, Logo, ThemeToggle), THE System SHALL extract them to a shared location
2. THE Marketing_Website SHALL use shared components for consistent branding
3. THE Desktop_App SHALL use shared components where applicable
4. THE shared components SHALL be accessible to both applications without duplication

### Requirement 5: Navigation and Routing

**User Story:** As a user visiting the marketing website, I want clear navigation to all informational pages and the download page, so that I can easily find what I need.

#### Acceptance Criteria

1. THE Marketing_Website SHALL include a navigation bar with links to all pages
2. THE Marketing_Website navigation SHALL include a prominent "Download" button
3. THE Marketing_Website SHALL use React Router for client-side routing
4. THE Marketing_Website SHALL include a 404 page for invalid routes
5. THE Marketing_Website SHALL redirect all routes to index.html for SPA functionality

### Requirement 6: Call-to-Action Updates

**User Story:** As a potential user browsing the marketing website, I want clear calls-to-action that direct me to download the app, so that I know how to get started.

#### Acceptance Criteria

1. WHEN the Marketing_Website displays a "Try Now" or "Get Started" button, THE System SHALL navigate to the Download page
2. THE Hero section SHALL include a primary "Download App" call-to-action
3. THE Features section SHALL include calls-to-action directing to the Download page
4. THE Marketing_Website SHALL NOT include "Login" or "Sign Up" buttons (authentication happens in Desktop_App)

### Requirement 7: Content Migration

**User Story:** As a developer, I want all existing content to be preserved during the separation, so that no information is lost.

#### Acceptance Criteria

1. THE Marketing_Website SHALL include all content from LandingPage (Hero, DemoSection, Features, Waitlist)
2. THE Marketing_Website SHALL include all content from DocsPage
3. THE Marketing_Website SHALL include all content from ApiReferencePage
4. THE Marketing_Website SHALL include all content from CliGuidePage
5. THE Marketing_Website SHALL include all content from AboutPage
6. THE Marketing_Website SHALL include all content from ResearchPage and ResearchPostPage
7. THE Marketing_Website SHALL preserve all styling and visual design

### Requirement 8: Build and Deployment Configuration

**User Story:** As a developer, I want the marketing website to have its own build configuration, so that it can be deployed independently of the desktop app.

#### Acceptance Criteria

1. THE Marketing_Website SHALL have its own package.json with dependencies
2. THE Marketing_Website SHALL have its own Vite configuration
3. THE Marketing_Website SHALL build to a `dist/` directory
4. THE Marketing_Website SHALL include a `_redirects` file for SPA routing on static hosts
5. THE Marketing_Website SHALL be optimized for production (minification, tree-shaking)

### Requirement 9: Desktop App Entry Point

**User Story:** As a user launching the desktop app, I want to immediately see the generation interface or login screen, so that I can start working without navigating through marketing content.

#### Acceptance Criteria

1. WHEN the Desktop_App launches, THE System SHALL display the login screen if not authenticated
2. WHEN the Desktop_App launches and user is authenticated, THE System SHALL display the ChatPage (generation interface)
3. THE Desktop_App SHALL NOT display marketing pages (Landing, Features, etc.)
4. THE Desktop_App SHALL have minimal navigation focused on generation workflow

### Requirement 10: Documentation Consistency

**User Story:** As a developer, I want updated documentation that reflects the new structure, so that I can understand how to work with both applications.

#### Acceptance Criteria

1. THE project README SHALL document the new frontend structure (website/ and desktop/)
2. THE Marketing_Website SHALL have its own README with build and deployment instructions
3. THE Desktop_App SHALL have its own README with build and packaging instructions
4. THE documentation SHALL explain the relationship between Marketing_Website and Desktop_App
5. THE documentation SHALL include deployment guides for both applications

### Requirement 11: Asset Management

**User Story:** As a developer, I want assets (images, icons, fonts) to be properly organized, so that both applications can access what they need.

#### Acceptance Criteria

1. WHEN assets are shared between applications, THE System SHALL place them in a shared location or duplicate them
2. THE Marketing_Website SHALL include all necessary assets for its pages
3. THE Desktop_App SHALL include all necessary assets for its pages
4. THE asset organization SHALL be documented in each application's README

### Requirement 12: Environment Configuration

**User Story:** As a developer, I want clear environment configuration for each application, so that I can configure API endpoints and other settings appropriately.

#### Acceptance Criteria

1. THE Marketing_Website SHALL NOT require API endpoint configuration (no backend communication)
2. THE Desktop_App SHALL maintain its API endpoint configuration for cloud backend communication
3. THE environment configuration SHALL be documented for each application
4. THE Marketing_Website SHALL have minimal environment variables (if any)
