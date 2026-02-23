# Implementation Plan: Project Structure Optimization

## Overview

This plan reorganizes the Backend Generation Platform's file and folder structure to improve maintainability, discoverability, and developer experience. The implementation will be done incrementally to minimize disruption and allow for validation at each step.

## Tasks

- [x] 1. Create new directory structure
  - Create config/ directory for configuration files
  - Create scripts/ directory for utility scripts
  - Create tests/unit/, tests/integration/, tests/e2e/ subdirectories
  - Create tests/fixtures/ for test data
  - Create docs/architecture/, docs/features/, docs/implementation/, docs/historical/ subdirectories
  - _Requirements: 2.1, 5.1, 7.1, 7.2, 7.3, 9.1_

- [x] 2. Reorganize test files
  - [x] 2.1 Move unit tests to tests/unit/
    - Move tests/test_code_generator.py → tests/unit/
    - Move tests/test_spec_schema.py → tests/unit/
    - Move tests/test_project_assembler.py → tests/unit/
    - Move tests/test_spec_review.py → tests/unit/
    - _Requirements: 1.1, 7.1_

  - [x] 2.2 Move integration tests to tests/integration/
    - Move tests/test_api_endpoints.py → tests/integration/
    - Move tests/test_orchestrator.py → tests/integration/
    - Move tests/test_prompt_to_spec.py → tests/integration/
    - Move tests/test_model_registry.py → tests/integration/
    - Move tests/test_integration.py → tests/integration/
    - Move test_rag.py → tests/integration/
    - _Requirements: 1.2, 7.2_

  - [x] 2.3 Move end-to-end tests to tests/e2e/
    - Move test_autofix_full.py → tests/e2e/
    - Move test_electron_integration.py → tests/e2e/
    - _Requirements: 1.2, 7.3_

  - [x] 2.4 Move sample specs to tests/fixtures/
    - Move tests/sample_specs/ → tests/fixtures/sample_specs/
    - _Requirements: 9.2_

  - [x] 2.5 Update test imports
    - Update all import statements in moved test files to use absolute paths
    - Update conftest.py if needed
    - _Requirements: 1.1, 1.2_

  - [ ]* 2.6 Create tests/README.md
    - Document test organization (unit, integration, e2e)
    - Document how to run each test suite
    - Document pytest markers
    - _Requirements: 1.5_

- [x] 3. Reorganize documentation
  - [x] 3.1 Move architecture documents
    - Move docs/architecture-cloud-electron.md → docs/architecture/cloud-electron.md
    - Move docs/project.md → docs/architecture/project.md
    - Move docs/integration.md → docs/architecture/integration.md
    - _Requirements: 2.1_

  - [x] 3.2 Move feature documents
    - Move docs/GROQ_INTEGRATION.md → docs/features/groq-integration.md
    - Move docs/AUTOFIX_TEST_RESULTS.md → docs/features/autofix.md
    - _Requirements: 2.1_

  - [x] 3.3 Move implementation documents
    - Move docs/IMPLEMENTATION_STATUS.md → docs/implementation/status.md
    - Move docs/IMPLEMENTATION_COMPLETE.md → docs/implementation/complete.md
    - Move docs/TEST_RESULTS.md → docs/implementation/test-results.md
    - _Requirements: 2.1_

  - [x] 3.4 Move historical documents
    - Move docs/project evolution.md → docs/historical/project-evolution.md
    - Move docs/starbase_spec.txt → docs/historical/starbase-spec.txt
    - Move docs/pdf_text_dump.txt → docs/historical/pdf-text-dump.txt
    - Move docs/error log.txt → docs/historical/error-log.txt
    - _Requirements: 2.5_

  - [x] 3.5 Update docs/README.md
    - Update all links to reflect new structure
    - Add category descriptions
    - Update navigation guidance
    - _Requirements: 2.2, 2.3_

  - [x] 3.6 Update internal documentation links
    - Update relative links in all moved documentation files
    - Verify all links resolve correctly
    - _Requirements: 2.2_

- [x] 4. Create configuration directory
  - [x] 4.1 Move database setup to config/
    - Move database_setup.sql → config/database_setup.sql
    - _Requirements: 3.3_

  - [ ]* 4.2 Create config/README.md
    - Document purpose of config directory
    - Document each configuration file
    - _Requirements: 6.3_

- [x] 5. Create scripts directory
  - [x] 5.1 Create utility scripts
    - Create scripts/setup_database.sh for database initialization
    - Create scripts/run_tests.sh for running test suites
    - Create scripts/clean_data.sh for cleaning test data
    - _Requirements: 5.2, 5.3_

  - [ ]* 5.2 Create scripts/README.md
    - Document each script's purpose
    - Document script usage and parameters
    - _Requirements: 5.4_

- [x] 6. Update configuration files
  - [x] 6.1 Update pytest.ini
    - Add testpaths configuration for new test structure
    - Add markers for unit, integration, e2e tests
    - Update python_files pattern if needed
    - _Requirements: 7.5_

  - [x] 6.2 Enhance .gitignore
    - Add comprehensive Python patterns
    - Add OS-specific patterns (.DS_Store, Thumbs.db, desktop.ini)
    - Add IDE patterns (.vscode/, .idea/, *.swp)
    - Add build artifact patterns
    - Add comments documenting each section
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 6.3 Update docker-compose.yml if needed
    - Update volume mounts if config/ path changed
    - Update any references to moved files
    - _Requirements: 6.1_

- [x] 7. Update main README.md
  - [x] 7.1 Update project structure diagram
    - Reflect new directory organization
    - Document purpose of each directory
    - _Requirements: 8.1, 8.2_

  - [x] 7.2 Add project organization section
    - Explain test organization
    - Explain documentation organization
    - Explain scripts directory
    - _Requirements: 8.3, 8.4_

  - [x] 7.3 Update testing section
    - Document how to run unit tests
    - Document how to run integration tests
    - Document how to run e2e tests
    - _Requirements: 1.5, 7.5_

- [x] 8. Checkpoint - Verify structure
  - Run full test suite to verify all tests pass
  - Verify all imports resolve correctly
  - Verify all documentation links work
  - Verify Docker build succeeds
  - Ask user if any issues arise

- [x] 9. Update PROJECT_CLEANUP.md
  - Document the structure optimization changes
  - Update current project structure section
  - Add benefits of new structure
  - _Requirements: 8.5_

- [x] 10. Final validation
  - [x] 10.1 Run all test suites
    - Run pytest tests/unit/ -v
    - Run pytest tests/integration/ -v
    - Run pytest tests/e2e/ -v
    - _Requirements: 1.1, 1.2, 7.1, 7.2, 7.3_

  - [x] 10.2 Verify documentation
    - Check all links in docs/README.md
    - Verify documentation is discoverable
    - _Requirements: 2.2, 8.2_

  - [x] 10.3 Verify clean root directory
    - List root directory files
    - Verify only essential files remain
    - _Requirements: 3.1, 3.2, 3.5_

  - [ ]* 10.4 Test developer onboarding
    - Follow README instructions as new developer
    - Verify structure is intuitive
    - _Requirements: 8.3_

## Notes

- Tasks marked with `*` are optional documentation tasks
- Use `git mv` command to preserve file history
- Update imports incrementally and test after each change
- Validate at checkpoints to catch issues early
- All tests must pass before considering optimization complete
