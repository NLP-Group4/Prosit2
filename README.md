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

### Backend Setup

#### 1. Clone & create virtual environment

```bash
git clone <repo-url>
cd api_builder/backend

python3 -m venv agents-env
source agents-env/bin/activate
```

#### 2. Install dependencies

```bash
cd backend
pip install -r requirements.txt
```

#### 3. Configure environment

```bash
# From project root
cp .env.example .env
```

Edit `.env` and add your Google API key:

```env
GOOGLE_GENAI_USE_VERTEXAI=0
GOOGLE_API_KEY=your-google-api-key-here
```

#### 4. Start the platform

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

#### 5. Open the UI

Navigate to **http://localhost:8000** in your browser.

### Frontend Setup

The project includes two frontend applications:

#### Marketing Website (Static Site)

```bash
cd frontend/website
npm install
npm run dev          # Development server
npm run build        # Production build
```

See [frontend/website/README.md](./frontend/website/README.md) for details.

#### Desktop App (Electron)

```bash
cd frontend/desktop
npm install
npm run dev          # Development mode
npm run electron:dev # Electron development
npm run package      # Package for distribution
```

See [frontend/desktop/README.md](./frontend/desktop/README.md) for details.

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
  -d @tests/fixtures/sample_specs/two_entity_auth.json \
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
├── backend/                  # Backend API and agents
│   ├── agents/               # LLM agents and orchestration
│   │   ├── orchestrator.py   # Pipeline: Prompt → Spec → Validate → Generate → ZIP
│   │   ├── prompt_to_spec.py # LLM agent (Gemini) for prompt → spec
│   │   ├── spec_review.py    # Deterministic validation agent
│   │   ├── auto_fix.py       # LLM-powered auto-fix agent
│   │   ├── groq_client.py    # Groq API client (fallback provider)
│   │   ├── intent_router.py  # Intent classification
│   │   └── model_registry.py # LLM model registry with fallback chains
│   ├── app/                  # FastAPI backend (platform API)
│   │   ├── main.py           # Builder API entrypoint
│   │   ├── spec_schema.py    # BackendSpec Pydantic model (IR)
│   │   ├── code_generator.py # Jinja2 → project files
│   │   ├── project_assembler.py # Files → ZIP archive
│   │   ├── platform_db.py    # Multi-user database models
│   │   ├── platform_auth.py  # JWT authentication
│   │   ├── storage.py        # File storage management
│   │   ├── rag.py            # RAG context retrieval
│   │   └── templates/        # Jinja2 templates for generated code
│   ├── config/               # Configuration files
│   │   ├── database_setup.sql # Database schema initialization
│   │   └── README.md         # Configuration documentation
│   ├── tests/                # Test suite (organized by type)
│   │   ├── unit/             # Fast, isolated unit tests
│   │   ├── integration/      # Integration tests with dependencies
│   │   ├── e2e/              # End-to-end workflow tests
│   │   ├── fixtures/         # Test fixtures and sample data
│   │   ├── conftest.py       # Pytest configuration
│   │   └── README.md         # Test documentation
│   ├── scripts/              # Utility scripts
│   │   ├── setup_database.sh # Database initialization
│   │   ├── run_tests.sh      # Test runner
│   │   ├── clean_data.sh     # Data cleanup
│   │   └── README.md         # Scripts documentation
│   ├── data/                 # User data storage (gitignored)
│   ├── output/               # Generated project ZIPs (gitignored)
│   ├── docker-compose.yml    # Backend deployment
│   ├── Dockerfile            # Backend container
│   ├── pytest.ini            # Pytest configuration
│   ├── requirements.txt      # Python dependencies
│   └── README.md             # Backend documentation
│
├── frontend/                 # Frontend applications
│   ├── website/             # Marketing website (static React site)
│   │   ├── src/             # React components and pages
│   │   │   ├── pages/       # Landing, Download, Docs, About, Research
│   │   │   ├── components/  # Navbar, Footer, Hero, Features, etc.
│   │   │   └── assets/      # Images and icons
│   │   ├── public/          # Static assets
│   │   ├── package.json     # Node dependencies
│   │   ├── vite.config.js   # Vite build configuration
│   │   └── README.md        # Website documentation
│   │
│   └── desktop/             # Electron desktop application
│       ├── electron/        # Electron main process
│       │   ├── main.cjs     # Electron entrypoint
│       │   ├── preload.cjs  # Preload script
│       │   └── services/    # Docker manager, verification runner
│       ├── src/             # React UI (generation interface)
│       │   ├── pages/       # ChatPage (generation UI)
│       │   ├── components/  # LoginModal, Navbar, etc.
│       │   └── context/     # AuthContext
│       ├── electron-builder.yml  # Build configuration
│       ├── package.json     # Node dependencies
│       ├── BUILD.md         # Build instructions
│       └── README.md        # Desktop app documentation
│
├── docs/                     # Documentation (organized by category)
│   ├── architecture/         # Architecture documents
│   ├── features/             # Feature documentation
│   ├── implementation/       # Implementation reports
│   ├── historical/           # Archived documents
│   └── README.md             # Documentation index
│
├── .kiro/                    # Kiro specs and configurations
│   └── specs/                # Feature specifications
│
├── data/                     # User data storage (gitignored)
├── output/                   # Generated project ZIPs (gitignored)
├── .env                      # Environment variables (gitignored)
├── .env.example              # Environment template
├── .gitignore                # Git ignore rules
└── README.md                 # This file
```

---

## Project Organization

### Monorepo Structure

The project is organized as a monorepo with clear separation between backend and frontend:

**Backend** (`backend/`):
- FastAPI platform API
- LLM agents for code generation
- Configuration and database setup
- Test suite
- Utility scripts
- Docker deployment files

**Frontend** (`frontend/`):
- **Marketing Website** (`frontend/website/`) - Static React site with landing page, documentation, download page, and informational content. Deployed as a static site (Netlify/Vercel).
- **Desktop App** (`frontend/desktop/`) - Electron application with generation interface, authentication, and local Docker integration. Packaged as a desktop installer.

**Shared** (root level):
- Documentation (`docs/`)
- Environment configuration (`.env`)
- Git configuration (`.gitignore`)

### Frontend Applications

The frontend is split into two independent applications:

#### Marketing Website (`frontend/website/`)

A static React website for public consumption:
- Landing page with product information
- Download page with platform-specific installers
- Documentation (Getting Started, API Reference, CLI Guide)
- About and Research pages
- No authentication required
- Deployed as static site

#### Desktop App (`frontend/desktop/`)

An Electron desktop application for authenticated users:
- Generation interface (ChatPage)
- Authentication (login/signup)
- Local Docker integration
- Project verification
- Requires authentication
- Packaged as desktop installer

### Key Files

- `README.md` - Main project documentation (this file)
- `backend/README.md` - Backend-specific documentation
- `frontend/website/README.md` - Marketing website documentation
- `frontend/desktop/README.md` - Desktop app documentation
- `frontend/desktop/BUILD.md` - Desktop app build instructions
- `backend/requirements.txt` - Python dependencies
- `backend/pytest.ini` - Test configuration
- `backend/docker-compose.yml` - Backend deployment configuration

### Utility Scripts

Common development tasks are automated in the `backend/scripts/` directory:

```bash
# Initialize database
cd backend
./scripts/setup_database.sh

# Run tests
./scripts/run_tests.sh [unit|integration|e2e|all|coverage]

# Clean data
./scripts/clean_data.sh [data|output|cache|logs|all]
```

See [backend/scripts/README.md](./backend/scripts/README.md) for detailed documentation.

---

## Testing

The test suite is organized by type for efficient execution. All tests are located in `backend/tests/`.

### Run All Tests
```bash
cd backend
pytest tests/ -v
# Or use the script
./scripts/run_tests.sh all
```

### Run by Test Type

**Unit tests** (fast, no Docker required):

```bash
cd backend
pytest tests/unit/ -v
# Or use the script
./scripts/run_tests.sh unit
```

**Integration tests** (requires external dependencies):

```bash
cd backend
pytest tests/integration/ -v
# Or use the script
./scripts/run_tests.sh integration
```

**End-to-end tests** (complete workflows):

```bash
cd backend
pytest tests/e2e/ -v
# Or use the script
./scripts/run_tests.sh e2e
```

### Run with Coverage

```bash
cd backend
pytest tests/ --cov=app --cov=agents --cov-report=html
# Or use the script
./scripts/run_tests.sh coverage
```

### Test Markers

Tests are marked by type for selective execution:

```bash
cd backend

# Run only unit tests
pytest -m unit -v

# Run only integration tests
pytest -m integration -v

# Run only e2e tests
pytest -m e2e -v

# Skip integration tests (fast feedback)
pytest -m "not integration" -v
```

See [backend/tests/README.md](./backend/tests/README.md) for detailed test documentation.

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
| `GROQ_API_KEY` | No | — | Groq API key for fallback LLM provider |
| `GOOGLE_GENAI_USE_VERTEXAI` | No | `0` | Set to `1` to use Vertex AI instead |
| `PLATFORM_DATABASE_URL` | Yes | — | PostgreSQL connection string for platform DB |
| `PLATFORM_SECRET_KEY` | Yes | — | Secret key for JWT token signing |
| `CORS_ORIGINS` | No | `*` | Comma-separated allowed origins for CORS |

---

## Documentation

For detailed documentation, see the [docs/](./docs/) folder:

- **Architecture:** [Cloud + Electron Architecture](./docs/architecture/cloud-electron.md)
- **Separation Guide:** [Backend/Frontend Separation](./docs/SEPARATION_GUIDE.md)
- **Deployment Guide:** [Deployment Instructions](./docs/DEPLOYMENT_GUIDE.md)
- **Monorepo Structure:** [Monorepo Complete](./docs/MONOREPO_COMPLETE.md)
- **Implementation:** [Implementation Complete Report](./docs/implementation/complete.md)
- **Features:** [Groq Integration](./docs/features/groq-integration.md), [Auto-Fix](./docs/features/autofix.md)

### Component-Specific Documentation

- **Backend:** [backend/README.md](./backend/README.md)
- **Marketing Website:** [frontend/website/README.md](./frontend/website/README.md)
- **Desktop App:** [frontend/desktop/README.md](./frontend/desktop/README.md)
- **Desktop Build:** [frontend/desktop/BUILD.md](./frontend/desktop/BUILD.md)

---

## License

This project was created as part of a graduate NLP course.
