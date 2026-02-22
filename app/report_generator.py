"""
Report Generator — creates PROJECT_REPORT.md for generated backends.

The report is a human-readable markdown summary included in the ZIP,
documenting what was built, validated, and verified.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.spec_schema import BackendSpec
from agents.deploy_verify import VerificationResult
from agents.spec_review import ValidationResult


def generate_report(
    prompt: str | None,
    spec: BackendSpec,
    validation: ValidationResult | None = None,
    verification: VerificationResult | None = None,
    model_used: str | None = None,
) -> str:
    """Generate a PROJECT_REPORT.md markdown string."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = []

    # Header
    lines.append(f"# Project Report: {spec.project_name}")
    lines.append("")
    meta_parts = [f"Generated: {now}"]
    if model_used:
        meta_parts.append(f"Model: {model_used}")
    lines.append(" | ".join(meta_parts))
    lines.append("")

    # Prompt
    if prompt:
        lines.append("## Prompt")
        lines.append("")
        lines.append(f"> {prompt}")
        lines.append("")

    # Description
    if spec.description:
        lines.append("## Description")
        lines.append("")
        lines.append(spec.description)
        lines.append("")

    # Configuration
    lines.append("## Configuration")
    lines.append("")
    lines.append(f"- **Database**: PostgreSQL {spec.database.version}")
    lines.append(f"- **Authentication**: {'Enabled (JWT)' if spec.auth.enabled else 'Disabled'}")
    if spec.auth.enabled:
        lines.append(f"- **Token Expiry**: {spec.auth.access_token_expiry_minutes} minutes")
    lines.append("")

    # Entities
    lines.append("## Entities")
    lines.append("")

    for entity in spec.entities:
        lines.append(f"### {entity.name} (`{entity.table_name}`)")
        lines.append("")
        lines.append("| Field | Type | PK | Nullable | Unique |")
        lines.append("|-------|------|----|----------|--------|")
        for f in entity.fields:
            pk = "✓" if f.primary_key else ""
            nullable = "✓" if f.nullable else ""
            unique = "✓" if f.unique else ""
            lines.append(f"| `{f.name}` | {f.type.value} | {pk} | {nullable} | {unique} |")
        lines.append("")
        if entity.crud:
            lines.append(f"CRUD endpoints: `/{entity.table_name}/`")
            lines.append("")

    # Validation
    if validation:
        lines.append("## Validation")
        lines.append("")
        if validation.valid:
            warning_count = len(validation.warnings) if validation.warnings else 0
            lines.append(f"✅ Passed with {warning_count} warning(s)")
        else:
            lines.append("❌ Failed")
        if validation.warnings:
            lines.append("")
            for w in validation.warnings:
                lines.append(f"- ⚠️ {w}")
        if validation.errors:
            lines.append("")
            for e in validation.errors:
                lines.append(f"- ❌ {e}")
        lines.append("")

    # Verification
    if verification and not verification.skipped:
        lines.append("## Verification")
        lines.append("")
        if verification.passed:
            lines.append(
                f"✅ **All {verification.total_tests} tests passed**"
            )
        else:
            lines.append(
                f"❌ **{verification.passed_tests}/{verification.total_tests} tests passed**"
            )
        lines.append("")
        lines.append("| Endpoint | Result |")
        lines.append("|----------|--------|")
        for r in verification.results:
            icon = "✓" if r.passed else "✗"
            detail = f"{r.actual_status}" if r.actual_status else "N/A"
            error = f" — {r.error}" if r.error else ""
            lines.append(f"| `{r.method} {r.path}` | {icon} {detail}{error} |")
        lines.append("")

    elif verification and verification.skipped:
        lines.append("## Verification")
        lines.append("")
        lines.append(f"⏭️ Skipped: {verification.skip_reason}")
        lines.append("")

    # Quick start
    lines.append("## Quick Start")
    lines.append("")
    lines.append("```bash")
    lines.append("# Start the backend")
    lines.append("docker compose up --build")
    lines.append("")
    lines.append("# Open Swagger docs")
    lines.append("open http://localhost:8000/docs")
    lines.append("```")
    lines.append("")

    return "\n".join(lines)
