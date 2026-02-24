"""
Compatibility package for Docker/runtime imports.

In local development from repo root, modules are imported as:
    backend.app.*, backend.agents.*

In the backend Docker image, code is copied to /app with top-level packages:
    app, agents

This shim makes `backend.app` and `backend.agents` resolve in that layout by
adding the parent directory to this package's search path.
"""

from __future__ import annotations

from pathlib import Path
from pkgutil import extend_path

# Allow namespace-style extension, then include /app so that subpackages like
# backend.app map to /app/app and backend.agents map to /app/agents.
__path__ = extend_path(__path__, __name__)  # type: ignore[name-defined]
_parent = str(Path(__file__).resolve().parent.parent)
if _parent not in __path__:
    __path__.append(_parent)

