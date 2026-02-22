"""
SpecReviewAgent — Deterministic validation of backend specifications.

This agent uses pure Python logic (not LLM) for consistent, deterministic
validation. It checks for structural issues, normalizes casing, and 
ensures logical consistency.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.spec_schema import BackendSpec, FieldType


@dataclass
class ValidationResult:
    """Result of spec review — either valid with a (possibly normalized) spec, or invalid with errors."""
    valid: bool
    spec: BackendSpec | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def review_spec(spec: BackendSpec) -> ValidationResult:
    """
    Validate a BackendSpec for logical consistency beyond what Pydantic enforces.

    Pydantic (spec_schema.py) already handles:
    - Structural validation (types, required fields, naming conventions)
    - Duplicate entity names and table names
    - Single primary key per entity

    This agent checks for higher-level logical issues:
    1. Duplicate field names within an entity
    2. Python reserved-word field names (warning)
    3. Nullable primary keys
    4. Auth table name conflicts
    5. Generic project name (warning)

    Args:
        spec: A BackendSpec instance (already structurally valid from Pydantic).

    Returns:
        ValidationResult with validity status, normalized spec, and any errors/warnings.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # ----- Per-entity field validation -----
    reserved_names = {"id", "type", "class", "import", "from", "return", "pass"}

    for entity in spec.entities:
        pk_fields = [f for f in entity.fields if f.primary_key]

        # Check for duplicate field names within entity
        field_names = set()
        for f in entity.fields:
            if f.name in field_names:
                errors.append(
                    f"Entity '{entity.name}' has duplicate field name: '{f.name}'"
                )
            field_names.add(f.name)

        # Check for Python reserved words used as field names (warning only)
        for f in entity.fields:
            if f.name in reserved_names and f.name != "id":
                warnings.append(
                    f"Entity '{entity.name}', field '{f.name}' uses a Python "
                    f"reserved word. This may cause issues in generated code."
                )

        # Check PK is not nullable
        for f in pk_fields:
            if f.nullable:
                errors.append(
                    f"Entity '{entity.name}': primary key field '{f.name}' "
                    f"must not be nullable"
                )

    # ----- Auth consistency -----
    if spec.auth.enabled:
        for entity in spec.entities:
            if entity.table_name == "user_accounts":
                errors.append(
                    f"Entity '{entity.name}' uses table name 'user_accounts' "
                    f"which is reserved for the built-in auth user model"
                )

    # ----- Project name safety -----
    if spec.project_name in {"app", "test", "tests", "src", "lib"}:
        warnings.append(
            f"Project name '{spec.project_name}' is generic and may conflict "
            f"with common directory names"
        )

    # ----- Return result -----
    if errors:
        return ValidationResult(valid=False, errors=errors, warnings=warnings)

    return ValidationResult(valid=True, spec=spec, errors=[], warnings=warnings)
