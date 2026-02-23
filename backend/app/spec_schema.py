"""
Canonical Backend Specification Schema (Pydantic v2)

This is the Intermediate Representation (IR) for the backend generation platform.
All code generation flows through a validated BackendSpec instance.
"""

import re
import uuid
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class FieldType(str, Enum):
    """Strict whitelist of allowed field types."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    UUID = "uuid"
    TEXT = "text"


class DatabaseType(str, Enum):
    POSTGRES = "postgres"


class AuthType(str, Enum):
    JWT = "jwt"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class FieldSpec(BaseModel):
    """Schema for a single entity field."""
    name: str = Field(..., min_length=1, description="Field name (snake_case)")
    type: FieldType = Field(..., description="One of the allowed field types")
    primary_key: bool = Field(default=False)
    nullable: bool = Field(default=True)
    unique: bool = Field(default=False)

    @field_validator("name")
    @classmethod
    def validate_field_name(cls, v: str) -> str:
        if not re.match(r"^[a-z][a-z0-9_]*$", v):
            raise ValueError(
                f"Field name '{v}' must be snake_case "
                "(lowercase, start with letter, only letters/digits/underscores)"
            )
        return v


class EntitySpec(BaseModel):
    """Schema for a single database entity / model."""
    name: str = Field(..., min_length=1, description="Entity name (PascalCase)")
    table_name: str = Field(..., min_length=1, description="Database table name (snake_case)")
    fields: list[FieldSpec] = Field(..., min_length=1, description="List of fields")
    crud: bool = Field(default=True, description="Auto-generate CRUD endpoints")

    @field_validator("name")
    @classmethod
    def validate_entity_name(cls, v: str) -> str:
        if not re.match(r"^[A-Z][a-zA-Z0-9]*$", v):
            raise ValueError(
                f"Entity name '{v}' must be PascalCase "
                "(start with uppercase letter, only letters/digits)"
            )
        return v

    @field_validator("table_name")
    @classmethod
    def validate_table_name(cls, v: str) -> str:
        if not re.match(r"^[a-z][a-z0-9_]*$", v):
            raise ValueError(
                f"Table name '{v}' must be snake_case"
            )
        return v

    @model_validator(mode="after")
    def validate_has_primary_key(self) -> "EntitySpec":
        """Every entity must have exactly one primary key field."""
        pk_fields = [f for f in self.fields if f.primary_key]
        if len(pk_fields) == 0:
            raise ValueError(
                f"Entity '{self.name}' must have at least one primary key field"
            )
        if len(pk_fields) > 1:
            raise ValueError(
                f"Entity '{self.name}' has {len(pk_fields)} primary keys — "
                "only one is allowed"
            )
        return self


class DatabaseConfig(BaseModel):
    """Database configuration — locked to PostgreSQL for MVP."""
    type: DatabaseType = Field(default=DatabaseType.POSTGRES)
    version: str = Field(default="15")


class AuthConfig(BaseModel):
    """Authentication configuration."""
    enabled: bool = Field(default=True)
    type: AuthType = Field(default=AuthType.JWT)
    access_token_expiry_minutes: int = Field(default=30, ge=1, le=1440)


# ---------------------------------------------------------------------------
# Root spec model
# ---------------------------------------------------------------------------

class BackendSpec(BaseModel):
    """
    The canonical backend specification — the heart of the system.

    Everything flows through this validated model: prompts are converted
    into a BackendSpec, validated, then consumed by the code generator.
    """
    project_name: str = Field(
        ..., min_length=1, max_length=64,
        description="Project name (lowercase, hyphens allowed)"
    )
    description: str = Field(default="", description="Project description")
    spec_version: str = Field(default="1.0", description="Spec schema version")
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    entities: list[EntitySpec] = Field(..., min_length=1, description="At least one entity")

    @field_validator("project_name")
    @classmethod
    def validate_project_name(cls, v: str) -> str:
        v = v.lower().strip()
        if not re.match(r"^[a-z][a-z0-9\-]*$", v):
            raise ValueError(
                f"Project name '{v}' must be lowercase, start with a letter, "
                "and contain only letters, digits, or hyphens"
            )
        return v

    @model_validator(mode="after")
    def validate_no_duplicate_entities(self) -> "BackendSpec":
        """Reject specs with duplicate entity names."""
        names = [e.name.lower() for e in self.entities]
        seen = set()
        for name in names:
            if name in seen:
                raise ValueError(f"Duplicate entity name: '{name}'")
            seen.add(name)
        return self

    @model_validator(mode="after")
    def validate_no_duplicate_table_names(self) -> "BackendSpec":
        """Reject specs with duplicate table names."""
        tables = [e.table_name for e in self.entities]
        seen = set()
        for t in tables:
            if t in seen:
                raise ValueError(f"Duplicate table name: '{t}'")
            seen.add(t)
        return self


# ---------------------------------------------------------------------------
# Electron Integration Schemas
# ---------------------------------------------------------------------------

class EndpointVerificationResult(BaseModel):
    test_name: str | None = None
    endpoint: str
    method: str
    passed: bool
    status_code: int | None = None
    error_message: str | None = None


class VerificationReportRequest(BaseModel):
    """Payload sent by the Electron App after local Docker verification."""
    passed: bool
    elapsed_ms: int | None = None
    results: list[EndpointVerificationResult] = Field(default_factory=list)


class FailedTest(BaseModel):
    method: str
    endpoint: str
    error_message: str


class AutoFixRequest(BaseModel):
    """Payload sent when Electron requests an AI auto-fix due to failing verifications."""
    attempt_number: int = Field(default=1, ge=1)
    failed_tests: list[FailedTest] = Field(..., min_length=1)

# ---------------------------------------------------------------------------
# Thread & Memory Schemas
# ---------------------------------------------------------------------------

class MessageSchema(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    created_at: str

class ThreadSummary(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    title: Optional[str] = None
    created_at: str
    updated_at: str

class ThreadDetail(ThreadSummary):
    messages: list[MessageSchema] = Field(default_factory=list)

class ChatRequest(BaseModel):
    message: str

class GenerateResponse(BaseModel):
    project_id: uuid.UUID
    project_name: str
    status: str
    content: Optional[str] = None
    thread_id: Optional[uuid.UUID] = None
    download_url: Optional[str] = None
    warnings: Optional[List[str]] = None

class ProjectSummary(BaseModel):
    id: uuid.UUID
    project_name: str
    status: str
    created_at: str

class ProjectDetail(ProjectSummary):
    spec: Optional[BackendSpec] = None
    files: Optional[Dict[str, str]] = None

class PromptRequest(BaseModel):
    prompt: str
    model: Optional[str] = "gemini-1.5-flash"
    skip_verify: bool = False

class AutomaticDeployRequest(BaseModel):
    project_id: uuid.UUID
    target_env: str = "local"
