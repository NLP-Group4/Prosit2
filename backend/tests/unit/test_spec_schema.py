"""
Tests for the BackendSpec Pydantic schema validation.
"""
import json
import pytest
from pathlib import Path
from pydantic import ValidationError

from backend.app.spec_schema import BackendSpec, FieldType


SAMPLE_DIR = Path(__file__).parent.parent / "fixtures" / "sample_specs"


class TestValidSpecs:
    """Test that well-formed specs pass validation."""

    def test_one_entity_spec(self):
        raw = json.loads((SAMPLE_DIR / "one_entity.json").read_text())
        spec = BackendSpec(**raw)
        assert spec.project_name == "todo-api"
        assert len(spec.entities) == 1
        assert spec.entities[0].name == "Task"
        assert spec.auth.enabled is False

    def test_two_entity_auth_spec(self):
        raw = json.loads((SAMPLE_DIR / "two_entity_auth.json").read_text())
        spec = BackendSpec(**raw)
        assert spec.project_name == "ecommerce-api"
        assert len(spec.entities) == 2
        assert spec.auth.enabled is True
        assert spec.auth.access_token_expiry_minutes == 60

    def test_minimal_spec(self):
        raw = {
            "project_name": "minimal",
            "entities": [
                {
                    "name": "Item",
                    "table_name": "items",
                    "fields": [
                        {"name": "id", "type": "uuid", "primary_key": True, "nullable": False, "unique": True}
                    ],
                }
            ],
        }
        spec = BackendSpec(**raw)
        assert spec.spec_version == "1.0"
        assert spec.database.type.value == "postgres"


class TestInvalidSpecs:
    """Test that invalid specs are properly rejected."""

    def test_empty_project_name(self):
        with pytest.raises(ValidationError, match="project_name"):
            BackendSpec(project_name="", entities=[])

    def test_invalid_project_name_chars(self):
        with pytest.raises(ValidationError):
            BackendSpec(
                project_name="My Project!",
                entities=[
                    {
                        "name": "Item",
                        "table_name": "items",
                        "fields": [{"name": "id", "type": "uuid", "primary_key": True, "nullable": False, "unique": True}],
                    }
                ],
            )

    def test_no_entities(self):
        with pytest.raises(ValidationError, match="entities"):
            BackendSpec(project_name="test", entities=[])

    def test_duplicate_entity_names(self):
        entity = {
            "name": "User",
            "table_name": "users",
            "fields": [{"name": "id", "type": "uuid", "primary_key": True, "nullable": False, "unique": True}],
        }
        entity2 = {
            "name": "User",
            "table_name": "accounts",
            "fields": [{"name": "id", "type": "uuid", "primary_key": True, "nullable": False, "unique": True}],
        }
        with pytest.raises(ValidationError, match="Duplicate entity name"):
            BackendSpec(project_name="test", entities=[entity, entity2])

    def test_duplicate_table_names(self):
        entity1 = {
            "name": "User",
            "table_name": "accounts",
            "fields": [{"name": "id", "type": "uuid", "primary_key": True, "nullable": False, "unique": True}],
        }
        entity2 = {
            "name": "Admin",
            "table_name": "accounts",
            "fields": [{"name": "id", "type": "uuid", "primary_key": True, "nullable": False, "unique": True}],
        }
        with pytest.raises(ValidationError, match="Duplicate table name"):
            BackendSpec(project_name="test", entities=[entity1, entity2])

    def test_missing_primary_key(self):
        with pytest.raises(ValidationError, match="primary key"):
            BackendSpec(
                project_name="test",
                entities=[
                    {
                        "name": "Item",
                        "table_name": "items",
                        "fields": [{"name": "name", "type": "string", "nullable": False}],
                    }
                ],
            )

    def test_invalid_field_type(self):
        with pytest.raises(ValidationError):
            BackendSpec(
                project_name="test",
                entities=[
                    {
                        "name": "Item",
                        "table_name": "items",
                        "fields": [
                            {"name": "id", "type": "uuid", "primary_key": True, "nullable": False, "unique": True},
                            {"name": "data", "type": "binary"},  # Not in whitelist
                        ],
                    }
                ],
            )

    def test_invalid_entity_name_not_pascal_case(self):
        with pytest.raises(ValidationError, match="PascalCase"):
            BackendSpec(
                project_name="test",
                entities=[
                    {
                        "name": "my_entity",
                        "table_name": "my_entities",
                        "fields": [{"name": "id", "type": "uuid", "primary_key": True, "nullable": False, "unique": True}],
                    }
                ],
            )

    def test_invalid_field_name_not_snake_case(self):
        with pytest.raises(ValidationError, match="snake_case"):
            BackendSpec(
                project_name="test",
                entities=[
                    {
                        "name": "Item",
                        "table_name": "items",
                        "fields": [
                            {"name": "Id", "type": "uuid", "primary_key": True, "nullable": False, "unique": True},
                        ],
                    }
                ],
            )
