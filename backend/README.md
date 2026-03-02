# Interius Backend

The backend for Interius is built with **FastAPI** and **SQLModel** (via SQLAlchemy). It uses an asynchronous Server-Sent Events (SSE) stream to drive the AI agentic pipeline, emitting live status events to the frontend while simultaneously persisting data artifacts to PostgreSQL.

## Core Structure

* `app/agent/`: Contains the pipeline logic.
  * `orchestrator.py`: The `run_pipeline_generator` handles the feed-forward pipeline and the `ReviewerAgent` retry loop.
  * `artifacts.py`: Defines the structured Pydantic outputs passed between agents.
  * `rag.py`: Uses an embedded ChromaDB client to perform Retrieval-Augmented Generation.
  * `*^*_agent.py`: Individual agents (Requirements, Architecture, Implementer, Reviewer) inheriting from `BaseAgent`.
  * `client.py`: Provides a unified `AsyncOpenAI` client, supporting seamless switching between providers like OpenRouter, Groq, Ollama, and OpenAI.
* `app/api/`: Contains standard REST endpoints handling user authentication, projects, pipeline jobs, and sandbox deployment via standard dependency injection.
* `app/models.py`: Defines the database schemas mapping to PostgreSQL.

## Running Locally

Interius uses `uv` for python dependency management. Ensure PostgreSQL is running (e.g., via `docker compose up db -d`).

1. Sync dependencies:
   ```bash
   uv sync
   ```

   If you are not using `uv`, use the curated fallback requirements file instead of a frozen environment export:
   ```bash
   python -m pip install -r requirements.txt
   ```

2. Generate the local DB schemas (if not already managed by the prestart script):
   ```bash
   uv run alembic upgrade head
   ```

3. Start the FastAPI development server:
   ```bash
   uv run fastapi run app/main.py --reload
   ```

## Docker Deployment

The repo now includes a root-level `compose.yml` and a production-oriented `backend/Dockerfile` for the backend.

Important: the backend launches per-project sandbox containers from `app/api/routes/sandbox.py`, so the API container needs Docker access on the host. The compose stack therefore mounts `/var/run/docker.sock` into the backend container.

### Required environment

Set these in a server-side `.env` file before starting the stack:

```env
ENVIRONMENT=production
PROJECT_NAME=Interius
FRONTEND_HOST=https://interius-ai.netlify.app
BACKEND_CORS_ORIGINS=https://interius-ai.netlify.app

SECRET_KEY=replace-with-a-strong-secret
FIRST_SUPERUSER=admin@example.com
FIRST_SUPERUSER_PASSWORD=replace-with-a-strong-password

POSTGRES_SERVER=db
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=replace-with-a-db-password
POSTGRES_DB=app
POSTGRES_SSLMODE=

LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=replace-with-your-key
INTERFACE_LLM_BASE_URL=
INTERFACE_LLM_API_KEY=
GEMINI_API_KEY=

MODEL_DEFAULT=gpt-5-mini
MODEL_INTERFACE=gpt-5-mini
MODEL_IMPLEMENTER=gpt-5-mini
MODEL_REVIEWER=gpt-4o-mini
```

### Start the backend stack

From the repo root:

```bash
docker compose up -d --build
```

The backend will:

1. wait for PostgreSQL,
2. run Alembic migrations,
3. create initial data,
4. start Uvicorn on port `8000`.

### Connect Netlify

After the backend is reachable from a public URL, set this in Netlify:

```env
VITE_BACKEND_URL=https://your-backend-domain
```

Then redeploy the frontend.
