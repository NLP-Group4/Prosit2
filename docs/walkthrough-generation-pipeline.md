# CraftLive — Code Walkthrough: Generation Pipeline

A detailed trace of what happens from the moment a user types a prompt to when they receive a fully reviewed, tested, and deployed API — referencing exact files, functions, and line numbers.

---

## 1. User Sends a Prompt (Frontend → Backend)

**File:** `frontend/src/pages/ChatPage.jsx`

When the user types a prompt (e.g., *"Build me a bookstore API"*) and presses Send:

1. The message is persisted to **Supabase** (`threads` / `messages` tables) for chat history.
2. The frontend issues a `POST` request to the backend SSE endpoint:
   ```
   POST /api/v1/generate/thread/{threadId}/chat
   ```
   The payload (`ChatGenerateStreamRequest`) includes the raw `prompt`, recent `thread_context` messages, and optional `attachment_summaries`.

3. The frontend opens an **EventSource** to consume the Server-Sent Events (SSE) stream and updates the UI in real time as each event arrives.

---

## 2. Thread Resolution (Backend API Route)

**File:** `backend/app/api/routes/generate.py` → `generate_pipeline_for_chat_thread()`

The backend receives the thread ID from the frontend. Since Supabase threads and PostgreSQL projects are separate databases, the backend must link them:

1. `_get_or_create_chat_bridge_user(session)` ensures a system-level user exists for chat-originated pipelines.
2. `_resolve_or_create_project_for_thread(session, current_user, thread_id, prompt)` searches PostgreSQL for a `Project` where `description` contains the marker `[chat-thread:{thread_id}]`.
   - **If found:** reuses the existing project (so multiple generations in the same thread share one project).
   - **If not found:** creates a new `Project` with the marker embedded in the description.
3. A `GenerationRun` record (status: `pending`) is created in the database to track this pipeline execution.

The function then returns an `EventSourceResponse` wrapping the generator function that orchestrates the entire pipeline.

---

## 3. Intent Classification (Interface Agent)

**File:** `backend/app/agent/interface.py` → `InterfaceAgent`

Before the full pipeline runs, the **InterfaceAgent** classifies the user's intent. This prevents unnecessary (and expensive) generation runs when the user is just chatting.

### Heuristic Fast-Paths (No LLM Call Needed)

The agent checks a series of heuristics first, in order:

1. **Artifact Retrieval** (`_quick_artifact_retrieval_request`): Detects phrases like *"send the files again"* → returns `action_type: artifact_retrieval` without a pipeline call.
2. **Code Question** (`_quick_thread_code_question`): Detects questions like *"how does auth work?"* when prior agent context exists → routes to ChromaDB RAG instead.
3. **Social/Greeting** (`_quick_non_pipeline`): Catches *"hi"*, *"thanks"*, *"who are you?"* → returns a chat reply directly.
4. **Resume from Architecture** (`_quick_resume_from_architecture`): Detects *"use the same architecture"* → triggers pipeline but skips Requirements and Architecture stages.

### LLM Classification (Fallback)

If no heuristic matches, the InterfaceAgent calls the LLM (`MODEL_INTERFACE`) with a structured output schema (`InterfaceDecision`). The LLM decides:
- `should_trigger_pipeline: true/false`
- `action_type: build_new | continue_from_architecture | chat | artifact_retrieval`
- `pipeline_prompt`: a cleaned version of the user's request for downstream agents
- `assistant_reply`: the message shown to the user

The response is normalized (`_normalize_decision`) to enforce consistency, and if attachments have text content, the acknowledgment is enriched with a concrete detail from the file.

---

## 4. The Orchestrator (Central Pipeline Controller)

**File:** `backend/app/agent/orchestrator.py` → `run_pipeline_generator()`

If the InterfaceAgent decides `should_trigger_pipeline=true`, the orchestrator takes over. This is an **async generator** function that `yield`s JSON-serialized SSE events at each stage.

The `GenerationRun` status is updated to `running`, and the pipeline proceeds through stages sequentially.

---

## 5. Stage 1: Requirements Agent

**File:** `backend/app/agent/requirements_agent.py` → `RequirementsAgent`

### What it does
Takes the raw user prompt and produces a structured `ProjectCharter` containing:
- `project_name`, `description`
- `entities[]` — data models with typed fields
- `endpoints[]` — REST routes with HTTP methods
- `business_rules[]` — specific logic constraints
- `auth_required` — whether auth is needed

### How it works
1. Calls `self.llm.generate_structured()` with `REQUIREMENTS_SYSTEM_PROMPT` and the user prompt.
2. The LLM returns JSON conforming to the `ProjectCharter` Pydantic schema.
3. **Graceful fallback:** If the LLM returns empty `entities` or `endpoints` (common with smaller/free models), defaults are injected (a generic `Item` entity and `/items` CRUD endpoints) instead of crashing.

### SSE Events
- `requirements` → *"Analyzing requirements..."*
- `requirements_done` → sends the full `ProjectCharter` artifact JSON

The artifact is also persisted to the database as an `ArtifactRecord` (stage: `requirements`).

---

## 6. Stage 2: Architecture Agent

**File:** `backend/app/agent/architecture_agent.py` → `ArchitectureAgent`

### What it does
Takes the `ProjectCharter` and designs the `SystemArchitecture`:
- `design_document` — Markdown-formatted architecture spec
- `mermaid_diagram` — flowchart visualizing the backend components
- `components[]` — bullet summaries of backend modules
- `data_model_summary[]` — entity descriptions for the ER diagram
- `endpoint_summary[]` — handler/router descriptions

### How it works
1. Serializes the charter as JSON and sends it to the LLM with `ARCHITECTURE_SYSTEM_PROMPT`.
2. The LLM returns a `SystemArchitecture` object.
3. **Mermaid normalization** (`_normalize_mermaid`): The raw Mermaid diagram from the LLM is cleaned up:
   - Strips markdown fences and BOM characters
   - Forces `flowchart TD` (top-down) layout
   - Removes fragile `note` syntax
   - Quotes labels with special characters
   - Replaces arrow characters inside labels that break tokenization

### SSE Events
- `architecture` → *"Designing system architecture..."*
- `architecture_done` → sends the full `SystemArchitecture` artifact JSON

The frontend uses the `mermaid_diagram` field to render the live architecture diagram and the `data_model_summary` for the ER schema visualizer.

---

## 7. Stage 3: Implementer Agent

**File:** `backend/app/agent/implementer_agent.py` → `ImplementerAgent`

### What it does
Takes the `SystemArchitecture` and produces actual Python source code — a complete, runnable FastAPI application.

### How it works (Two-Phase Generation)

**Phase 1: Planning** — The agent first calls the LLM with a `PLAN_PROMPT` to generate a `CodeGenerationPlan`:
```
files: [
  { path: "app/main.py", purpose: "FastAPI entrypoint" },
  { path: "app/models.py", purpose: "SQLModel entities" },
  { path: "app/routes.py", purpose: "CRUD endpoints" },
  ...
]
dependencies: ["sqlmodel", "passlib", ...]
```

**Phase 2: Per-File Generation** — For each planned file, the agent calls the LLM individually with a `FILE_PROMPT` that includes:
- The architecture document
- The full plan (so the LLM knows what other files exist)
- The specific file to generate

This two-phase approach avoids the LLM generating one massive JSON blob with all code, which frequently causes truncation and parsing failures.

### Patching Support
The `patch_files()` method allows targeted file regeneration. It receives `FilePatchRequest` objects (specifying path, reason, and instructions) and only regenerates the affected files while preserving the rest. This is used by both the reviewer and sandbox retry loops.

### SSE Events
- `implementer` → *"Generating source code..."*
- `implementer_done` → sends `files_count` and the full file map

The generated code is stored on disk via `artifact_store.py` (to avoid inlining large JSON in the database) and a `bundle_ref` is saved in the `ArtifactRecord`.

---

## 8. Stage 4: Deterministic Test Runner

**File:** `backend/app/agent/test_runner.py` → `TestRunner`

### What it does
Runs fast, **deterministic** checks on the generated code — no LLM calls, no containers. Catches issues the LLM commonly creates.

### Checks Performed

1. **Syntax Check** (`_syntax_check`): Compiles every `.py` file with Python's built-in `compile()`. Catches `SyntaxError` immediately.

2. **Import Validation** (`_import_validation_check`): Scans code for commonly-used names like `Field`, `SQLModel`, `Depends`, `HTTPException` and verifies they have matching `import` statements. This catches the most frequent LLM mistake — using a name like `Field(...)` without `from sqlmodel import Field`.

3. **Import Smoke Test** (`_run_import_smoke`): Writes all files to a temp directory and runs `python -c "from app.main import app"` as a subprocess. This catches runtime `ImportError` / `ModuleNotFoundError` that syntax checks can't detect (e.g., circular imports, missing `__init__.py`).

### Auto-Patching
If any check fails, the `TestRunner` creates `FilePatchRequest` objects targeting the specific files and sends them back to the Implementer for regeneration. The orchestrator applies the patches before proceeding.

### SSE Events
- `testing` → *"Running deterministic code checks..."*
- `testing_fix` → *"Found N issue(s), auto-patching..."*
- `testing_done` → summary of which checks were run and whether they passed

---

## 9. Stage 5: Test Generator Agent

**File:** `backend/app/agent/test_generator_agent.py` → `TestGeneratorAgent`

### What it does
Uses an LLM to generate a `pytest` test suite tailored to the generated API's actual endpoints and models.

### How it works
1. Builds a prompt combining:
   - The architecture `design_document`
   - The `endpoint_summary` and `data_model_summary`
   - The actual generated code files (so tests match real route paths)
2. Calls `self.llm.generate_structured()` with `TEST_GENERATOR_SYSTEM_PROMPT` to produce a `GeneratedTests` artifact.
3. The artifact contains `test_files[]` (pytest `.py` files) and `dependencies[]` (like `httpx`, `pytest-anyio`).

### Non-Blocking
Test generation is wrapped in a `try/except` — if it fails, the pipeline continues without tests. The sandbox will simply report 0 tests.

### SSE Events
- `test_generation` → *"Generating endpoint test suite..."*
- `test_generation_done` → list of generated test file paths

---

## 10. Stage 6: Reviewer Agent (Perceive-Plan-Act Loop)

**File:** `backend/app/agent/reviewer_agent.py` → `ReviewerAgent`

### What it does
Audits the generated code for security vulnerabilities, logic bugs, and code quality. Returns a `ReviewReport` with:
- `issues[]` — severity-tagged problems found
- `security_score` — 1-10 trust score
- `approved` — boolean
- `patch_requests[]` — targeted fix instructions
- `final_code[]` — (optional) directly rewritten files

### The Review Loop (Orchestrator Logic)

```
MAX_REVIEW_ITERATIONS = 5
REVIEW_TRUST_SCORE_THRESHOLD = 7
```

For each pass:
1. The ReviewerAgent reviews the current code.
2. **Approval condition:** `approved == True` AND `security_score >= 7`.
3. If approved → break loop, emit `reviewer_done`.
4. If not approved:
   - If the reviewer returned `final_code` (rewrites) → use them directly.
   - Otherwise, build `FilePatchRequest` from `issues` and `affected_files`.
   - Route patch requests back to the **Implementer** for targeted fixes.
   - Re-run the reviewer on the patched code.

### Score Floor Enforcement
```python
if previous_score is not None and review_report.security_score < previous_score:
    review_report.security_score = previous_score
```
The score can **never decrease** across passes — this prevents models that oscillate between scores from trapping the loop.

### SSE Events
- `reviewer` → *"Review pass N/5..."*
- `revision` → *"Pass N: X issues found, regenerating..."*
- `reviewer_done` → final score and artifact

---

## 11. Stage 7: Sandbox Deployment & Testing

**File:** `backend/app/agent/sandbox_executor.py` → `SandboxExecutor`

### What it does
Deploys the reviewed code + generated tests into a live Docker container (`sandbox-runner`), runs `pytest`, and reports results.

### The Deploy Process (`_write_files`)

1. **Cleans** any previous deployment in `/sandbox/{project_id}/`.
2. **Writes** all application code files (with `_auto_patch_content` fixes for common issues like missing `email-validator` dependency).
3. **Writes** test files (if generated).
4. **Writes** `requirements.txt` with base deps (`fastapi`, `uvicorn[standard]`, `sqlmodel`) + generated deps + test deps.
5. **Writes** `start.sh` — the launcher script:
   ```bash
   pip install -q -r requirements.txt
   ruff check . --fix --quiet  # auto-fix minor issues
   uvicorn $MODULE --host 0.0.0.0 --port 9000 &
   # Wait for API to be healthy (Python urllib, not curl)
   python -c "import urllib.request, time; ..."
   # Run pytest and write results
   pytest tests/ ... > /sandbox/{id}/pytest.log
   touch /sandbox/{id}/.pytest_done
   ```

### Health Check (`_wait_for_health`)
The backend polls `http://sandbox-runner:9000/docs` using `urllib.request.urlopen` with a 45-second timeout. This confirms the generated API actually started and is serving requests.

### Test Execution (`_run_pytest`)
Instead of running `docker exec` (which fails because the Docker CLI isn't available inside the backend container), `start.sh` runs `pytest` **natively** inside the sandbox after Uvicorn starts. The backend then:
1. Polls for a `.pytest_done` marker file on the shared volume.
2. Reads `pytest.log` to extract pass/fail counts and failure details.
3. Parses the log with regex to build a `SandboxTestReport`.

### Sandbox Retry Loop (Orchestrator)

```
MAX_SANDBOX_RETRIES = 3
```

If the sandbox fails (deploy error, health check fails, or tests fail):
1. The orchestrator parses the `test_output` for Python tracebacks using regex:
   ```python
   re.search(r'File "[^"]*/(app/\S+\.py)", line (\d+)', test_output)
   re.search(r'(NameError|ImportError|...): (.+)', test_output)
   ```
2. Builds `FilePatchRequest` objects targeting the exact files mentioned in the traceback.
3. Sends them to the Implementer for patching.
4. Re-deploys and re-tests.

### SSE Events
- `sandbox_deploy` → *"Sandbox deploy attempt N/3..."*
- `sandbox_retry` → *"Attempt N failed — patching..."*
- `sandbox_deploy_done` → ✅ or ❌ with test counts

---

## 12. Completion & RAG Indexing

**File:** `backend/app/agent/orchestrator.py` (end of `run_pipeline_generator`)

After the sandbox loop finishes:

1. The `GenerationRun` status is updated to `completed`.
2. The final `completed` SSE event is emitted with a summary of all artifacts.
3. Back in `generate.py`, the completed code files are indexed into **ChromaDB** via `replace_thread_generated_files()` for future code Q&A.

---

## 13. Frontend Receives Results

**File:** `frontend/src/pages/ChatPage.jsx`

The frontend processes each SSE event and updates the UI:

| SSE Event | UI Update |
|-----------|-----------|
| `requirements_done` | Shows the "Requirements Document" artifact chip, renders the ER schema diagram |
| `architecture_done` | Shows the "Architecture Diagram" chip, renders the Mermaid flowchart |
| `implementer_done` | Populates code file chips, enables "Download Backend Files" button |
| `reviewer_done` | Shows review score badge |
| `sandbox_deploy_done` | Shows test pass/fail summary |
| `completed` | Enables "Test API Endpoints" and "Open Sandbox" buttons |

The **Dynamic API Tester** panel parses `requirementsArtifact.endpoints` from the latest agent message and renders endpoint cards matching the actual generated API — not hardcoded routes.

Artifacts (requirements, architecture, code files) are persisted to the `message_artifacts` Supabase table so they survive page refreshes and can be retrieved later.

---

## Supporting Infrastructure

### LLM Client

**File:** `backend/app/agent/llm_client.py` → `LLMClient`

All agents communicate with LLMs through this unified client. Key features:

- **Provider-agnostic:** Uses `AsyncOpenAI` with configurable `base_url`, so any OpenAI-compatible API works (OpenRouter, Groq, Ollama, etc.).
- **Structured output:** `generate_structured()` sends a system prompt + user prompt + schema, then parses the response into a Pydantic model.
- **Think-tag stripping:** Models like DeepSeek-R1 wrap their reasoning in `<think>...</think>` tags — these are stripped before JSON parsing.
- **Robust JSON extraction:** Tries multiple strategies to extract valid JSON from LLM responses:
  1. Direct parse
  2. Strip code fences (` ```json ... ``` `)
  3. Extract balanced JSON span (handles preamble/postamble text)
  4. Retry with schema hint in the prompt
- **Timeout & retry:** 120-second timeout, 3 max retries per call.

### Base Agent

**File:** `backend/app/agent/base.py` → `BaseAgent[InType, OutType]`

All agents inherit from this generic ABC. It provides:
- A constructor that initializes `self.llm = LLMClient(model_name=...)` using the configured model.
- An abstract `run()` method that each agent implements.
- An optional `get_system_prompt()` helper.

### Artifact Store

**File:** `backend/app/agent/artifact_store.py`

Large code bundles are written to disk (`backend/artifact_store/`) as JSON files rather than being stored inline in PostgreSQL. The database `ArtifactRecord` stores a `bundle_ref` path pointing to the file. This prevents the database from growing unboundedly with large generated codebases.

---

## End-to-End Flow Summary

```
User types prompt
    ↓
Frontend → POST /generate/thread/{threadId}/chat (SSE)
    ↓
Thread → Project resolution (PostgreSQL)
    ↓
InterfaceAgent: classify intent (heuristics → LLM fallback)
    ↓ (if build intent)
RequirementsAgent → ProjectCharter
    ↓
ArchitectureAgent → SystemArchitecture + Mermaid diagram
    ↓
ImplementerAgent → GeneratedCode (plan-then-generate)
    ↓
TestRunner → deterministic checks (syntax, imports) → auto-patch
    ↓
TestGeneratorAgent → pytest suite
    ↓
ReviewerAgent → review loop (up to 5 passes, trust ≥ 7)
    ↓
SandboxExecutor → deploy + pytest (up to 3 retries with auto-patch)
    ↓
ChromaDB → index generated code for future RAG queries
    ↓
Frontend → renders artifacts, code files, test results, API tester
```
