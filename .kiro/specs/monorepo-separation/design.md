# Design Document: Monorepo Backend/Frontend Separation

## Overview

This design outlines the reorganization of the Backend Generation Platform into a clear monorepo structure with explicit backend/ and frontend/ directories. The goal is to make the logical separation physically obvious in the folder structure while maintaining all functionality.

## Architecture

### Current Structure (Confusing)

```
api_builder/
├── agents/              # Backend (not obvious)
├── app/                 # Backend (not obvious)
├── config/              # Backend (not obvious)
├── tests/               # Backend (not obvious)
├── scripts/             # Backend (not obvious)
├── frontend/            # Frontend (obvious)
├── docs/                # Shared
├── data/                # Runtime (gitignored)
├── output/              # Runtime (gitignored)
├── docker-compose.yml   # Backend (not obvious)
├── Dockerfile           # Backend (not obvious)
├── requirements.txt     # Backend (not obvious)
├── pytest.ini           # Backend (not obvious)
└── README.md            # Root
```

**Problem:** Backend files scattered at root make it unclear what belongs where.

### Proposed Structure (Clear)

```
api_builder/
├── backend/             # ← All backend code (CLEAR)
│   ├── agents/          # LLM agents
│   ├── app/             # FastAPI application
│   ├── config/          # Configuration files
│   ├── tests/           # Backend tests
│   ├── scripts/         # Backend utility scripts
│   ├── docker-compose.yml
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── pytest.ini
│   └── README.md        # Backend-specific README
│
├── frontend/            # ← All frontend code (CLEAR)
│   ├── electron/
│   ├── src/
│   ├── package.json
│   ├── electron-builder.yml
│   └── README.md        # Frontend-specific README
│
├── docs/                # ← Shared documentation
├── .env                 # ← Shared environment (gitignored)
├── .env.example         # ← Shared environment template
├── .gitignore           # ← Shared git rules
└── README.md            # ← Root README (overview)
```

**Benefits:**
- Crystal clear what's backend vs frontend
- Can deploy backend/ independently
- Can package frontend/ independently
- Industry standard monorepo pattern
- Easier onboarding for new developers

## Components and Interfaces

### 1. Backend Directory Structure

```
backend/
├── agents/                   # LLM agents and orchestration
│   ├── __init__.py
│   ├── orchestrator.py
│   ├── prompt_to_spec.py
│   ├── spec_review.py
│   ├── auto_fix.py
│   ├── groq_client.py
│   ├── intent_router.py
│   ├── model_registry.py
│   └── deploy_verify.py
│
├── app/                      # FastAPI application
│   ├── __init__.py
│   ├── main.py
│   ├── spec_schema.py
│   ├── code_generator.py
│   ├── project_assembler.py
│   ├── platform_db.py
│   ├── platform_auth.py
│   ├── storage.py
│   ├── rag.py
│   ├── document_processor.py
│   ├── report_generator.py
│   └── templates/
│
├── config/                   # Configuration
│   ├── database_setup.sql
│   └── README.md
│
├── tests/                    # Test suite
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   ├── fixtures/
│   ├── conftest.py
│   └── README.md
│
├── scripts/                  # Utility scripts
│   ├── setup_database.sh
│   ├── run_tests.sh
│   ├── clean_data.sh
│   └── README.md
│
├── docker-compose.yml        # Docker composition
├── Dockerfile                # Container definition
├── requirements.txt          # Python dependencies
├── pytest.ini                # Test configuration
└── README.md                 # Backend README
```

### 2. Import Path Changes

**Before (confusing):**
```python
# From app/main.py
from app.spec_schema import BackendSpec
from agents.orchestrator import run_pipeline
```

**After (clear):**
```python
# From backend/app/main.py
from backend.app.spec_schema import BackendSpec
from backend.agents.orchestrator import run_pipeline
```

**Implementation:**
- Add `backend/` to Python path
- Update all absolute imports
- Update all relative imports
- Update test imports

### 3. Configuration Updates

#### docker-compose.yml

**Before:**
```yaml
services:
  api:
    build: .
    volumes:
      - ./app:/app/app
      - ./agents:/app/agents
```

**After:**
```yaml
services:
  api:
    build: ./backend
    volumes:
      - ./backend/app:/app/app
      - ./backend/agents:/app/agents
```

#### Dockerfile

**Before:**
```dockerfile
WORKDIR /app
COPY requirements.txt .
COPY app/ ./app/
COPY agents/ ./agents/
```

**After:**
```dockerfile
WORKDIR /app
COPY requirements.txt .
COPY app/ ./app/
COPY agents/ ./agents/
# Note: Dockerfile stays in backend/, so paths are relative to backend/
```

#### pytest.ini

**Before:**
```ini
[pytest]
testpaths = tests
```

**After:**
```ini
[pytest]
testpaths = tests
# Note: pytest.ini stays in backend/, so paths are relative to backend/
```

### 4. Script Updates

**Before:**
```bash
# scripts/run_tests.sh
pytest tests/unit/ -v
```

**After:**
```bash
# backend/scripts/run_tests.sh
pytest tests/unit/ -v
# Note: Script runs from backend/, so paths are relative
```

### 5. Shared Resources

**Root Level (Shared):**
- `docs/` - Documentation for both components
- `.env` - Environment variables (gitignored)
- `.env.example` - Environment template
- `.gitignore` - Git ignore rules
- `README.md` - Project overview and navigation

**Backend Level:**
- `backend/README.md` - Backend-specific documentation
- `backend/.env.example` - Backend environment template (optional)

**Frontend Level:**
- `frontend/README.md` - Frontend-specific documentation (already exists)
- `frontend/.env.example` - Frontend environment template (optional)

## Data Models

No data model changes required - this is purely structural reorganization.

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Import Resolution

*For any* Python file in the backend/ directory, all import statements SHALL resolve correctly to modules within backend/.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

### Property 2: Test Discovery

*For any* test file in backend/tests/, pytest SHALL discover and execute it when run from the backend/ directory.

**Validates: Requirements 7.1, 7.2, 7.3, 7.4**

### Property 3: Backend Independence

*For any* deployment operation, the backend/ directory SHALL contain all necessary files to deploy without requiring files outside backend/.

**Validates: Requirements 8.1, 8.2, 8.3, 8.4**

### Property 4: Frontend Independence

*For any* build operation, the frontend/ directory SHALL contain all necessary files to build without requiring files outside frontend/ (except shared docs).

**Validates: Requirements 9.1, 9.2, 9.3, 9.4**

### Property 5: Configuration Validity

*For any* configuration file (docker-compose.yml, Dockerfile, pytest.ini), all path references SHALL point to existing files or directories.

**Validates: Requirements 4.1, 4.2, 4.3, 4.4**

### Property 6: Git History Preservation

*For any* moved file, git log SHALL show the complete history including commits before the move.

**Validates: Requirements 1.5**

### Property 7: Test Pass Rate

*For any* test suite execution after reorganization, the pass rate SHALL equal or exceed the pass rate before reorganization.

**Validates: Requirements 7.5**

## Error Handling

### Import Errors

**Issue:** Imports fail after moving files

**Solution:**
- Update Python path to include backend/
- Update all absolute imports systematically
- Use find/replace for common patterns
- Test incrementally

**Validation:** Run tests after each batch of changes

### Path Resolution Errors

**Issue:** Configuration files can't find referenced files

**Solution:**
- Update all path references in configuration
- Use relative paths from configuration file location
- Test Docker build and compose

**Validation:** Build Docker image and run compose

### Git History Loss

**Issue:** Moving files might lose git history

**Solution:**
- Use `git mv` command to preserve history
- Move entire directories when possible
- Verify history with `git log --follow`

**Validation:** Check git log for moved files

## Testing Strategy

### Unit Tests

1. **Test import updates** - Verify all imports resolve
2. **Test configuration** - Verify all config files valid
3. **Test path resolution** - Verify all paths exist

### Integration Tests

1. **Run full test suite** - Verify all tests pass
2. **Build Docker image** - Verify Docker build works
3. **Run docker-compose** - Verify compose works
4. **Test deployment** - Verify backend deploys independently

### Manual Testing

1. **Run backend locally** - `cd backend && uvicorn app.main:app`
2. **Run frontend locally** - `cd frontend && npm run dev`
3. **Run both together** - Verify full system works
4. **Deploy backend** - Verify cloud deployment works
5. **Package frontend** - Verify Electron build works

## Implementation Notes

### Migration Steps

1. **Create backend/ directory**
2. **Move directories** (agents/, app/, config/, tests/, scripts/)
3. **Move files** (docker-compose.yml, Dockerfile, requirements.txt, pytest.ini)
4. **Create backend/README.md**
5. **Update Python imports** in all .py files
6. **Update configuration files** (docker-compose.yml, Dockerfile, pytest.ini)
7. **Update scripts** with new paths
8. **Update documentation** (README.md, deployment guides)
9. **Run tests** to verify everything works
10. **Update .gitignore** if needed
11. **Commit changes** with descriptive message

### Python Path Configuration

**Option 1: Update PYTHONPATH**
```bash
# In backend/
export PYTHONPATH="${PYTHONPATH}:$(pwd)/.."
python -m app.main
```

**Option 2: Install as package**
```bash
# In backend/
pip install -e .
```

**Option 3: Update sys.path**
```python
# In backend/app/main.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
```

**Recommended:** Option 1 for development, Option 2 for production

### Import Update Patterns

**Pattern 1: Absolute imports**
```python
# Before
from app.spec_schema import BackendSpec

# After
from backend.app.spec_schema import BackendSpec
```

**Pattern 2: Relative imports (no change needed)**
```python
# Before and After (same)
from .spec_schema import BackendSpec
```

**Pattern 3: Test imports**
```python
# Before
from app.spec_schema import BackendSpec

# After
from backend.app.spec_schema import BackendSpec
```

### Backward Compatibility

**Breaking Changes:**
- Import paths change (intentional)
- Docker build context changes
- Deployment paths change

**No API Changes:**
- REST API endpoints unchanged
- Database schema unchanged
- Environment variables unchanged

### Performance Considerations

- No performance impact - purely organizational
- Docker build might be slightly faster (smaller context)
- No runtime performance changes

## Deployment Impact

### Backend Deployment

**Before:**
```bash
# Deploy from root
docker build -t backend-api .
docker run -p 8000:8000 backend-api
```

**After:**
```bash
# Deploy from backend/
cd backend
docker build -t backend-api .
docker run -p 8000:8000 backend-api
```

### Frontend Packaging

**Before and After (no change):**
```bash
cd frontend
npm run package
```

### CI/CD Updates

**GitHub Actions example:**
```yaml
# Before
- name: Build backend
  run: docker build -t backend-api .

# After
- name: Build backend
  run: |
    cd backend
    docker build -t backend-api .
```

## Documentation Updates

### README.md (Root)

Update to show new structure and provide navigation:
- Overview of monorepo structure
- Links to backend/README.md and frontend/README.md
- Quick start for both components

### backend/README.md (New)

Create backend-specific README:
- Backend architecture
- Development setup
- Running locally
- Running tests
- Deployment instructions

### frontend/README.md (Update)

Update existing frontend README:
- Clarify it's the Electron app
- Reference backend API
- Build instructions

### docs/DEPLOYMENT_GUIDE.md

Update deployment guide:
- New paths for backend deployment
- Updated Docker commands
- Updated CI/CD examples
