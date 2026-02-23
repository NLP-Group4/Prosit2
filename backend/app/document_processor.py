"""
Document Processor — Extracts plain text from uploaded files.

Supports: .txt, .md, .json, .csv, .pdf
All extraction produces plain text suitable for chunking and embedding.
"""

from __future__ import annotations

import csv
import io
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Maximum file size (5 MB)
MAX_FILE_SIZE = 5 * 1024 * 1024

# Supported extensions
SUPPORTED_EXTENSIONS = {".txt", ".md", ".json", ".csv", ".pdf"}


class UnsupportedFileError(Exception):
    pass


class FileTooLargeError(Exception):
    pass


def extract_text(filename: str, content: bytes) -> str:
    """
    Extract plain text from file content based on extension.

    Args:
        filename: Original filename (used to detect format).
        content: Raw file bytes.

    Returns:
        Extracted plain text.

    Raises:
        UnsupportedFileError: If the file type is not supported.
        FileTooLargeError: If the file exceeds MAX_FILE_SIZE.
    """
    if len(content) > MAX_FILE_SIZE:
        raise FileTooLargeError(
            f"File is {len(content)} bytes — max allowed is {MAX_FILE_SIZE} (5MB)"
        )

    ext = Path(filename).suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileError(
            f"Unsupported file type: '{ext}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    if ext in (".txt", ".md"):
        return _extract_text_plain(content)
    elif ext == ".json":
        return _extract_text_json(content)
    elif ext == ".csv":
        return _extract_text_csv(content)
    elif ext == ".pdf":
        return _extract_text_pdf(content)

    raise UnsupportedFileError(f"No extractor for '{ext}'")


def _extract_text_plain(content: bytes) -> str:
    """Plain text / markdown — decode as UTF-8."""
    return content.decode("utf-8", errors="replace").strip()


def _extract_text_json(content: bytes) -> str:
    """JSON — pretty-print for readable context."""
    try:
        data = json.loads(content)
        return json.dumps(data, indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        # Fall back to raw text if JSON is invalid
        return content.decode("utf-8", errors="replace").strip()


def _extract_text_csv(content: bytes) -> str:
    """CSV — serialize rows as readable text."""
    text = content.decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)

    if not rows:
        return ""

    # Use first row as headers
    headers = rows[0]
    lines = []
    for row in rows[1:]:
        pairs = [
            f"{h}: {v}" for h, v in zip(headers, row) if v.strip()
        ]
        if pairs:
            lines.append("; ".join(pairs))

    return "\n".join(lines)


def _extract_text_pdf(content: bytes) -> str:
    """PDF — extract text via pymupdf."""
    try:
        import pymupdf  # noqa: F811

        doc = pymupdf.Document(stream=content, filetype="pdf")
        pages = []
        for page in doc:
            text = page.get_text().strip()
            if text:
                pages.append(text)
        doc.close()
        return "\n\n".join(pages)
    except ImportError:
        logger.warning("pymupdf not installed — PDF extraction unavailable")
        raise UnsupportedFileError("PDF support requires pymupdf (pip install pymupdf)")
    except Exception as e:
        raise ValueError(f"Failed to extract text from PDF: {e}")
