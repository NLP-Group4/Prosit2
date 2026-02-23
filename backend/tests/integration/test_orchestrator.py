"""
Tests for the Orchestrator — validates full pipeline with mocked agents.

The orchestrator now requires user_id and db session for artifact persistence.
"""

import json
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

from backend.app.spec_schema import BackendSpec
from backend.agents.orchestrator import run_pipeline, GenerationResult
from backend.agents.spec_review import ValidationResult


VALID_SPEC_DICT = {
    "project_name": "test-api",
    "description": "A test backend",
    "spec_version": "1.0",
    "database": {"type": "postgres", "version": "15"},
    "auth": {"enabled": False, "type": "jwt", "access_token_expiry_minutes": 30},
    "entities": [
        {
            "name": "Item",
            "table_name": "items",
            "fields": [
                {"name": "id", "type": "uuid", "primary_key": True, "nullable": False, "unique": True},
                {"name": "title", "type": "string", "nullable": False},
            ],
            "crud": True,
        }
    ],
}


def _mock_db():
    """Create a mock database session for testing."""
    db = MagicMock()
    # Mock the project record that gets created
    mock_project = MagicMock()
    mock_project.id = uuid.uuid4()
    mock_project.status = "pending"
    db.add = MagicMock()
    db.commit = MagicMock()
    db.refresh = MagicMock(side_effect=lambda p: setattr(p, 'id', mock_project.id))
    return db, mock_project.id


FAKE_USER_ID = uuid.uuid4()


class TestRunPipeline:
    @pytest.mark.asyncio
    async def test_successful_pipeline(self, tmp_path):
        """Full pipeline should produce a ZIP on success."""
        spec = BackendSpec(**VALID_SPEC_DICT)
        fake_zip = tmp_path / "test.zip"
        fake_zip.write_text("fake zip")
        db, project_id = _mock_db()

        with patch("agents.orchestrator.generate_spec_from_prompt",
                    new_callable=AsyncMock) as mock_spec, \
             patch("agents.orchestrator.review_spec") as mock_review, \
             patch("agents.orchestrator.generate_project_files") as mock_gen, \
             patch("agents.orchestrator.assemble_project") as mock_assemble, \
             patch("agents.orchestrator.generate_report") as mock_report, \
             patch("agents.orchestrator.storage") as mock_storage:

            mock_spec.return_value = (spec, "gemini-2.0-flash")
            mock_review.return_value = ValidationResult(valid=True, spec=spec)
            mock_gen.return_value = {"app/main.py": "# test"}
            mock_assemble.return_value = fake_zip
            mock_report.return_value = "# Report"
            mock_storage.save_project_zip.return_value = "fake/path.zip"
            mock_storage.get_project_zip_path.return_value = fake_zip

            result = await run_pipeline(
                "Build a test API",
                user_id=FAKE_USER_ID,
                db=db,
            )

            assert result.success is True
            assert result.project_id is not None
            assert result.spec.project_name == "test-api"
            assert result.model_used == "gemini-2.0-flash"
            # Verify DB operations happened
            assert db.add.called
            assert db.commit.called

    @pytest.mark.asyncio
    async def test_spec_generation_failure(self):
        """Pipeline should return failure when spec generation fails."""
        db, project_id = _mock_db()

        with patch("agents.orchestrator.generate_spec_from_prompt",
                    new_callable=AsyncMock) as mock_spec:
            mock_spec.side_effect = ValueError("All models failed")

            result = await run_pipeline(
                "Build a test API",
                user_id=FAKE_USER_ID,
                db=db,
            )

            assert result.success is False
            assert result.project_id is not None
            assert any("failed" in e.lower() for e in result.errors)

    @pytest.mark.asyncio
    async def test_spec_validation_failure(self):
        """Pipeline should return failure when spec review rejects the spec."""
        spec = BackendSpec(**VALID_SPEC_DICT)
        db, project_id = _mock_db()

        with patch("agents.orchestrator.generate_spec_from_prompt",
                    new_callable=AsyncMock) as mock_spec, \
             patch("agents.orchestrator.review_spec") as mock_review:

            mock_spec.return_value = (spec, "gemini-2.0-flash")
            mock_review.return_value = ValidationResult(
                valid=False,
                errors=["Duplicate field name: 'email'"],
                warnings=["Generic project name"],
            )

            result = await run_pipeline(
                "Build a test API",
                user_id=FAKE_USER_ID,
                db=db,
            )

            assert result.success is False
            assert result.spec is spec
            assert "Duplicate field name" in result.errors[0]
            assert len(result.warnings) == 1

    @pytest.mark.asyncio
    async def test_pipeline_passes_model_id(self, tmp_path):
        """Custom model_id should be forwarded to PromptToSpecAgent."""
        spec = BackendSpec(**VALID_SPEC_DICT)
        fake_zip = tmp_path / "test.zip"
        fake_zip.write_text("fake zip")
        db, project_id = _mock_db()

        with patch("agents.orchestrator.generate_spec_from_prompt",
                    new_callable=AsyncMock) as mock_spec, \
             patch("agents.orchestrator.review_spec") as mock_review, \
             patch("agents.orchestrator.generate_project_files") as mock_gen, \
             patch("agents.orchestrator.assemble_project") as mock_assemble, \
             patch("agents.orchestrator.generate_report") as mock_report, \
             patch("agents.orchestrator.storage") as mock_storage:

            mock_spec.return_value = (spec, "gemini-2.5-pro")
            mock_review.return_value = ValidationResult(valid=True, spec=spec)
            mock_gen.return_value = {"app/main.py": "# test"}
            mock_assemble.return_value = fake_zip
            mock_report.return_value = "# Report"
            mock_storage.save_project_zip.return_value = "fake/path.zip"
            mock_storage.get_project_zip_path.return_value = fake_zip

            result = await run_pipeline(
                "Build a test API",
                user_id=FAKE_USER_ID,
                db=db,
                model_id="gemini-2.5-pro",
            )

            mock_spec.assert_called_once_with("Build a test API", model_id="gemini-2.5-pro", context="")
            assert result.model_used == "gemini-2.5-pro"

    @pytest.mark.asyncio
    async def test_warnings_propagated_on_success(self, tmp_path):
        """Warnings from spec review should be propagated in successful results."""
        spec = BackendSpec(**VALID_SPEC_DICT)
        fake_zip = tmp_path / "test.zip"
        fake_zip.write_text("fake zip")
        db, project_id = _mock_db()

        with patch("agents.orchestrator.generate_spec_from_prompt",
                    new_callable=AsyncMock) as mock_spec, \
             patch("agents.orchestrator.review_spec") as mock_review, \
             patch("agents.orchestrator.generate_project_files") as mock_gen, \
             patch("agents.orchestrator.assemble_project") as mock_assemble, \
             patch("agents.orchestrator.generate_report") as mock_report, \
             patch("agents.orchestrator.storage") as mock_storage:

            mock_spec.return_value = (spec, "gemini-2.0-flash")
            mock_review.return_value = ValidationResult(
                valid=True, spec=spec, warnings=["Name is generic"]
            )
            mock_gen.return_value = {"app/main.py": "# test"}
            mock_assemble.return_value = fake_zip
            mock_report.return_value = "# Report"
            mock_storage.save_project_zip.return_value = "fake/path.zip"
            mock_storage.get_project_zip_path.return_value = fake_zip

            result = await run_pipeline(
                "Build a test API",
                user_id=FAKE_USER_ID,
                db=db,
            )

            assert result.success is True
            assert "Name is generic" in result.warnings


class TestGenerationResult:
    def test_default_values(self):
        result = GenerationResult(success=False)
        assert result.zip_path is None
        assert result.spec is None
        assert result.errors is None
        assert result.warnings is None
        assert result.model_used is None
        assert result.project_id is None
