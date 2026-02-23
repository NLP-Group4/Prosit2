# Utility Scripts

This directory contains utility scripts for common development and maintenance tasks.

## Available Scripts

### setup_database.sh

Initialize the platform PostgreSQL database with the required schema.

**Usage:**
```bash
./scripts/setup_database.sh
```

**What it does:**
- Checks if PostgreSQL is running
- Creates the platform database if it doesn't exist
- Runs the schema setup from `config/database_setup.sql`
- Creates tables for users, projects, and verification results

**Prerequisites:**
- PostgreSQL installed and running
- `.env` file configured with database credentials (or uses defaults)

**Environment Variables:**
- `PLATFORM_DB_HOST` - Database host (default: localhost)
- `PLATFORM_DB_PORT` - Database port (default: 5432)
- `PLATFORM_DB_NAME` - Database name (default: platform_db)
- `PLATFORM_DB_USER` - Database user (default: postgres)

---

### run_tests.sh

Run test suites with proper configuration and colored output.

**Usage:**
```bash
./scripts/run_tests.sh [unit|integration|e2e|all|coverage] [-v|--verbose]
```

**Examples:**
```bash
# Run unit tests
./scripts/run_tests.sh unit

# Run integration tests with verbose output
./scripts/run_tests.sh integration -v

# Run all test suites
./scripts/run_tests.sh all

# Run tests with coverage report
./scripts/run_tests.sh coverage
```

**Test Types:**
- `unit` - Fast, isolated unit tests (tests/unit/)
- `integration` - Integration tests with dependencies (tests/integration/)
- `e2e` - End-to-end workflow tests (tests/e2e/)
- `all` - Run all test suites sequentially
- `coverage` - Run tests with coverage report

**Prerequisites:**
- Virtual environment activated (script will activate agents-env if not)
- All dependencies installed (`pip install -r requirements.txt`)

---

### clean_data.sh

Clean test data, temporary files, and caches.

**Usage:**
```bash
./scripts/clean_data.sh [data|output|cache|logs|all]
```

**Examples:**
```bash
# Clean user data
./scripts/clean_data.sh data

# Clean generated project ZIPs
./scripts/clean_data.sh output

# Clean Python cache files
./scripts/clean_data.sh cache

# Clean log files
./scripts/clean_data.sh logs

# Clean everything
./scripts/clean_data.sh all
```

**Clean Types:**
- `data` - Remove all user data from data/ directory
- `output` - Remove all generated project ZIPs from output/ directory
- `cache` - Remove Python cache files (__pycache__, .pytest_cache, .coverage)
- `logs` - Remove all .log files
- `all` - Clean everything (prompts for confirmation)

**Warning:** These operations are destructive and cannot be undone. The script will prompt for confirmation before deleting data.

---

## Creating New Scripts

When adding new utility scripts:

1. **Make it executable:**
   ```bash
   chmod +x scripts/your_script.sh
   ```

2. **Add a shebang:**
   ```bash
   #!/bin/bash
   ```

3. **Use set -e for safety:**
   ```bash
   set -e  # Exit on error
   ```

4. **Add colored output:**
   ```bash
   GREEN='\033[0;32m'
   NC='\033[0m'
   echo -e "${GREEN}✅ Success!${NC}"
   ```

5. **Document in this README:**
   - Add usage instructions
   - List prerequisites
   - Provide examples
   - Explain what the script does

6. **Handle errors gracefully:**
   - Check prerequisites before running
   - Provide helpful error messages
   - Prompt for confirmation on destructive operations

## Script Conventions

- Use descriptive names (verb_noun.sh)
- Include help text for invalid arguments
- Use colored output for better UX
- Prompt for confirmation on destructive operations
- Check prerequisites before executing
- Provide clear success/failure messages
- Exit with appropriate status codes (0 for success, non-zero for failure)

## Related Documentation

- [Test Suite Documentation](../tests/README.md)
- [Configuration Files](../config/README.md)
- [Main README](../README.md)
