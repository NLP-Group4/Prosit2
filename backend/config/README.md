# Configuration Files

This directory contains configuration files for the Backend Generation Platform.

## Files

### database_setup.sql

PostgreSQL database schema initialization script for the platform database.

**Purpose:** Creates the necessary tables, indexes, and constraints for the multi-user platform.

**Tables:**
- `users` - User accounts and authentication
- `projects` - Generated backend projects
- `verification_results` - Project verification test results

**Usage:**
```bash
# Initialize the database
psql -U postgres -d platform_db -f config/database_setup.sql

# Or use the setup script
./scripts/setup_database.sh
```

**Note:** This is for the platform database, not the generated backend databases. Each generated backend has its own database schema defined in its generated code.

## Adding New Configuration Files

When adding new configuration files to this directory:

1. Document the file's purpose in this README
2. Provide usage examples
3. Include any prerequisites or dependencies
4. Note any environment variables required

## Related Configuration

Other configuration files in the project:

- `.env` - Environment variables (gitignored, see `.env.example`)
- `pytest.ini` - Pytest test configuration
- `docker-compose.yml` - Docker service composition
- `Dockerfile` - Docker image definition
- `requirements.txt` - Python dependencies
- `frontend/electron-builder.yml` - Electron app build configuration
