# Chat System Behavior (Current State)

This document describes how the Interius chat system currently behaves across the frontend, backend pipeline, persistence, and deployment layers.

## Scope

This covers the current behavior in:

- `frontend/src/pages/ChatPage.jsx` — Chat UI, pipeline rendering, Schema Visualizer, API Tester, Sandbox deploy
- `frontend/src/pages/ChatPage.css` — Styling including Schema Visualizer styles
- `frontend/src/lib/interface.js` — Interface agent client
- `frontend/src/lib/threadFileContext.js` — Session-local file context cache
- `backend/app/agent/interface.py` — Intent routing agent
- `backend/app/agent/orchestrator.py` — Multi-agent pipeline orchestrator
- `backend/app/agent/llm_client.py` — Provider-agnostic LLM client (OpenRouter compatible)
- `backend/app/api/routes/generate.py` — SSE streaming endpoints
- `backend/app/api/routes/sandbox.py` — Sandbox deployment endpoints
- `backend/app/crud.py` — Database operations with transaction safety
- Supabase tables `threads`, `messages`, `message_attachments`, `message_artifacts`

## High-Level Architecture

The chat has two runtime lanes:

1. **Interface / conversation lane** (fast intent routing and QA)
2. **Build / generation lane** (full orchestrator pipeline)

### Interface lane

The frontend sends each user prompt to:

- `POST /api/v1/generate/interface`

The backend `InterfaceAgent` (configured via `MODEL_INTERFACE`) decides whether the prompt should:

- be answered directly in chat (`should_trigger_pipeline=false`)
- trigger the generation pipeline (`should_trigger_pipeline=true`)

### Build lane (LIVE orchestrator)

When `should_trigger_pipeline=true`, the frontend:

1. Shows the interface acknowledgment message (assistant reply)
2. Opens an SSE connection to `POST /api/v1/generate/thread/{threadId}/chat`
3. Renders real-time pipeline progress across all 7 stages
4. Displays generated artifacts (Requirements doc, ER schema, Architecture design, Mermaid diagram, Code files, Test suites)
5. Offers **Test API Endpoints** and **Open Sandbox** actions on completion

The pipeline is **fully live** — the orchestrator runs the real multi-agent pipeline using the configured OpenRouter models.

## LLM Provider Configuration

The backend is provider-agnostic via an OpenAI-compatible client. Interius uses OpenRouter by default (`LLM_BASE_URL="https://openrouter.ai/api/v1"`) configuring specific models per agent in `config.py`:

| Agent Configuration | Default Model | Purpose |
|---------------------|---------------|---------|
| `MODEL_INTERFACE` | `deepseek/deepseek-r1-0528:free` | Fast intent routing and grounded QA |
| `MODEL_DEFAULT` | `deepseek/deepseek-r1-0528:free` | Requirements, Architecture, Test Generation |
| `MODEL_IMPLEMENTER` | `arcee-ai/trinity-large-preview:free` | Heavy coding and patching |
| `MODEL_REVIEWER` | `arcee-ai/trinity-large-preview:free` | Security review and patch requests |

The LLM client uses a **120s timeout** and **3 max retries** to handle large structured generation calls, especially for architecture and implementer stages. It also strips reasoning tags (e.g., `<think>`) before parsing JSON.

## Message Types and Rendering

Persisted chat message roles:

- `user` — human prompts
- `assistant` — interface agent conversational reply / routing acknowledgment
- `agent` — pipeline result message (rendered as the build card)

### Rendering behavior

- `assistant` messages render as normal assistant chat bubbles
- `agent` messages render as the richer generation/pipeline card with progress stages
- If an `assistant` acknowledgment is immediately followed by an `agent` pipeline result, the UI groups them visually

## Thread Behavior

### Thread ↔ Backend Project Mapping

Frontend threads (Supabase) map to backend Projects via a marker:

```
Project.description = "[chat-thread:{supabase_thread_id}]"
```

This is handled by `_resolve_or_create_project_for_thread()` in `generate.py`. The first build in a thread creates a new Project; subsequent builds in the same thread reuse it.

### Thread creation

- A new thread is created when the user sends a message with no active thread
- Initial title is generated from the first prompt

### Thread rename (automatic on first build request)

If a thread starts with small talk and later receives its first build-triggering prompt, the thread title is auto-renamed from that build request (once per thread).

## Interface Agent Behavior

Backend file: `backend/app/agent/interface.py`

### Role

The interface agent acts as:

- Conversational assistant (for non-build prompts)
- Intent router (for build prompts)
- Thread code Q&A handler (for questions about previously generated code)

### Output shape

Returns an `InterfaceDecision` with:

- `intent` — classified intent type (`pipeline_request`, `context_question`, `social`, `clarification`)
- `should_trigger_pipeline` — boolean
- `assistant_reply` — conversational text
- `pipeline_prompt` — refined prompt for the orchestrator
- `action_type` — `chat | build_new | continue_from_architecture | artifact_retrieval`
- `execution_plan` — optional list of pipeline steps to resume/skip

### Thread Code Q&A

When the interface detects a question about previously generated code (and `should_trigger_pipeline=false`), it:

1. Queries ChromaDB for relevant generated code snippets from the thread
2. Feeds them to the LLM with a grounded Q&A prompt
3. Returns an answer citing specific files and line numbers

## Pipeline Stages and Artifacts

### 1. Requirements Stage
- Produces: `ProjectCharter` (entities, endpoints, business rules, auth)
- Frontend receives: Requirements Markdown preview + **Schema Visualizer ER diagram JSON**

### 2. Architecture Stage
- Produces: `SystemArchitecture` (design document, Mermaid diagram, components, data model, endpoints)
- Frontend receives: Architecture Design Markdown + interactive Mermaid diagram

### 3. Implementer Stage
- Produces: `GeneratedCode` (plan-then-generate pattern)
- Frontend receives: File list with code preview panel

### 4. Test Runner Stage (Deterministic)
- Produces: `TestReport`
- Runs syntax compilation and import smoke tests. Generates auto-patch requests for the implementer upon failure.
- Frontend receives: Check results (pass/fail)

### 5. Test Generator Stage (LLM)
- Produces: `GeneratedTests`
- Generates a custom `pytest` suite for the architecture. Output is non-blocking.
- Frontend receives: Test file list

### 6. Reviewer Stage
- Produces: `ReviewReport` (issues, suggestions, security score, patch requests)
- **Review Loop:** Up to 5 fix-and-re-review passes. Code is approved only if `approved == True` AND `security_score >= 7`.
- Frontend receives: Review score badge, revision notifications

### 7. Sandbox Deploy Stage
- Produces: `SandboxTestReport`
- **Deploy Loop:** Up to 3 deploy-and-test retries. Extracts Python tracebacks and auto-patches failing files via the orchestrator.
- Frontend receives: Test pass/fail counts, status indicators

## Schema Visualizer & API Tester

### Schema Visualizer
The Schema Visualizer is an interactive SVG component rendered in `ChatPage.jsx` that displays ER diagrams generated from the requirements artifact.
1. `_build_schema_visualizer_artifact()` in `generate.py` parses `ProjectCharter.entities`
2. Generates a JSON schema rendered by the `SchemaVisualizer` component with PK/FK/nullable badges and hover states.

### Dynamic API Tester
The frontend extracts `endpoints` from the `ProjectCharter` artifact to dynamically render interactive mock endpoints in the right-side API Tester panel.

## Sandbox Deployment

1. The orchestrator fetches the final code and generated tests.
2. Writes files to the shared Docker volume `/sandbox/{project_id}/`.
3. Auto-patches common LLM code-generation mistakes via `_auto_patch_content()`.
4. Writes a `requirements.txt` and `start.sh` launcher script.
5. The sandbox container runs `start.sh` natively — installing dependencies, running `uvicorn`, waiting for a Python `urllib` health check, and executing `pytest`.
6. Results read via the output `pytest.log`.

## Chat Persistence

### Supabase (long-term frontend persistence)

- `threads` — thread metadata
- `messages` — chat messages (user/assistant/agent)
- `message_attachments` — file metadata (not raw content)
- `message_artifacts` — generated artifact JSON (requirements, architecture, code file map)

### Backend PostgreSQL (pipeline data)

- `Project` → `GenerationRun` → `ArtifactRecord` chain
- **Artifact Store:** Large code bundles are stored on-disk in `backend/artifact_store/` and referenced via `bundle_ref`.

### Browser storage

- `localStorage`: `interius_active_thread`
- `sessionStorage`: memory context caches

## Transaction Safety

All CRUD mutations in `crud.py` are wrapped in try/except with `session.rollback()` to prevent idle transaction blocks on PostgreSQL database errors.

## Quick Manual Test Checklist

### Conversation routing
1. Send `hello` → expect direct assistant reply (no pipeline)
2. Ask for previously attached file → expect context retrieval

### Build routing
1. Send a build prompt → expect acknowledgment + 7-stage pipeline trigger
2. Verify ER diagram schema renders after Requirements stage
3. Verify test generation and review score badge appear
4. Verify dynamic API tester updates with custom routes

### Sandbox deployment
1. After build completes, observe auto-deploy status in chat.
2. Click "Open Sandbox" to view Swagger UI at `http://localhost:9000/docs`.

### Thread Code Q&A
1. Generate code in a thread
2. Ask "how does the auth endpoint work?" → expect grounded answer with source code citations
