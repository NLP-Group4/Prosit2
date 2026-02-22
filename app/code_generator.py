"""
Code Generator — renders Jinja2 templates using a validated BackendSpec.

Produces a dict[str, str] mapping relative file paths to their content.
This is a deterministic transformation: same spec → same output.
"""

from __future__ import annotations

import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from app.spec_schema import BackendSpec

# Template directory lives alongside this module
TEMPLATE_DIR = Path(__file__).parent / "templates"


def _get_entity_singular(table_name: str) -> str:
    """Derive a singular name from a table name (improved heuristic)."""
    if table_name.endswith("ies"):
        return table_name[:-3] + "y"            # categories → category
    elif table_name.endswith("sses"):
        return table_name[:-2]                   # addresses → address
    elif table_name.endswith("ses"):
        return table_name[:-2]                   # statuses → status
    elif table_name.endswith("xes"):
        return table_name[:-2]                   # boxes → box
    elif table_name.endswith("s") and not table_name.endswith("ss"):
        return table_name[:-1]                   # products → product
    return table_name                            # data → data, class → class


def generate_project_files(spec: BackendSpec) -> dict[str, str]:
    """
    Generate all backend source files from a validated spec.

    Returns:
        Dictionary mapping relative file path (e.g. "app/main.py")
        to the file's rendered content.
    """
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )

    spec_dict = spec.model_dump()
    files: dict[str, str] = {}

    # --- Shared context (enrich entities with computed fields) ---
    enriched_entities = []
    for entity in spec.entities:
        entity_dict = entity.model_dump()
        entity_dict["singular"] = _get_entity_singular(entity.table_name)
        # Find the primary key field name
        for f in entity.fields:
            if f.primary_key:
                entity_dict["pk_field"] = f.name
                break
        # Convert FieldType enums to plain strings so templates can use
        # field.type directly instead of fragile field.type.value
        for f in entity_dict["fields"]:
            if hasattr(f["type"], "value"):
                f["type"] = f["type"].value
        enriched_entities.append(entity_dict)

    ctx = {
        "project_name": spec.project_name,
        "description": spec.description,
        "database": spec_dict["database"],
        "auth": spec_dict["auth"],
        "entities": enriched_entities,
    }

    # --- Generate single-instance files ---
    single_files = {
        "app/main.py": "main.py.j2",
        "app/database.py": "database.py.j2",
        "app/config.py": "config.py.j2",
        "app/models.py": "models.py.j2",
        "app/schemas.py": "schemas.py.j2",
        "app/crud.py": "crud.py.j2",
        "requirements.txt": "requirements.txt.j2",
        "Dockerfile": "dockerfile.j2",
        "docker-compose.yml": "docker_compose.yml.j2",
        ".gitignore": "gitignore.j2",
    }

    for output_path, template_name in single_files.items():
        template = env.get_template(template_name)
        files[output_path] = template.render(**ctx)

    # --- Generate auth module if enabled ---
    if spec.auth.enabled:
        auth_template = env.get_template("auth.py.j2")
        files["app/auth.py"] = auth_template.render(**ctx)

    # --- Generate per-entity routers ---
    router_template = env.get_template("router.py.j2")
    for entity_dict in enriched_entities:
        if entity_dict["crud"]:
            # Skip generating CRUD router for "User" entity when auth is
            # enabled — user management is handled by /auth/register & /auth/login
            if spec.auth.enabled and entity_dict["name"] == "User":
                continue
            router_ctx = {
                "entity": entity_dict,
                "entity_singular": entity_dict["singular"],
                "auth_enabled": spec.auth.enabled,
            }
            output_path = f"app/routers/{entity_dict['table_name']}.py"
            files[output_path] = router_template.render(**router_ctx)

    # --- Generate __init__.py files ---
    files["app/__init__.py"] = ""
    files["app/routers/__init__.py"] = ""

    # --- Generate .env.example ---
    env_lines = [
        f"DATABASE_URL=postgresql://postgres:postgres@db:5432/{spec.project_name.replace('-', '_')}",
    ]
    if spec.auth.enabled:
        env_lines.append("SECRET_KEY=change-me-in-production")
    files[".env.example"] = "\n".join(env_lines) + "\n"

    return files
