# Test Suite Documentation

This directory contains the complete test suite for the Backend Generation Platform, organized by test type for easy discovery and execution.

## Test Organization

### Unit Tests (`unit/`)

Fast, isolated tests that verify individual components without external dependencies.

**Files:**
- `test_code_generator.py` - Code generation logic tests
- `test_spec_schema.py` - Specification schema validation tests
- `test_project_assembler.py` - Project assembly and ZIP creation tests
- `test_spec_review.py` - Specification review agent tests

**Run unit tests:**
```bash
pytest tests/unit/ -v
```

### Integration Tests (`integration/`)

Tests that verify components working together with external dependencies (database, LLM APIs, Docker).

**Files:**
- `test_api_endpoints.py` - FastAPI endpoint tests
- `test_orchestrator.py` - Agent orchestration pipeline tests
- `test_prompt_to_spec.py` - Prompt-to-specification conversion tests
- `test_model_registry.py` - LLM model registry tests
- `test_integration.py` - Full Docker integration tests
- `test_rag.py` - RAG system integration tests

**Run integration tests:**
```bash
pytest tests/integration/ -v
```

### End-to-End Tests (`e2e/`)

Complete workflow tests that verify the entire system from user input to final output.

**Files:**
- `test_autofix_full.py` - Complete auto-fix workflow test
- `test_electron_integration.py` - Electron app integration test

**Run e2e tests:**
```bash
pytest tests/e2e/ -v
```

### Test Fixtures (`fixtures/`)

Shared test data, sample specifications, and test utilities.

**Contents:**
- `sample_specs/` - Sample backend specifications for testing

## Running Tests

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test Types
```bash
# Unit tests only (fast)
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# E2E tests only
pytest tests/e2e/ -v
```

### Run Tests by Marker
```bash
# Run only unit tests
pytest -m unit -v

# Run only integration tests
pytest -m integration -v

# Run only e2e tests
pytest -m e2e -v

# Skip integration tests (useful for quick checks)
pytest -m "not integration" -v
```

### Run Specific Test File
```bash
pytest tests/unit/test_code_generator.py -v
```

### Run Specific Test Function
```bash
pytest tests/unit/test_code_generator.py::test_generate_main_file -v
```

## Test Configuration

Test configuration is managed in:
- `pytest.ini` - Pytest configuration (markers, paths, options)
- `conftest.py` - Shared fixtures and test setup

## Writing Tests

### Test Naming Convention
- Test files: `test_*.py`
- Test functions: `test_*`
- Test classes: `Test*`

### Test Markers
Use pytest markers to categorize tests:

```python
import pytest

@pytest.mark.unit
def test_something_fast():
    """Fast unit test"""
    pass

@pytest.mark.integration
def test_something_with_dependencies():
    """Integration test requiring external services"""
    pass

@pytest.mark.e2e
def test_complete_workflow():
    """End-to-end workflow test"""
    pass
```

### Test Structure
Follow the Arrange-Act-Assert pattern:

```python
def test_example():
    # Arrange - Set up test data
    input_data = {"key": "value"}
    
    # Act - Execute the code under test
    result = function_under_test(input_data)
    
    # Assert - Verify the results
    assert result == expected_output
```

## Continuous Integration

Tests are automatically run in CI/CD pipelines:
- Unit tests run on every commit
- Integration tests run on pull requests
- E2E tests run before deployment

## Troubleshooting

### Tests Failing Locally

1. **Check environment variables** - Ensure `.env` is configured
2. **Check dependencies** - Run `pip install -r requirements.txt`
3. **Check Docker** - Ensure Docker is running for integration tests
4. **Check API keys** - Ensure GOOGLE_API_KEY and GROQ_API_KEY are set

### Slow Tests

- Run only unit tests for quick feedback: `pytest tests/unit/ -v`
- Skip integration tests: `pytest -m "not integration" -v`
- Run specific test files instead of entire suite

### Import Errors

- Ensure you're running from project root
- Ensure virtual environment is activated: `source backend/agents-env/bin/activate` (from root) or `source agents-env/bin/activate` (from backend/)
- Check Python path includes project root

## Test Coverage

Generate coverage report:
```bash
pytest --cov=app --cov=agents tests/ --cov-report=html
```

View coverage report:
```bash
open htmlcov/index.html
```

## Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Main Project README](../README.md)
- [Contributing Guidelines](../docs/CONTRIBUTING.md) (if available)
