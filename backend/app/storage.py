"""
User-Scoped File Storage — secure file management for user projects.

All file paths use UUIDs only to prevent path traversal attacks.
Every operation validates user ownership.
"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

# Root data directory (mounted as volume in Docker)
DATA_DIR = Path(__file__).parent.parent / "data"


def _user_project_dir(user_id: uuid.UUID, project_id: uuid.UUID) -> Path:
    """Build the storage path for a user's project."""
    # Use str(UUID) to ensure canonical format — no path traversal possible
    return DATA_DIR / str(user_id) / str(project_id)


def save_project_zip(
    user_id: uuid.UUID,
    project_id: uuid.UUID,
    source_zip: Path,
) -> str:
    """
    Move a generated ZIP to the user's project directory.

    Returns:
        Relative path from DATA_DIR (e.g. "{user_id}/{project_id}/project.zip")
    """
    dest_dir = _user_project_dir(user_id, project_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / "project.zip"
    shutil.move(str(source_zip), str(dest_path))
    return str(dest_path.relative_to(DATA_DIR))


def get_project_zip_path(
    user_id: uuid.UUID,
    project_id: uuid.UUID,
) -> Path | None:
    """
    Get the absolute path to a user's project ZIP.

    Returns None if the file doesn't exist.
    """
    zip_path = _user_project_dir(user_id, project_id) / "project.zip"
    if zip_path.exists():
        return zip_path
    return None


def delete_project_files(
    user_id: uuid.UUID,
    project_id: uuid.UUID,
) -> None:
    """Delete all files for a user's project."""
    project_dir = _user_project_dir(user_id, project_id)
    if project_dir.exists():
        shutil.rmtree(project_dir)
