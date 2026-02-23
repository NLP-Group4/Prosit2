"""
Tests for the code generator — ensures valid specs produce correct file structures.
"""
import json
import pytest
from pathlib import Path

from backend.app.spec_schema import BackendSpec
from backend.app.code_generator import generate_project_files

SAMPLE_DIR = Path(__file__).parent.parent / "fixtures" / "sample_specs"


class TestOneEntityGeneration:
    """Test code generation with a single entity, no auth."""

    @pytest.fixture
    def spec(self):
        raw = json.loads((SAMPLE_DIR / "one_entity.json").read_text())
        return BackendSpec(**raw)

    @pytest.fixture
    def files(self, spec):
        return generate_project_files(spec)

    def test_expected_files_present(self, files):
        expected = [
            "app/main.py",
            "app/database.py",
            "app/config.py",
            "app/models.py",
            "app/schemas.py",
            "app/crud.py",
            "app/__init__.py",
            "app/routers/__init__.py",
            "app/routers/tasks.py",
            "requirements.txt",
            "Dockerfile",
            "docker-compose.yml",
            ".env.example",
        ]
        for f in expected:
            assert f in files, f"Missing file: {f}"

    def test_no_auth_file_when_disabled(self, files):
        assert "app/auth.py" not in files

    def test_main_has_task_router(self, files):
        assert "tasks_router" in files["app/main.py"]

    def test_main_no_auth_router(self, files):
        assert "auth_router" not in files["app/main.py"]

    def test_models_has_task_class(self, files):
        assert "class Task(Base)" in files["app/models.py"]

    def test_schemas_has_task_schemas(self, files):
        content = files["app/schemas.py"]
        assert "class TaskBase" in content
        assert "class TaskCreate" in content
        assert "class TaskUpdate" in content
        assert "class TaskResponse" in content

    def test_crud_has_task_functions(self, files):
        content = files["app/crud.py"]
        assert "create_task_item" in content
        assert "get_task_item" in content
        assert "get_tasks_list" in content

    def test_router_has_crud_endpoints(self, files):
        content = files["app/routers/tasks.py"]
        assert "def create_task" in content
        assert "def list_tasks" in content
        assert "def get_task" in content
        assert "def update_task" in content
        assert "def delete_task" in content

    def test_dockerfile_valid(self, files):
        content = files["Dockerfile"]
        assert "python:3.11-slim" in content
        assert "uvicorn" in content

    def test_docker_compose_has_postgres(self, files):
        content = files["docker-compose.yml"]
        assert "postgres:15" in content
        assert "todo_api" in content


class TestTwoEntityAuthGeneration:
    """Test code generation with two entities and JWT auth enabled."""

    @pytest.fixture
    def spec(self):
        raw = json.loads((SAMPLE_DIR / "two_entity_auth.json").read_text())
        return BackendSpec(**raw)

    @pytest.fixture
    def files(self, spec):
        return generate_project_files(spec)

    def test_auth_file_present(self, files):
        assert "app/auth.py" in files

    def test_both_routers_present(self, files):
        assert "app/routers/products.py" in files
        assert "app/routers/orders.py" in files

    def test_main_has_auth_router(self, files):
        assert "auth_router" in files["app/main.py"]

    def test_models_has_both_entities(self, files):
        content = files["app/models.py"]
        assert "class Product(Base)" in content
        assert "class Order(Base)" in content

    def test_models_has_user_account(self, files):
        assert "class UserAccount(Base)" in files["app/models.py"]

    def test_auth_has_jwt_functions(self, files):
        content = files["app/auth.py"]
        assert "create_access_token" in content
        assert "get_current_user" in content
        assert "get_password_hash" in content

    def test_routers_have_auth_dependency(self, files):
        for router_file in ["app/routers/products.py", "app/routers/orders.py"]:
            content = files[router_file]
            assert "get_current_user" in content

    def test_requirements_has_auth_deps(self, files):
        content = files["requirements.txt"]
        assert "python-jose" in content
        assert "passlib" in content

    def test_config_has_secret_key(self, files):
        assert "SECRET_KEY" in files["app/config.py"]


class TestCrudFalse:
    """Test that crud: false entities do not generate routers."""

    @pytest.fixture
    def spec(self):
        return BackendSpec(
            project_name="no-crud",
            entities=[
                {
                    "name": "Metric",
                    "table_name": "metrics",
                    "fields": [{"name": "id", "type": "uuid", "primary_key": True, "nullable": False, "unique": True}],
                    "crud": False,
                },
            ],
            auth={"enabled": False, "type": "jwt", "access_token_expiry_minutes": 30},
        )

    @pytest.fixture
    def files(self, spec):
        return generate_project_files(spec)

    def test_no_router_for_crud_false(self, files):
        assert "app/routers/metrics.py" not in files

    def test_model_still_generated(self, files):
        assert "class Metric(Base)" in files["app/models.py"]


class TestSingularization:
    """Test the improved singularization heuristic inside code generation."""

    from app.code_generator import _get_entity_singular

    @pytest.mark.parametrize("table,expected", [
        ("products", "product"),
        ("categories", "category"),
        ("statuses", "status"),
        ("boxes", "box"),
        ("addresses", "address"),
        ("data", "data"),
        ("tasks", "task"),
    ])
    def test_singular_forms(self, table, expected):
        from app.code_generator import _get_entity_singular
        assert _get_entity_singular(table) == expected
