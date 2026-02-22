# Backend Generation Platform

A deterministic backend compiler that converts natural language prompts (or JSON specifications) into fully functional, Dockerized FastAPI backends.

> Feed it a spec, get a production-ready API.

---

## Features

- **Prompt-to-backend** — Describe your API in plain English, get a downloadable ZIP
- **Spec-to-backend** — Submit a JSON specification for deterministic code generation
- **Full CRUD** — Auto-generated endpoints for every entity
- **JWT authentication** — Optional, configurable auth with registration and login
- **Dockerized output** — Generated projects run with a single `docker compose up`
- **Swagger UI** — Every generated backend ships with OpenAPI docs at `/docs` and `/redoc`
- **Endpoint verification** — Automated smoke testing of all endpoints before delivery

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| **Python** | 3.11+ | Runtime |
| **pip / venv** | — | Package management |
| **Google API Key** | — | Powers the PromptToSpec agent (Gemini) |
| **Docker** *(optional)* | 20+ | Required only to run generated backends or integration tests |

---

## Quick Start

### 1. Clone & create virtual environment

```bash
git clone <repo-url>
cd api_builder

python3 -m venv agents-env
source agents-env/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and add your Google API key:

```env
GOOGLE_GENAI_USE_VERTEXAI=0
GOOGLE_API_KEY=your-google-api-key-here
```

### 4. Start the platform

```bash
uvicorn app.main:app --reload --port 8000
```

### 5. Open the UI

Navigate to **http://localhost:8000** in your browser.

---

## Usage

### Option A: Web UI (recommended)

1. Open http://localhost:8000
2. Type a prompt like: *"A blog API with posts and comments. Authentication required."*
3. Click **Generate Backend**
4. Download the ZIP file

### Option B: API — from a prompt

```bash
curl -X POST http://localhost:8000/generate-from-prompt \
  -H "Content-Type: application/json" \
  -d '{"prompt": "A todo list API with tasks and categories"}' \
  --output backend.zip
```

### Option C: API — from a JSON spec

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d @tests/sample_specs/two_entity_auth.json \
  --output backend.zip
```

### Interactive API docs

Visit **http://localhost:8000/docs** for the Swagger UI, or **http://localhost:8000/redoc** for ReDoc.

---

## Running the Generated Backend

Every generated project is self-contained. After downloading:

```bash
unzip backend.zip
cd <project-name>
docker compose up --build
```

Once running:

| URL | Description |
|-----|-------------|
| http://localhost:8000 | API root |
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/redoc | ReDoc documentation |
| http://localhost:8000/health | Health check |

---

## Project Structure

```
api_builder/
├── app/
│   ├── main.py              # Builder API (FastAPI)
│   ├── spec_schema.py        # BackendSpec Pydantic model (IR)
│   ├── code_generator.py     # Jinja2 → project files
│   ├── project_assembler.py  # Files → ZIP archive
│   └── templates/            # Jinja2 templates for generated code
│       ├── main.py.j2
│       ├── models.py.j2
│       ├── schemas.py.j2
│       ├── crud.py.j2
│       ├── router.py.j2
│       ├── auth.py.j2
│       ├── config.py.j2
│       ├── database.py.j2
│       ├── dockerfile.j2
│       ├── docker_compose.yml.j2
│       ├── requirements.txt.j2
│       └── gitignore.j2
├── agents/
│   ├── orchestrator.py       # Pipeline: Prompt → Spec → Validate → Generate → ZIP → Verify
│   ├── prompt_to_spec.py     # LLM agent (Gemini) for prompt → spec
│   ├── spec_review.py        # Deterministic validation agent
│   ├── deploy_verify.py      # Docker deploy + endpoint smoke test agent
│   └── model_registry.py     # LLM model registry with fallback chains
├── static/
│   └── index.html            # Web UI
├── tests/
│   ├── test_spec_schema.py
│   ├── test_code_generator.py
│   ├── test_spec_review.py
│   ├── test_project_assembler.py
│   └── test_integration.py   # Docker-based E2E tests
├── requirements.txt
├── .env.example
├── pytest.ini
└── project.md                # MVP specification
```

---

## Testing

### Unit tests (fast, no Docker required)

```bash
source agents-env/bin/activate
pytest tests/ -v -m "not integration"
```

### Integration tests (requires Docker)

Builds and runs a generated project in Docker, then verifies health, Swagger UI, JWT auth, and full CRUD:

```bash
pytest tests/test_integration.py -v -m integration
```

---

## Specification Schema

The system's Intermediate Representation (IR). Both prompt-based and manual flows produce a `BackendSpec`:

```json
{
  "project_name": "my-api",
  "description": "My awesome API",
  "database": { "type": "postgres", "version": "15" },
  "auth": { "enabled": true, "type": "jwt", "access_token_expiry_minutes": 30 },
  "entities": [
    {
      "name": "Task",
      "table_name": "tasks",
      "fields": [
        { "name": "id", "type": "uuid", "primary_key": true, "nullable": false, "unique": true },
        { "name": "title", "type": "string", "nullable": false },
        { "name": "done", "type": "boolean", "nullable": false }
      ],
      "crud": true
    }
  ]
}
```

**Allowed field types:** `string`, `integer`, `float`, `boolean`, `datetime`, `uuid`, `text`

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_API_KEY` | Yes | — | Gemini API key for prompt-based generation |
| `GOOGLE_GENAI_USE_VERTEXAI` | No | `0` | Set to `1` to use Vertex AI instead |
| `CORS_ORIGINS` | No | `*` | Comma-separated allowed origins for CORS |

---

## License

This project was created as part of a graduate NLP course.
