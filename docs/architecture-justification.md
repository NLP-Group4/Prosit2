# Interius — Architecture & Technology Justification

This document explains **why** each major technology, design pattern, and architectural decision was made in Interius. It is structured around the Prosit 2 requirement: *"How you went about solving the problem and justification of your choices."*

---

## 1. Why a Multi-Agent Pipeline?

### The Problem
A single LLM call cannot reliably produce a working API from a plain-English prompt. The output is too large, the task is too complex, and the result is unpredictable. A monolithic prompt leads to:
- Truncated JSON (models hit output token limits)
- Missing imports, broken schemas, inconsistent naming
- No mechanism for self-correction

### Our Solution: Separation of Concerns
We decompose the software development lifecycle into **specialized agents**, each with a narrow, well-defined task — mirroring how a real development team operates:

| Agent | Analogous Human Role | Why Separate? |
|-------|----------------------|---------------|
| Requirements Agent | Product Manager | Structured extraction prevents ambiguity from propagating downstream |
| Architecture Agent | System Architect | Design decisions are made before code, not during |
| Implementer Agent | Software Developer | Per-file generation avoids JSON truncation on large codebases |
| Test Runner | Static Analysis Tool | Deterministic checks don't need an LLM — faster and more reliable |
| Test Generator | QA Engineer | LLM-generated tests match the actual architecture dynamically |
| Reviewer Agent | Code Reviewer / Security Auditor | Catches bugs the implementer introduced; different model = different perspective |
| Sandbox Executor | DevOps / CI Pipeline | Real runtime validation in Docker — the only way to confirm the code actually works |

### Theoretical Grounding
This follows the **Perceive-Plan-Act** loop from agentic AI research:
- **Perceive**: Reviewer reads the code; Sandbox reports runtime errors
- **Plan**: The orchestrator builds `FilePatchRequest` objects targeting specific files
- **Act**: The Implementer regenerates only the affected files

The review and sandbox stages implement **self-reflection** — the system evaluates its own output and iterates until a quality threshold is met (`security_score ≥ 7`).

---

## 2. Why FastAPI (Backend Framework)?

| Criterion | FastAPI | Alternatives Considered |
|-----------|---------|------------------------|
| **Async-native** | First-class `async/await` — critical for parallel LLM calls and SSE streaming | Flask requires extensions; Django is synchronous by default |
| **Pydantic integration** | Every agent returns a Pydantic model; FastAPI validates them natively | Express.js has no equivalent schema validation layer |
| **OpenAPI auto-docs** | `/docs` endpoint auto-generated — useful for the sandbox Swagger UI | Would need manual Swagger setup in Flask |
| **SSE support** | `EventSourceResponse` from `sse-starlette` works natively | Flask-SSE exists but is less mature |
| **SQLModel compatibility** | SQLModel (by the same author) provides ORM + Pydantic schemas in one class | SQLAlchemy alone requires separate schema/model definitions |
| **Python ecosystem** | Direct access to `openai`, `chromadb`, `pdftotext`, and all ML libraries | Node.js would require separate Python microservices for ML tasks |

**Verdict:** FastAPI is the natural choice for an AI-powered backend that needs async LLM calls, structured validation, real-time streaming, and Python ML ecosystem access.

---

## 3. Why OpenRouter (LLM Provider)?

### The Problem
Different tasks benefit from different models:
- **Requirements extraction** needs strong instruction-following (structured JSON)
- **Code generation** needs deep coding knowledge
- **Code review** needs reasoning ability
- **Intent routing** needs speed (low latency)

### Why Not a Single Provider?
Locking into one provider (e.g., only OpenAI, only Anthropic) means:
- If that provider has an outage, the entire system fails
- You cannot optimize cost vs. quality per agent
- You miss model-specific strengths (DeepSeek for reasoning, Qwen for coding)

### Our Approach: Provider-Agnostic via OpenRouter
We use the **OpenAI-compatible API standard** with OpenRouter as the default router:

```python
# config.py — every agent is independently configurable
MODEL_DEFAULT = "deepseek/deepseek-r1-0528:free"
MODEL_IMPLEMENTER = "qwen/qwen3-235b-a22b-thinking-2507"
MODEL_REVIEWER = "deepseek/deepseek-r1-0528:free"
MODEL_INTERFACE = "deepseek/deepseek-r1-0528:free"
```

**Benefits:**
- **One `base_url` change** switches the entire system to Groq, Ollama (local), or direct OpenAI
- Per-agent model selection lets us optimize cost (free models for routing, premium for code gen)
- The `LLMClient` handles model-specific quirks (e.g., stripping `<think>` tags from DeepSeek-R1)

---

## 4. Why React + Vite (Frontend)?

| Criterion | React + Vite | Alternatives |
|-----------|-------------|--------------|
| **Component model** | Composable, reusable components for chat, pipeline cards, artifact viewers | Vue/Svelte would also work but team had React experience |
| **HMR speed** | Vite's hot module replacement is near-instant vs. Webpack's multi-second rebuilds | Create React App uses Webpack (slow) |
| **SSE consumption** | Native `EventSource` API works directly in React state management | Same in any framework |
| **Ecosystem** | Framer Motion (animations), React Markdown, Mermaid rendering — all React-native | Smaller ecosystems for Svelte/Vue |
| **Supabase SDK** | `@supabase/supabase-js` has first-class React hooks (`useSupabaseClient`) | Available for all frameworks |

**Why Vanilla CSS instead of Tailwind?** Full control over complex layout components like the Schema Visualizer (interactive SVG), pipeline progress cards, and the API Tester panel. These required custom CSS animations and precise positioning that utility classes make harder to maintain.

---

## 5. Why Supabase (Frontend Persistence)?

### The Problem
The backend PostgreSQL database is designed for pipeline data (projects, runs, artifacts). But the **chat experience** needs:
- User authentication (sign up, login, OAuth)
- Thread persistence (across sessions)
- Message history (user + assistant + agent messages)
- File attachment metadata
- Real-time updates

### Why Not Just Use Backend PostgreSQL?
- **Authentication**: We would need to build email/password auth, OAuth integration, and session management from scratch
- **Real-time**: PostgreSQL doesn't natively push updates to the frontend; Supabase provides real-time subscriptions
- **RLS Policies**: Supabase's Row Level Security ensures users can only access their own threads without backend middleware
- **Speed**: Supabase provides auth + database + storage as a single service — we avoid building infrastructure

### The Thread ↔ Project Bridge
Since we use two databases, we bridge them with a marker:
```
Project.description = "[chat-thread:{supabase_thread_id}]"
```
This is simple, reliable, and queryable. The `_resolve_or_create_project_for_thread()` function handles the lookup/creation.

---

## 6. Why ChromaDB (Vector Store)?

| Criterion | ChromaDB | Alternatives |
|-----------|----------|-------------|
| **Embedded mode** | Runs in-process — no separate server needed | Pinecone, Weaviate, Qdrant all require separate deployments |
| **Per-collection isolation** | Each thread gets its own collection — no cross-thread data leakage | Would need manual namespacing in Pinecone |
| **Python-native** | `pip install chromadb` — zero config | Elasticsearch requires Java, separate cluster |
| **Persistent storage** | Writes to `backend/chroma_db/` — survives container restarts | In-memory stores lose data |
| **Gemini embeddings** | `text-embedding-004` via Google's API gives high-quality dense vectors | OpenAI embeddings cost more per call |

**Use case:** After each pipeline run, all generated code files are indexed into ChromaDB. When a user asks *"how does auth work in my API?"*, the InterfaceAgent retrieves the top-5 most similar code chunks and answers with file citations.

---

## 7. Why Docker Sandbox (Execution Engine)?

### The Problem
Generating code isn't enough — we need to **prove it works**. The only reliable way to verify a generated FastAPI application is to actually run it.

### Why Not Just Lint/Parse?
- Linting catches syntax errors but not runtime `ImportError`, circular imports, or misconfigured routes
- Parsing catches structural issues but not missing dependencies (`sqlmodel` not installed)
- Only **running the code** reveals whether the API starts and serves requests

### Our Approach: Sidecar Docker Container
The `sandbox-runner` is a lightweight Docker container that shares a volume (`/sandbox/`) with the backend:

| Step | What Happens | Why |
|------|-------------|-----|
| 1. Write files | Code + tests + `requirements.txt` + `start.sh` written to shared volume | Docker volume is the simplest IPC mechanism |
| 2. Install deps | `pip install -r requirements.txt` | Real dependency resolution — catches missing packages |
| 3. Ruff fix | `ruff check --fix` | Auto-corrects minor formatting/import issues the LLM introduced |
| 4. Start uvicorn | `uvicorn app.main:app --port 9000` | Confirms the app actually starts |
| 5. Health check | `urllib.request.urlopen("http://localhost:9000/docs")` | Proves the API is serving (we use `urllib` because `curl` isn't installed in the container) |
| 6. Run pytest | `pytest tests/ --tb=short` | Real endpoint tests against the live API |
| 7. Report results | Parse `pytest.log` for pass/fail counts and tracebacks | Structured feedback enables targeted auto-patching |

### Why Not `docker exec`?
The backend container doesn't have the Docker CLI installed (and shouldn't — security risk). Instead, `start.sh` runs everything **natively** inside the sandbox container, and results are communicated via files on the shared volume.

---

## 8. Why Structured Output (Pydantic Models)?

### The Problem
Raw LLM text output is unreliable:
- JSON may be malformed
- Fields may be missing
- Types may be wrong
- Extra text before/after the JSON

### Our Approach
Every agent returns a **Pydantic BaseModel**:

| Artifact | Model | Key Fields |
|----------|-------|------------|
| Requirements | `ProjectCharter` | `entities[]`, `endpoints[]`, `business_rules[]`, `auth_required` |
| Architecture | `SystemArchitecture` | `design_document`, `mermaid_diagram`, `components[]` |
| Code | `GeneratedCode` | `files[]` (path + content), `dependencies[]` |
| Review | `ReviewReport` | `issues[]`, `security_score`, `approved`, `patch_requests[]` |
| Tests | `GeneratedTests` | `test_files[]`, `dependencies[]` |
| Sandbox | `SandboxTestReport` | `deployed`, `health_check_ok`, `tests_passed`, `tests_failed` |

**Benefits:**
- **Validation**: Pydantic rejects malformed responses immediately — the LLM is retried
- **Type safety**: `security_score: int = Field(ge=1, le=10)` prevents invalid scores
- **Serialization**: `.model_dump()` produces clean JSON for SSE events and database storage
- **Documentation**: The schema is self-documenting — each field has a description

---

## 9. Why SSE Streaming (Real-Time Communication)?

| Approach | Pros | Cons |
|----------|------|------|
| **Polling** | Simple to implement | Wastes bandwidth; delays of seconds between updates |
| **WebSockets** | Full-duplex, low latency | Complex connection management; overkill for one-way updates |
| **SSE (our choice)** | Server pushes events over HTTP; built-in browser `EventSource` API; auto-reconnect | One-directional only (fine for our use case) |

The pipeline naturally produces **sequential, one-way events** (requirements_done → architecture_done → implementer_done → ...). SSE is the perfect fit:
- No WebSocket upgrade negotiation
- Works through HTTP proxies and load balancers
- The frontend simply listens and updates the UI progressively
- `EventSourceResponse` from `sse-starlette` integrates natively with FastAPI's async generators

---

## 10. Why Two-Phase Code Generation?

### The Problem
Asking an LLM to generate all files in a single structured JSON response fails for non-trivial projects:
- The response exceeds token limits and truncates mid-file
- JSON parsing fails because the response is incomplete
- The model loses coherence across many files

### Our Solution: Plan-Then-Generate

**Phase 1 — Planning:** The Implementer asks the LLM to produce a `CodeGenerationPlan`:
```json
{
  "files": [
    { "path": "app/main.py", "purpose": "FastAPI entrypoint" },
    { "path": "app/models.py", "purpose": "SQLModel entities" }
  ],
  "dependencies": ["sqlmodel", "passlib"]
}
```

**Phase 2 — Per-File Generation:** For each planned file, a separate LLM call generates just that file's content as plain text. The full plan is included in context so the model knows what other files exist.

**Benefits:**
- No truncation — each file is its own response
- Plain text output (not JSON-wrapped code) — fewer escaping issues
- Failed files can be individually retried without regenerating the entire codebase
- `patch_files()` can regenerate only specific files using the same mechanism

---

## Summary

| Decision | Choice | Core Justification |
|----------|--------|-------------------|
| Architecture | Multi-agent pipeline | Separation of concerns; self-reflection loops; targeted patching |
| Backend | FastAPI + SQLModel | Async-native, Pydantic validation, SSE support, Python ML ecosystem |
| LLM Provider | OpenRouter | Provider-agnostic; per-agent model selection; cost optimization |
| Frontend | React + Vite | Component model, HMR speed, team expertise, ecosystem |
| Frontend Auth/DB | Supabase | Auth + database + RLS in one service; real-time subscriptions |
| Vector Store | ChromaDB | Embedded, per-thread isolation, zero-config, persistent |
| Execution | Docker Sandbox | Only real runtime proves code works; shared-volume IPC |
| Data Contracts | Pydantic Models | Validation, type safety, self-documenting data contracts |
| Communication | SSE Streaming | One-way, auto-reconnect, lightweight, HTTP-compatible |
| Code Generation | Plan-then-generate | Avoids truncation, isolates failures, enables targeted patching |
| Interface Routing | Few-Shot Intent | Achieves **98.04% accuracy** (0.978 F1) on user intent classification, preventing expensive/slow pipeline runs for clear chat messages |
