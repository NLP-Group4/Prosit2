# Design Document: Project Structure Optimization

## Overview

This design outlines the reorganization of the Backend Generation Platform's file and folder structure to improve maintainability, discoverability, and developer experience. The optimization focuses on logical grouping, clear separation of concerns, and reducing root directory clutter.

## Architecture

### Current Structure Issues

1. **Root Directory Clutter**: Test files scattered in root (test_autofix_full.py, test_electron_integration.py, test_rag.py)
2. **Flat Documentation**: All docs in single docs/ folder without categorization
3. **Mixed Concerns**: Database setup in root, no scripts directory
4. **Test Organization**: Tests in tests/ but integration tests in root
5. **Incomplete .gitignore**: Missing some common patterns

### Proposed Structure

```
api_builder/
├── .kiro/                        # Kiro specs and configurations
│   └── specs/                    # Feature specifications
├── agents/                       # LLM agents (no change)
├── app/                          # FastAPI backend (no change)
├── config/                       # Configuration files (NEW)
│   └── database_setup.sql        # Database initialization
├── data/                         # Runtime user data (gitignored)
├── docs/                         # Documentation (reorganized)
│   ├── architecture/             # Architecture documents
│   ├── features/                 # Feature documentation
│   ├── implementation/           # Implementation reports
│   ├── historical/               # Archived documents
│   └── README.md                 # Documentation index
├── frontend/                     # Electron app (no change)
├── output/                       # Generated ZIPs (gitignored)
├── scripts/                      # Utility scripts (NEW)
│   ├── setup_database.sh         # Database setup script
│   ├── run_tests.sh              # Test runner script
│   └── README.md                 # Scripts documentation
├── tests/                        # Test suite (reorganized)
│   ├── unit/                     # Unit tests
│   ├── integration/              # Integration tests
│   ├── e2e/                      # End-to-end tests
│   ├── fixtures/                 # Test fixtures and sample data
│   │   └── sample_specs/         # Sample specifications
│   ├── conftest.py               # Pytest configuration
│   └── README.md                 # Test documentation
├── .env                          # Environment variables (gitignored)
├── .env.example                  # Environment template
├── .gitignore                    # Git ignore rules (enhanced)
├── docker-compose.yml            # Docker composition
├── Dockerfile                    # Docker image definition
├── pytest.ini                    # Pytest configuration
├── README.md                     # Main project README
└── requirements.txt              # Python dependencies
```

## Components and Interfaces

### 1. Test Organization

**Structure:**
```
tests/
├── unit/                         # Fast, isolated tests
│   ├── test_code_generator.py
│   ├── test_spec_schema.py
│   ├── test_project_assembler.py
│   └── test_spec_review.py
├── integration/                  # Tests with external dependencies
│   ├── test_api_endpoints.py
│   ├── test_orchestrator.py
│   ├── test_prompt_to_spec.py
│   ├── test_model_registry.py
│   ├── test_integration.py      # Docker integration
│   └── test_rag.py               # RAG system integration
├── e2e/                          # End-to-end workflow tests
│   ├── test_autofix_full.py
│   └── test_electron_integration.py
├── fixtures/                     # Shared test data
│   ├── sample_specs/
│   └── __init__.py
├── conftest.py                   # Pytest fixtures
└── README.md                     # Test documentation
```

**Pytest Configuration:**
- Update pytest.ini to recognize new test paths
- Add markers: @pytest.mark.unit, @pytest.mark.integration, @pytest.mark.e2e
- Configure test discovery patterns

### 2. Documentation Organization

**Structure:**
```
docs/
├── architecture/                 # Architecture documents
│   ├── cloud-electron.md
│   └── system-design.md
├── features/                     # Feature documentation
│   ├── groq-integration.md
│   └── autofix.md
├── implementation/               # Implementation reports
│   ├── status.md
│   ├── complete.md
│   └── test-results.md
├── historical/                   # Archived documents
│   ├── project-evolution.md
│   ├── starbase-spec.txt
│   ├── pdf-text-dump.txt
│   └── error-log.txt
└── README.md                     # Documentation index
```

**File Mappings:**
- architecture-cloud-electron.md → architecture/cloud-electron.md
- GROQ_INTEGRATION.md → features/groq-integration.md
- AUTOFIX_TEST_RESULTS.md → features/autofix.md
- IMPLEMENTATION_STATUS.md → implementation/status.md
- IMPLEMENTATION_COMPLETE.md → implementation/complete.md
- TEST_RESULTS.md → implementation/test-results.md
- project evolution.md → historical/project-evolution.md
- starbase_spec.txt → historical/starbase-spec.txt
- pdf_text_dump.txt → historical/pdf-text-dump.txt
- error log.txt → historical/error-log.txt

### 3. Configuration Directory

**Purpose:** Centralize configuration files that aren't environment-specific

**Contents:**
- database_setup.sql - Database schema initialization
- (Future) nginx.conf, logging.conf, etc.

### 4. Scripts Directory

**Purpose:** Utility scripts for common development tasks

**Contents:**
```
scripts/
├── setup_database.sh             # Initialize database
├── run_tests.sh                  # Run test suites
├── clean_data.sh                 # Clean test data
└── README.md                     # Scripts documentation
```

### 5. Enhanced .gitignore

**Additions:**
```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.pytest_cache/
.coverage
htmlcov/
*.egg-info/
dist/
build/

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db
desktop.ini

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~
.project
.classpath
.settings/

# Logs
*.log
logs/

# Environment
.env
.env.local
.env.*.local

# Data
data/
output/
*.db
*.sqlite
*.sqlite3

# Virtual environments
venv/
env/
ENV/
agents-env/

# Docker
platform_pgdata/
```

## Data Models

No data model changes required - this is purely structural reorganization.

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Test Discovery Completeness

*For any* test file in the tests/ directory tree, pytest SHALL discover and be able to execute it when running the appropriate test suite command.

**Validates: Requirements 1.3, 7.1, 7.2, 7.3**

### Property 2: Documentation Link Validity

*For any* documentation link in docs/README.md, the target file SHALL exist at the specified path.

**Validates: Requirements 2.2, 8.2**

### Property 3: Root Directory Minimalism

*For any* file in the root directory (excluding directories and .gitignore entries), it SHALL be either a configuration file, README.md, or a Docker-related file.

**Validates: Requirements 3.1, 3.2, 3.5**

### Property 4: Test Organization Consistency

*For any* test file, its location SHALL match its test type (unit tests in tests/unit/, integration tests in tests/integration/, e2e tests in tests/e2e/).

**Validates: Requirements 7.1, 7.2, 7.3**

### Property 5: Gitignore Coverage

*For any* generated or temporary file type, there SHALL exist a corresponding .gitignore pattern that prevents it from being tracked.

**Validates: Requirements 4.1, 4.2, 4.3, 4.4**

### Property 6: Documentation Categorization

*For any* documentation file in docs/, it SHALL be located in a category subdirectory (architecture/, features/, implementation/, or historical/).

**Validates: Requirements 2.1, 2.3, 2.5**

### Property 7: Import Path Stability

*For any* Python import statement in the codebase, moving test files SHALL NOT break the import (imports use absolute paths from project root).

**Validates: Requirements 1.1, 1.2, 7.1, 7.2, 7.3**

## Error Handling

### File Move Errors

- **Issue:** File moves might break imports or references
- **Solution:** Use absolute imports from project root (e.g., `from tests.fixtures import ...`)
- **Validation:** Run full test suite after reorganization

### Documentation Link Breakage

- **Issue:** Moving docs might break internal links
- **Solution:** Update all relative links in moved files
- **Validation:** Check all markdown links with a link checker

### Git History Preservation

- **Issue:** Moving files might lose git history
- **Solution:** Use `git mv` command to preserve history
- **Validation:** Verify git log follows moved files

## Testing Strategy

### Unit Tests

1. **Test pytest.ini configuration** - Verify test discovery works with new structure
2. **Test import paths** - Verify all imports resolve correctly
3. **Test documentation links** - Verify all links in docs/README.md are valid

### Integration Tests

1. **Run full test suite** - Verify all tests pass after reorganization
2. **Test Docker build** - Verify Docker containers build with new structure
3. **Test CI/CD** - Verify any CI/CD pipelines work with new structure

### Property-Based Tests

1. **Property 1: Test Discovery** - Generate random test file locations, verify pytest finds them
2. **Property 2: Documentation Links** - Parse all markdown files, verify all links resolve
3. **Property 3: Root Directory** - List root files, verify only allowed types present
4. **Property 4: Test Organization** - Check all test files are in correct subdirectories
5. **Property 5: Gitignore Coverage** - Generate temporary files, verify they're ignored
6. **Property 6: Documentation Categorization** - Verify all docs are in category subdirectories
7. **Property 7: Import Stability** - Parse all Python files, verify imports resolve

### Manual Testing

1. Clone fresh repository and verify structure is clear
2. Run through developer onboarding to verify documentation is discoverable
3. Execute common development tasks to verify scripts work

## Implementation Notes

### Migration Steps

1. **Create new directories** (config/, scripts/, test subdirectories, docs subdirectories)
2. **Move test files** using `git mv` to preserve history
3. **Move documentation files** using `git mv` to preserve history
4. **Move configuration files** to config/
5. **Update pytest.ini** with new test paths
6. **Update docs/README.md** with new structure
7. **Update main README.md** with new structure diagram
8. **Update .gitignore** with enhanced patterns
9. **Create scripts/** with utility scripts
10. **Update all relative imports** in moved files
11. **Update all documentation links** in moved files
12. **Run full test suite** to verify nothing broke
13. **Update CI/CD configuration** if applicable

### Backward Compatibility

- Old import paths will break - this is intentional
- Update all imports to use new paths
- No API changes - only file locations change

### Performance Considerations

- No performance impact - purely organizational
- Test discovery might be slightly faster with better organization
- Documentation navigation will be faster with categorization
