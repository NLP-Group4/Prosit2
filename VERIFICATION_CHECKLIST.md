# Electron App Verification Checklist

Use this checklist to verify the project generation flow in the Electron app.

## Credentials
- **Email:** testuser@mail.com
- **Password:** haxqy6-byqcyn-waCcun

## Prerequisites
1. **Backend running:** `cd backend && uvicorn app.main:app --reload --port 8000`
2. **Docker Desktop running** (required for local deployment verification)
3. **Electron app:** `cd frontend/desktop && npm run electron:dev`

---

## Verification Steps

### 1. Login
- [ ] Open the Electron app
- [ ] Login modal appears (or click to open if already closed)
- [ ] Enter credentials and sign in
- [ ] Chat interface loads with empty state / "Let's build something"

### 2. Project Generation
- [ ] Type a prompt (e.g. "A minimal todo API with tasks and done flag")
- [ ] Click send or press Enter
- [ ] Observe phase progress: Requirement analysis → Architecture → Code generation → Containerizing → Verification
- [ ] Generation completes with "Project generated successfully" message
- [ ] Download ZIP button appears
- [ ] Project appears in the **Projects** sidebar
- [ ] Project expands to show thread "Initial build – [project-name]"

### 3. Projects & Threads Rendering
- [ ] Sidebar shows project with correct title
- [ ] Click project header to expand/collapse
- [ ] Thread "Initial build – [project-name]" is visible under the project
- [ ] Clicking the thread loads the project details (spec, files, endpoints)
- [ ] Messages and completion state display correctly

### 4. Return to Generated Project
- [ ] Click "New thread" to clear the current view
- [ ] Expand a previous project in the sidebar
- [ ] Click its thread
- [ ] Project details load correctly (no undefined/blank)
- [ ] Download button and file preview work
- [ ] "Test API Endpoints" and "View Local API Documentation" buttons visible

### 5. Docker & Local API
- [ ] After generation in Electron, "View Local API Documentation" links to http://localhost:8001/docs
- [ ] Open that link — Swagger UI loads for the generated backend
- [ ] Health endpoint: `GET http://localhost:8001/health` returns `{"status":"ok"}`
- [ ] Generated API endpoints are accessible (e.g. `/docs`, entity CRUD)

### 6. New Thread in Project
- [ ] Expand a project
- [ ] Click "+ New thread" under the project
- [ ] New thread is created ("Conversation N")
- [ ] Switching between threads works without errors

---

## Bug Fixes Applied

1. **loadProjectDetails(activeThread) → loadProjectDetails(activeProject)**  
   Previously, loading project details when viewing a thread passed the thread ID instead of the project ID, causing undefined data. Fixed so project details load correctly when returning to a project.

2. **Electron handler now passes `thread_id`**  
   The generate-and-verify IPC handler now includes `thread_id` in its return value so the UI can correctly set the active thread and display it in the sidebar.

---

## API Quick Test (curl)

```bash
# Login
TOKEN=$(curl -s -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser@mail.com&password=haxqy6-byqcyn-waCcun" | jq -r '.access_token')

# List projects
curl -s "http://localhost:8000/projects" -H "Authorization: Bearer $TOKEN" | jq

# Project detail
curl -s "http://localhost:8000/projects/<PROJECT_ID>" -H "Authorization: Bearer $TOKEN" | jq

# Project threads
curl -s "http://localhost:8000/projects/<PROJECT_ID>/threads" -H "Authorization: Bearer $TOKEN" | jq

# Generated API health (after Electron deployment)
curl -s http://localhost:8001/health
```
