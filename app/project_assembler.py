"""
Project Assembler — writes generated files to disk and packages as ZIP.

Takes the output of code_generator.generate_project_files() and produces
a downloadable ZIP archive.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import time
import uuid as uuid_mod
import zipfile
from pathlib import Path


# Default output directory
OUTPUT_DIR = Path(__file__).parent.parent / "output"

# Maximum age of ZIP files before cleanup (seconds)
_MAX_ZIP_AGE_SECONDS = 3600  # 1 hour


def cleanup_old_zips(output_dir: Path) -> None:
    """Remove ZIP files older than _MAX_ZIP_AGE_SECONDS from the output directory."""
    if not output_dir.exists():
        return
    now = time.time()
    for f in output_dir.glob("*.zip"):
        try:
            if now - f.stat().st_mtime > _MAX_ZIP_AGE_SECONDS:
                f.unlink()
        except OSError:
            pass  # File may have been removed by another process


def assemble_project(
    project_name: str,
    files: dict[str, str],
    output_dir: Path | None = None,
) -> Path:
    """
    Write generated files to a temp directory and package as a ZIP.

    Args:
        project_name: Name of the project (used as root folder in ZIP).
        files: Dict mapping relative paths to file contents.
        output_dir: Where to write the final ZIP. Defaults to ./output/.

    Returns:
        Path to the generated ZIP file.
    """
    if output_dir is None:
        output_dir = OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    # Clean up old ZIPs to avoid unbounded disk usage
    cleanup_old_zips(output_dir)

    # Create a temp directory to write files into
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir) / project_name

        # Write all files
        for relative_path, content in files.items():
            full_path = project_root / relative_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")

        # Create the alembic directory (empty placeholder)
        alembic_dir = project_root / "alembic"
        alembic_dir.mkdir(parents=True, exist_ok=True)
        (alembic_dir / ".gitkeep").touch()

        # Package as ZIP — UUID suffix prevents concurrent overwrites
        short_id = uuid_mod.uuid4().hex[:8]
        zip_filename = f"{project_name}-{short_id}.zip"
        zip_path = output_dir / zip_filename

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _dirs, filenames in os.walk(project_root):
                for filename in filenames:
                    file_path = Path(root) / filename
                    arcname = file_path.relative_to(Path(tmpdir))
                    zf.write(file_path, arcname)

    return zip_path
