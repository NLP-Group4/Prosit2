# Backend Generation Platform - Backend

This directory contains the backend API and LLM agent orchestration system for the Backend Generation Platform.

## Architecture

The backend consists of:

- **FastAPI Application** (`app/`) - REST API for spec management, code generation, and project assembly
- **LLM Agents** (`agents/`) - Orchestration, prompt-to-spec, spec review, auto-fix, and deployment verification
- **Configuration** (`config/`) - Database setup and configuration files
- **Tests** (`tests/`) - Unit, integration, and end-to-end tests
- **Scripts** (`scripts/`) - Utility scripts for database setup, testing, and data management

## Development Setup

### Prerequisites

- Python 3.9+
- PostgreSQL 13+
- Docker and Docker Compose (optional)

### Local Setup

1. Create and activate virtual environment (from backend directory):
```bash
cd backend
python -m venv agents-env
source agents-env/bin/activate  # On macOS/Linux
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp ../.env.example ../.env
# Edit .env with your configuration
```

4. Set up database:
```bash
./scripts/setup_database.sh
```

### Running Locally

Start the FastAPI server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

API documentation: `http://localhost:8000/docs`

### Running with Docker

Build and run with Docker Compose:
```bash
docker compose up --build
```

## Testing

Run all tests:
```bash
pytest tests/ -v
```

Run specific test suites:
```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# End-to-end tests only
pytest tests/e2e/ -v
```

Run tests with coverage:
```bash
pytest tests/ --cov=app --cov=agents --cov-report=html
```

See `tests/README.md` for more details.

## Project Structure

```
backend/
├── agents/              # LLM agents and orchestration
│   ├── orchestrator.py      # Main agent orchestration
│   ├── prompt_to_spec.py    # Convert prompts to specs
│   ├── spec_review.py       # Review and validate specs
│   ├── auto_fix.py          # Automatic error fixing
│   ├── deploy_verify.py     # Deployment verification
│   ├── groq_client.py       # Groq API client
│   ├── intent_router.py     # Intent classification
│   └── model_registry.py    # Model configuration
│
├── app/                 # FastAPI application
│   ├── main.py              # Application entry point
│   ├── spec_schema.py       # Pydantic models
│   ├── code_generator.py    # Code generation logic
│   ├── project_assembler.py # Project assembly
│   ├── platform_db.py       # Database operations
│   ├── platform_auth.py     # Authentication
│   ├── storage.py           # File storage
│   ├── rag.py               # RAG implementation
│   ├── document_processor.py # Document processing
│   ├── report_generator.py  # Report generation
│   └── templates/           # Code templates
│
├── config/              # Configuration
│   ├── database_setup.sql   # Database schema
│   └── README.md
│
├── tests/               # Test suite
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   ├── e2e/                 # End-to-end tests
│   ├── fixtures/            # Test fixtures
│   └── conftest.py          # Pytest configuration
│
├── scripts/             # Utility scripts
│   ├── setup_database.sh    # Database setup
│   ├── run_tests.sh         # Test runner
│   └── clean_data.sh        # Data cleanup
│
├── data/                # User data storage (gitignored)
├── output/              # Temporary ZIP storage (gitignored)
├── docker-compose.yml   # Docker composition
├── Dockerfile           # Container definition
├── requirements.txt     # Python dependencies
└── pytest.ini           # Test configuration
```

## Deployment

### Docker Deployment

Build the Docker image:
```bash
docker build -t backend-api .
```

Run the container:
```bash
docker run -p 8000:8000 --env-file ../.env backend-api
```

### Cloud Deployment

See `../docs/DEPLOYMENT_GUIDE.md` for detailed deployment instructions for:
- Railway
- AWS (ECS, Lambda)
- Render
- Other cloud platforms

## API Endpoints

### Health Check
- `GET /health` - Health check endpoint

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login user
- `POST /auth/logout` - Logout user

### Spec Management
- `POST /specs` - Create new spec
- `GET /specs/{spec_id}` - Get spec by ID
- `PUT /specs/{spec_id}` - Update spec
- `DELETE /specs/{spec_id}` - Delete spec
- `GET /specs` - List all specs

### Code Generation
- `POST /generate` - Generate code from spec
- `GET /generate/{job_id}` - Get generation status

### Project Assembly
- `POST /assemble` - Assemble project from generated code
- `GET /assemble/{job_id}` - Get assembly status

See API documentation at `/docs` for complete endpoint reference.

## Environment Variables

Required environment variables (see `../.env.example`):

- `DATABASE_URL` - PostgreSQL connection string
- `GROQ_API_KEY` - Groq API key for LLM access
- `JWT_SECRET` - Secret key for JWT tokens
- `STORAGE_PATH` - Path for file storage

## Contributing

1. Create a feature branch
2. Make your changes
3. Add tests for new functionality
4. Run tests: `pytest tests/ -v`
5. Submit a pull request

## License

See root LICENSE file for details.
