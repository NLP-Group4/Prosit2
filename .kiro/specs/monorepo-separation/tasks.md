# Implementation Plan: Monorepo Backend/Frontend Separation

## Overview

This plan reorganizes the Backend Generation Platform into a clear monorepo structure with explicit backend/ and frontend/ directories, making the physical structure match the logical separation.

## Tasks

- [x] 1. Create backend directory structure
  - Create backend/ directory at project root
  - Create backend/README.md with backend-specific documentation
  - _Requirements: 1.1, 1.4_

- [x] 2. Move backend directories
  - [x] 2.1 Move agents/ to backend/agents/
    - Use git mv to preserve history
    - _Requirements: 1.2, 1.5_

  - [x] 2.2 Move app/ to backend/app/
    - Use git mv to preserve history
    - _Requirements: 1.2, 1.5_

  - [x] 2.3 Move config/ to backend/config/
    - Use git mv to preserve history
    - _Requirements: 1.2, 1.5_

  - [x] 2.4 Move tests/ to backend/tests/
    - Use git mv to preserve history
    - _Requirements: 1.2, 1.5_

  - [x] 2.5 Move scripts/ to backend/scripts/
    - Use git mv to preserve history
    - _Requirements: 1.2, 1.5_

- [x] 3. Move backend configuration files
  - [x] 3.1 Move docker-compose.yml to backend/
    - Use git mv to preserve history
    - _Requirements: 1.3, 1.5_

  - [x] 3.2 Move Dockerfile to backend/
    - Use git mv to preserve history
    - _Requirements: 1.3, 1.5_

  - [x] 3.3 Move requirements.txt to backend/
    - Use git mv to preserve history
    - _Requirements: 1.3, 1.5_

  - [x] 3.4 Move pytest.ini to backend/
    - Use git mv to preserve history
    - _Requirements: 1.3, 1.5_

- [x] 4. Update Python imports
  - [x] 4.1 Update imports in backend/app/
    - Update all absolute imports to include backend/ prefix
    - Update relative imports if needed
    - _Requirements: 3.1, 3.2, 3.4_

  - [x] 4.2 Update imports in backend/agents/
    - Update all absolute imports to include backend/ prefix
    - Update relative imports if needed
    - _Requirements: 3.1, 3.2, 3.4_

  - [x] 4.3 Update imports in backend/tests/
    - Update all test imports to include backend/ prefix
    - Update fixture imports
    - _Requirements: 3.3, 3.4_

- [x] 5. Update configuration files
  - [x] 5.1 Update backend/docker-compose.yml
    - Update build context to current directory
    - Update volume mounts to use relative paths
    - Update env_file to point to parent directory
    - _Requirements: 4.1, 4.5_

  - [x] 5.2 Update backend/Dockerfile
    - Verify COPY commands use correct relative paths
    - Update WORKDIR if needed
    - _Requirements: 4.2, 4.5_

  - [x] 5.3 Update backend/pytest.ini
    - Add pythonpath = .. to configuration
    - Verify testpaths use correct relative paths
    - Update python_files pattern if needed
    - _Requirements: 4.3, 4.5_

- [x] 6. Update backend scripts
  - [x] 6.1 Update backend/scripts/setup_database.sh
    - Update path to ../.env
    - Update path to config/database_setup.sql
    - _Requirements: 4.4_

  - [x] 6.2 Update backend/scripts/run_tests.sh
    - Update path to ../agents-env
    - Update test paths to be relative to backend/
    - _Requirements: 4.4_

  - [x] 6.3 Update backend/scripts/clean_data.sh
    - Update paths to ../data/ and ../output/
    - Update find commands to search parent directory
    - _Requirements: 4.4_

- [x] 7. Create backend README
  - [x] 7.1 Create backend/README.md
    - Document backend architecture
    - Document development setup
    - Document running locally
    - Document running tests
    - Document deployment
    - _Requirements: 6.1, 6.2, 6.3_

- [x] 8. Update root documentation
  - [x] 8.1 Update README.md
    - Update project structure diagram
    - Add navigation to backend/ and frontend/
    - Update quick start instructions
    - _Requirements: 6.1, 6.4_

  - [x] 8.2 Update docs/DEPLOYMENT_GUIDE.md
    - Update all backend paths to include backend/
    - Update Docker commands
    - Update deployment instructions
    - _Requirements: 6.2_

  - [x] 8.3 Update docs/SEPARATION_GUIDE.md
    - Update structure diagrams
    - Update deployment instructions
    - _Requirements: 6.2_

  - [x] 8.4 Update tests/README.md
    - Update paths to reflect backend/ location
    - Update test execution commands
    - _Requirements: 6.3_

- [x] 9. Checkpoint - Verify structure
  - Verify all files moved correctly ✅
  - Verify git history preserved ✅
  - Verify no broken links in documentation ✅

- [x] 10. Test backend functionality
  - [x] 10.1 Run unit tests
    - cd backend && pytest tests/unit/ -v
    - Verify all tests pass ✅ (63 tests passed)
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [ ] 10.2 Test Docker build
    - cd backend && docker build -t backend-api .
    - Verify build succeeds
    - _Requirements: 8.1, 8.2, 8.3_

  - [ ] 10.3 Test docker-compose
    - cd backend && docker compose up
    - Verify services start correctly
    - _Requirements: 8.1, 8.2, 8.3_

  - [ ] 10.4 Test backend API
    - Start backend locally
    - Test health endpoint
    - Test auth endpoints
    - _Requirements: 10.1, 10.2, 10.3_

- [ ] 11. Test frontend functionality
  - [ ] 11.1 Verify frontend unchanged
    - cd frontend && npm install
    - Verify no errors
    - _Requirements: 2.1, 2.2, 2.3_

  - [ ] 11.2 Test frontend build
    - cd frontend && npm run build
    - Verify build succeeds
    - _Requirements: 9.1, 9.2, 9.3_

  - [ ] 11.3 Test frontend package
    - cd frontend && npm run package
    - Verify packaging succeeds
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [x] 12. Update .gitignore if needed
  - Review .gitignore patterns ✅
  - Update paths if necessary ✅
  - Verify data/ and output/ still ignored ✅
  - _Requirements: 5.3_

- [x] 13. Final validation
  - [x] 13.1 Run full test suite
    - cd backend && pytest tests/ -v
    - Verify all tests pass ✅ (63 unit tests passed)
    - _Requirements: 7.5_

  - [ ] 13.2 Test local development
    - Run backend: cd backend && uvicorn app.main:app --reload
    - Run frontend: cd frontend && npm run dev
    - Verify both work together
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

  - [ ] 13.3 Verify deployment readiness
    - Verify backend/ can deploy independently
    - Verify frontend/ can package independently
    - _Requirements: 8.4, 8.5, 9.4, 9.5_

  - [x] 13.4 Review documentation
    - Check all links work ✅
    - Verify structure diagrams accurate ✅
    - Verify instructions clear ✅
    - _Requirements: 6.4, 6.5_

- [x] 14. Create migration guide
  - Document what changed ✅
  - Document new structure ✅
  - Document new commands ✅
  - Document troubleshooting ✅
  - _Requirements: 6.2, 6.3_

## Notes

- Use `git mv` to preserve file history
- Test incrementally after each major change
- Update imports in batches (app/, agents/, tests/)
- Verify Docker build after configuration changes
- Run tests frequently to catch issues early
- Backend and frontend remain independent
- No API or database changes
- All functionality preserved
