"""
Tests for the project assembler — ZIP packaging and structure validation.
"""
import zipfile
from pathlib import Path

import pytest

from backend.app.project_assembler import assemble_project, cleanup_old_zips


@pytest.fixture
def sample_files():
    """Minimal set of generated project files."""
    return {
        "app/main.py": "# entrypoint\n",
        "app/__init__.py": "",
        "requirements.txt": "fastapi\n",
        "Dockerfile": "FROM python:3.11-slim\n",
    }


@pytest.fixture
def output_dir(tmp_path):
    """Use a temp directory as the output directory."""
    out = tmp_path / "output"
    out.mkdir()
    return out


class TestAssembleProject:
    """Test that assemble_project produces correct ZIP files."""

    def test_zip_is_created(self, sample_files, output_dir):
        zip_path = assemble_project("my-api", sample_files, output_dir=output_dir)
        assert zip_path.exists()
        assert zip_path.suffix == ".zip"

    def test_zip_contains_expected_files(self, sample_files, output_dir):
        zip_path = assemble_project("my-api", sample_files, output_dir=output_dir)
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
            assert "my-api/app/main.py" in names
            assert "my-api/app/__init__.py" in names
            assert "my-api/requirements.txt" in names
            assert "my-api/Dockerfile" in names

    def test_alembic_placeholder_exists(self, sample_files, output_dir):
        zip_path = assemble_project("my-api", sample_files, output_dir=output_dir)
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
            assert "my-api/alembic/.gitkeep" in names

    def test_project_root_uses_project_name(self, sample_files, output_dir):
        zip_path = assemble_project("cool-backend", sample_files, output_dir=output_dir)
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
            assert all(n.startswith("cool-backend/") for n in names)

    def test_unique_zip_filenames(self, sample_files, output_dir):
        """Two calls should produce different ZIP filenames (UUID suffix)."""
        path1 = assemble_project("my-api", sample_files, output_dir=output_dir)
        path2 = assemble_project("my-api", sample_files, output_dir=output_dir)
        assert path1.name != path2.name
        assert path1.exists() and path2.exists()

    def test_file_content_preserved(self, sample_files, output_dir):
        zip_path = assemble_project("my-api", sample_files, output_dir=output_dir)
        with zipfile.ZipFile(zip_path) as zf:
            content = zf.read("my-api/app/main.py").decode("utf-8")
            assert content == "# entrypoint\n"


class TestCleanupOldZips:
    """Test that old ZIP files are cleaned up."""

    def test_cleanup_removes_old_files(self, output_dir):
        import time

        old_zip = output_dir / "old-project.zip"
        old_zip.write_text("old")
        # Artificially age the file
        import os
        old_time = time.time() - 7200  # 2 hours ago
        os.utime(old_zip, (old_time, old_time))

        new_zip = output_dir / "new-project.zip"
        new_zip.write_text("new")

        cleanup_old_zips(output_dir)

        assert not old_zip.exists()
        assert new_zip.exists()

    def test_cleanup_handles_missing_dir(self, tmp_path):
        """Should not raise if directory doesn't exist."""
        cleanup_old_zips(tmp_path / "nonexistent")
