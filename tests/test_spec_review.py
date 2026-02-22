"""
Tests for the SpecReviewAgent — logical validation beyond Pydantic.
"""
import pytest

from app.spec_schema import BackendSpec
from agents.spec_review import review_spec


def _make_entity(name="Item", table_name="items", fields=None, crud=True):
    """Helper to build an entity dict with sensible defaults."""
    if fields is None:
        fields = [{"name": "id", "type": "uuid", "primary_key": True, "nullable": False, "unique": True}]
    return {"name": name, "table_name": table_name, "fields": fields, "crud": crud}


def _make_spec(project_name="test-api", entities=None, auth_enabled=False):
    """Helper to build a valid BackendSpec with overrides."""
    if entities is None:
        entities = [_make_entity()]
    return BackendSpec(
        project_name=project_name,
        entities=entities,
        auth={"enabled": auth_enabled, "type": "jwt", "access_token_expiry_minutes": 30},
    )


class TestValidSpecs:
    """Specs that should pass review."""

    def test_simple_valid_spec(self):
        spec = _make_spec()
        result = review_spec(spec)
        assert result.valid is True
        assert result.errors == []

    def test_valid_spec_with_auth(self):
        spec = _make_spec(auth_enabled=True)
        result = review_spec(spec)
        assert result.valid is True

    def test_valid_spec_returns_spec_object(self):
        spec = _make_spec()
        result = review_spec(spec)
        assert result.spec is spec


class TestDuplicateFieldNames:
    """Fields duplicated within the same entity."""

    def test_duplicate_field_names_rejected(self):
        fields = [
            {"name": "id", "type": "uuid", "primary_key": True, "nullable": False, "unique": True},
            {"name": "email", "type": "string", "nullable": False},
            {"name": "email", "type": "string", "nullable": True},
        ]
        spec = _make_spec(entities=[_make_entity(fields=fields)])
        result = review_spec(spec)
        assert result.valid is False
        assert any("duplicate field name" in e.lower() for e in result.errors)


class TestReservedWords:
    """Python reserved words used as field names."""

    def test_reserved_word_warning(self):
        fields = [
            {"name": "id", "type": "uuid", "primary_key": True, "nullable": False, "unique": True},
            {"name": "type", "type": "string", "nullable": False},
        ]
        spec = _make_spec(entities=[_make_entity(fields=fields)])
        result = review_spec(spec)
        assert result.valid is True  # warning only, not error
        assert any("reserved word" in w.lower() for w in result.warnings)

    def test_id_field_not_warned(self):
        """The 'id' field should not trigger a reserved-word warning."""
        spec = _make_spec()
        result = review_spec(spec)
        assert len(result.warnings) == 0


class TestNullablePrimaryKey:
    """Primary key fields must not be nullable."""

    def test_nullable_pk_rejected(self):
        fields = [
            {"name": "id", "type": "uuid", "primary_key": True, "nullable": True, "unique": True},
        ]
        spec = _make_spec(entities=[_make_entity(fields=fields)])
        result = review_spec(spec)
        assert result.valid is False
        assert any("nullable" in e.lower() and "primary key" in e.lower() for e in result.errors)


class TestAuthTableConflict:
    """Entities that conflict with the built-in auth user_accounts table."""

    def test_user_accounts_table_conflict(self):
        entity = _make_entity(name="Account", table_name="user_accounts")
        spec = _make_spec(entities=[entity], auth_enabled=True)
        result = review_spec(spec)
        assert result.valid is False
        assert any("user_accounts" in e for e in result.errors)

    def test_user_accounts_table_ok_when_auth_disabled(self):
        entity = _make_entity(name="Account", table_name="user_accounts")
        spec = _make_spec(entities=[entity], auth_enabled=False)
        result = review_spec(spec)
        assert result.valid is True


class TestGenericProjectName:
    """Generic project names produce a warning."""

    @pytest.mark.parametrize("name", ["app", "test", "tests", "src", "lib"])
    def test_generic_name_warning(self, name):
        spec = _make_spec(project_name=name)
        result = review_spec(spec)
        assert result.valid is True
        assert any("generic" in w.lower() for w in result.warnings)

    def test_normal_name_no_warning(self):
        spec = _make_spec(project_name="my-cool-api")
        result = review_spec(spec)
        assert len(result.warnings) == 0
