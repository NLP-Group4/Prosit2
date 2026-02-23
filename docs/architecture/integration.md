# Cloud + Electron Integration Specification

> **Status**: Proposed · **Last Updated**: 2026-02-23

This document specifies the integration contracts and interaction flows between the Cloud API (FastAPI) and the Electron Desktop App. It adheres strictly to the boundaries defined in `architecture-cloud-electron.md`.

## 1. Core Principles

- **Cloud is Sovereign**: All LLM interactions, user accounts, generated code, and API keys are strictly managed by the Cloud API.
- **Electron is the Executor**: The local desktop app handles computing the verification via Docker. It performs no AI logic.
- **Stateless Verification**: The verification reports are transient, used only to trigger auto-fix agent loops.
- **JWT Authorization**: All secured APIs require Bearer token authorization using JWTs.

---

## 2. API Contracts: Cloud Integration Endpoints

This section describes the specific application interfaces the Electron app will consume.

### 2.1 Project Verification Reporting (`POST /projects/{id}/verify-report`)

Called by the Electron App after running local HTTP smoke tests against the generated backend container.

**Endpoint**: `POST /api/v1/projects/{id}/verify-report`
**Auth**: Bearer Token
**Request Body (`VerificationReport`):**

```json
{
  "project_id": "uuid",
  "passed": false,
  "elapsed_ms": 1450,
  "results": [
    {
      "test_name": "Health Check GET /health",
      "endpoint": "/health",
      "method": "GET",
      "passed": true,
      "status_code": 200,
      "error_message": null
    },
    {
      "test_name": "CRUD Create User",
      "endpoint": "/users",
      "method": "POST",
      "passed": false,
      "status_code": 422,
      "error_message": "Unprocessable Entity: Missing required field 'email'"
    }
  ]
}
```

**Response (`200 OK`):**

```json
{
  "status": "recorded",
  "action_required": "fix",
  "message": "Failing tests detected. Proceed to trigger auto-fix."
}
```

### 2.2 Trigger Auto-Fix (`POST /projects/{id}/fix`)

Triggered by Electron when tests fail (maximum of 3 attempts).

**Endpoint**: `POST /api/v1/projects/{id}/fix`
**Auth**: Bearer Token
**Request Body:**

```json
{
  "report_id": "uuid",
  "attempt_number": 1,
  "failed_tests": [
    {
      "method": "POST",
      "endpoint": "/users",
      "error_message": "Unprocessable Entity: Missing required field 'email'"
    }
  ]
}
```

**Response (`202 Accepted`):**

```json
{
  "job_id": "uuid",
  "status": "fixing",
  "estimated_completion_seconds": 15
}
```

*(Electron should poll `/projects/{id}` for status `ready` and then download the new ZIP)*

---

## 3. Electron Architecture: Local Verification Flow

### 3.1 Docker Manager Lifecycle

The Electron app's `docker-manager.js` orchestrates project deployment:

1. **Unzip Target**: Unpack downloaded ZIP to OS temp directory `/tmp/apigenerator/{project_uuid}/`.
2. **Find Ports**: Allocate a random open port on `localhost` (e.g., `8005`) to prevent collisions if multiple projects run.
3. **Inject Environment**: Create a local `.env` exposing the mapped port.
4. **Deploy**: Spawn `docker compose up --build -d`.
5. **Poll Health**: Poll `GET http://localhost:{port}/health` every 1s (timeout 30s) until `200 OK` is returned.

### 3.2 Verification Runner (`verify-runner.js`)

Equivalent to the previous Python `deploy_verify.py`. Uses pure Javascript `fetch()`.

1. Disables CORS in the local fetch instance if necessary.
2. Uses the AST/Spec payload retrieved from `GET /projects/{id}` to know which endpoints to fuzz.
3. Accumulates results and formats the payload for `POST /projects/{id}/verify-report`.

---

## 4. WebSockets / Polling strategy

For MVP, to avoid complex bidirectional WebSockets:

- When a `POST /projects/{id}/fix` or `POST /generate-from-prompt` is triggered, the Cloud returns a `job_id`.
- Electron polls `GET /projects/{id}/status` every 2 seconds until status changes from `generating` or `fixing` to `ready` or `failed`.
- Max polling timeout: 120 seconds.

---

## 5. Security and Clean-up

- **Data Retention**: The Electron app MUST delete the temp directory and stop all associated Docker containers (`docker compose down -v`) when the native window is closed or the run is aborted.
- **Port Masking**: The database port mapped in `docker-compose.yml` must solely bind to the Docker network (`expose: 5432`) and should not be mapped to the host (`ports: ["5432:5432"]`) to prevent local port conflicts and reduce the attack surface.
- **Secret Management**: JWT token is stored using Electron's `safeStorage`. The token is appended to the `Authorization: Bearer <token>` header for all Cloud API requests via `api-client.js`.